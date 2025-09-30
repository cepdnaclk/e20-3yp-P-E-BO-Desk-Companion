#!/usr/bin/env python3

"""
Voice Assistant with Robot Control

Listens for trigger phrases and controls robot emotions with simultaneous arm/eye expressions and voice output.
Integrated with standalone functions for arm and eye movements.
Includes song playback functionality triggered by 'play song' commands.
Updated to:
- Never speak emotion labels aloud; react via eyes/arms instead.
- Cap spoken replies to ~40 tokens and redact emotion/forbidden phrases.
- Maintain implicit empathetic persona in all replies.
"""

import google.generativeai as genai
from google.api_core import exceptions as gcore_exceptions

import pygame
import time
import os
import asyncio
import edge_tts
import speech_recognition as sr
import whisper
import sounddevice as sd
import numpy as np
import tempfile
import scipy.io.wavfile
import subprocess
import re
import random
import errno
import threading
import board
import busio
import smbus
import RPi.GPIO as GPIO

from arms.arms_pwm import (
    say_hi,
    express_tired,
    express_happy,
    express_sad,
    express_angry,
    reset_to_neutral,
    scan_i2c_devices,
    angle_to_pulse_value,
    set_servos,
    smooth_move
)

from display.eyes_qr import RoboEyesDual
from interaction.play_song1 import play_music
from Communication.sender import AudioNode, start_audio_node

from datetime import datetime, timezone
import dateutil.parser
import firebase_admin
from firebase_admin import credentials, db
import json
import socket
import fcntl
import struct
import logging

# ==== Globals (top of assistant_combined1.py) ====
# Session and memory
SKIP_USER_CHECK = bool(int(os.getenv("PEBO_SKIP_USER_CHECK", "1")))  # 1=skip user gating, 0=enable
SESSION_ACTIVE: bool = False
CURRENT_USER_NAME: str | None = None
LAST_MOOD: str | None = None
LAST_TOPICS: list[str] = []
MEM_PATH = "/home/pi/pebo_memory.json"


NAME_RE = re.compile(r"\b(my\s+name\s+is|i\s*am|i'm)\s+([A-Za-z]{2,30})\b", re.IGNORECASE)
def extract_name_from_text(text: str) -> str | None:
    m = NAME_RE.search(text or "")
    return m.group(2).strip().title() if m else None
# ---------------------------
# Logging
# ---------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/ipconfig/store_ip.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------------------------
# GPIO / Pins
# ---------------------------
TOUCH_PIN = 17  # GPIO pin number (Pin 11)
GPIO.setmode(GPIO.BCM)
GPIO.setup(TOUCH_PIN, GPIO.IN)

LED_PIN = 18  # GPIO pin number (Pin 12)

# ---------------------------
# I2C / Displays
# ---------------------------
PCA9685_ADDR = 0x40
LEFT_EYE_ADDRESS = 0x3C
RIGHT_EYE_ADDRESS = 0x3D

i2c = None
eyes = None
current_eye_thread = None
stop_event = None

# ---------------------------
# Firebase
# ---------------------------
SERVICE_ACCOUNT_PATH = '/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/ipconfig/firebase_config.json'
DATABASE_URL = 'https://pebo-task-manager-767f3-default-rtdb.asia-southeast1.firebasedatabase.app'

JSON_CONFIG_PATH = "/home/pi/pebo_config.json"

# ---------------------------
# Persona / TTS safety
# ---------------------------
ASSISTANT_NAME = "pebo"
MAX_SPOKEN_TOKENS = 40

FORBIDDEN_PHRASES = [
    "emotional companion", "therapist", "psychologist"
]

EMOTION_TERMS = [
    "happy", "sad", "angry", "love", "normal", "fear", "confused",
    "emotion", "mood", "feeling", "feelings", "you look", "you sound"
]

ROLE_PROMPT = (
  "Act as 'pebo', empathetic, concise, a bit cute. Do not describe gestures or stage directions. "
  "Never name detected emotions aloud. Keep replies ~40 tokens, supportive and Yohanly."
)
STAGE_RE = re.compile(r'\s*\(*\b(eyes?|hands?|head|nods?|blinks?|gestures?|sighs?|smiles?)\b.*?\)*[.?!]?', re.IGNORECASE)
def sanitize_llm_text(t: str) -> str:
    t = STAGE_RE.sub("", t or "").strip()
    return t if t else "Here with support."




# Place near TTS helpers
# Serialize TTS so only one audio plays at a time
speak_lock = asyncio.Lock()

async def speak_once(text: str):
    async with speak_lock:
        await speak_text(text)  # speak_text already trims and redacts safely


EMO_REGEX = {
    "Sad": r"\b(sad|down|blue|upset|depressed|unhappy|low)\b",
    "Angry": r"\b(angry|mad|furious|pissed|irritated|annoyed|frustrated)\b",
    "Happy": r"\b(happy|glad|cheerful|excited|joyful|stoked|thrilled)\b",
    "Love": r"\b(love|loving|beloved|adore|affection|fond|caring|cute|adorable|sweet|charming)\b",
    "Normal": r"\b(okay|ok|fine|alright|normal|so-so|meh|neutral)\b",
    "Tired": r"\b(tired|sleepy|exhausted|fatigued|drained)\b",
    "Confused": r"\b(confused|unsure|uncertain|lost)\b",
    "Fear": r"\b(scared|afraid|anxious|nervous|worried|stressed)\b",
}
def extract_emotion_from_text(text: str) -> str | None:
    t = (text or "").lower()
    if re.search(r"\bnot\s+(sad|angry|mad|upset|depressed|happy|in love|loving|scared|afraid|anxious|nervous|tired)\b", t):
        return None
    for label, pattern in EMO_REGEX.items():
        if re.search(pattern, t, re.IGNORECASE):
            return label
    return None

# ---------------------------
# Eyes/Arms Helpers
# ---------------------------
def load_memory():
    global CURRENT_USER_NAME, LAST_MOOD, LAST_TOPICS
    try:
        with open(MEM_PATH, "r", encoding="utf-8") as f:
            m = json.load(f)
        CURRENT_USER_NAME = m.get("name")
        LAST_MOOD = m.get("mood")
        LAST_TOPICS = (m.get("topics") or [])[-5:]
    except Exception:
        pass

def save_memory():
    try:
        with open(MEM_PATH, "w", encoding="utf-8") as f:
            json.dump({"name": CURRENT_USER_NAME, "mood": LAST_MOOD, "topics": LAST_TOPICS[-5:]}, f)
    except Exception:
        pass


def initialize_hardware():
    """Initialize I2C and eyes globally."""
    global i2c, eyes
    i2c = busio.I2C(board.SCL, board.SDA)
    eyes = RoboEyesDual(LEFT_EYE_ADDRESS, RIGHT_EYE_ADDRESS)
    eyes.begin(128, 64, 40)

def run_emotion(arm_func, eye_func, duration=1):
    """Run arm movement and eye expression simultaneously, then return to normal mode."""
    global current_eye_thread, stop_event
    stop_event = threading.Event()
    current_eye_thread = threading.Thread(target=eye_func, args=(stop_event,))
    current_eye_thread.daemon = True
    current_eye_thread.start()

    if arm_func:
        arm_func()

    time.sleep(duration)
    stop_event.set()
    if current_eye_thread:
        current_eye_thread.join(timeout=1.0)
    current_eye_thread = None
    normal()

def hi():
    print("Expressing Hi")
    run_emotion(say_hi, eyes.Happy)

# assistant_combined1.py
def normal():
    print("Expressing Normal")
    global current_eye_thread, stop_event
    if stop_event: stop_event.set()
    if current_eye_thread: current_eye_thread.join(timeout=1.0)
    stop_event = threading.Event()
    # FIX: use Default (capital D), not default
    current_eye_thread = threading.Thread(target=eyes.Default, args=(stop_event,))
    current_eye_thread.daemon = True
    current_eye_thread.start()



def happy():
    print("Expressing Happy")
    run_emotion(express_happy, eyes.Happy)

def sad():
    print("Expressing Sad")
    run_emotion(express_sad, eyes.Tired)

def angry():
    print("Expressing Angry")
    run_emotion(express_angry, eyes.Angry)

def love():
    print("Expressing Love")
    run_emotion(express_happy, eyes.Love)

def qr(device_id):
    """Express QR code with the specified device ID"""
    print(f"Expressing QR with device ID: {device_id}")
    run_emotion(None, lambda stop_event: eyes.QR(device_id, stop_event=stop_event), duration=15)

def cleanup():
    """Clean up resources, clear displays, and deinitialize I2C bus."""
    global i2c, eyes, current_eye_thread, stop_event
    print("🖥️ Cleaning up resources...")

    if stop_event:
        stop_event.set()
    if current_eye_thread:
        current_eye_thread.join(timeout=1.0)
        current_eye_thread = None

    try:
        reset_to_neutral()
        eyes.display_left.fill(0)
        eyes.display_left.show()
        eyes.display_right.fill(0)
        eyes.display_right.show()
        print("🖥️ Displays cleared")
    except Exception as e:
        print(f"🖥️ Error clearing displays: {e}")

    try:
        i2c.deinit()
        print("🖥️ I2C bus deinitialized, SCL and SDA cleared")
    except Exception as e:
        print(f"🖥️ Error deinitializing I2C bus: {e}")

    print("🖥️ Cleanup complete")

# ---------------------------
# Audio / pygame
# ---------------------------
# Audio init guard
HAS_AUDIO = True
try:
    pygame.mixer.init()
except Exception as e:
    HAS_AUDIO = False
    print(f"[audio] pygame init failed, running degraded: {e}")


def amplify_audio(input_file, output_file, gain_db=10):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", input_file,
        "-filter:a", f"volume={gain_db}dB",
        output_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ---------------------------
# TTS redaction + token cap
# ---------------------------
def _remove_forbidden_phrases(text: str) -> str:
    out = text
    for p in FORBIDDEN_PHRASES:
        out = re.sub(re.escape(p), "", out, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", out).strip()

def _sentence_split(text: str):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]

def _redact_emotion_mentions(text: str) -> str:
    sentences = _sentence_split(text)
    kept = []
    for s in sentences:
        if any(re.search(rf"\b{re.escape(term)}\b", s, re.IGNORECASE) for term in EMOTION_TERMS):
            continue
        kept.append(s)
    cleaned = " ".join(kept).strip()
    return cleaned if cleaned else "HELLOO! i'M YOUR pebo. I'm Here for you."

def _trim_to_tokens(text: str, max_tokens: int = MAX_SPOKEN_TOKENS) -> str:
    words = re.findall(r"\S+", text)
    if len(words) <= max_tokens:
        return text.strip()
    return " ".join(words[:max_tokens]).rstrip(",.;:") + "…"

def prepare_spoken_text(text: str) -> str:
    text = _remove_forbidden_phrases(text)
    text = _redact_emotion_mentions(text)
    text = _trim_to_tokens(text, MAX_SPOKEN_TOKENS)
    return text

async def speak_text(text):
    if not HAS_AUDIO:
        print(f"[speak] (no audio) {prepare_spoken_text(text)}")
        return

    # Prepare and pad ultra‑short utterances so Edge TTS always returns audio
    safe_text = prepare_spoken_text(text)
    # If there are fewer than 2 word characters (e.g., "4"), pad to a sentence
    if len(re.findall(r"\w", safe_text)) < 2:
        safe_text = f"The answer is {safe_text}."

    voices = ["en-US-JennyNeural", "en-US-GuyNeural", "en-GB-LibbyNeural"]
    filename = "response.mp3"
    boosted_file = "boosted_response.mp3"

    last_err = None
    for voice in voices:
        try:
            tts = edge_tts.Communicate(safe_text, voice)
            await tts.save(filename)
            amplify_audio(filename, boosted_file, gain_db=20)
            pygame.mixer.music.load(boosted_file)
            pygame.mixer.music.set_volume(1.0)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.25)
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            try:
                os.remove(filename)
                os.remove(boosted_file)
            except Exception:
                pass
            return
        except edge_tts.exceptions.NoAudioReceived as e:
            last_err = e
            await asyncio.sleep(0.3)
            continue
        except Exception as e:
            last_err = e
            await asyncio.sleep(0.3)
            continue

    # Fallback: offline TTS to guarantee the assistant continues speaking
    try:
        fallback_wav = "fallback_tts.wav"
        # espeak must be installed on the device; adjust voice/rate as desired
        subprocess.run(["espeak", "-ven+f3", "-s", "170", safe_text, "-w", fallback_wav], check=True)
        pygame.mixer.music.load(fallback_wav)
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.25)
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        try:
            os.remove(fallback_wav)
        except Exception:
            pass
    except Exception as e2:
        # As a last resort, log the failure so the session does not crash
        print(f"[tts] All TTS attempts failed: {last_err} | Fallback error: {e2} | text={safe_text!r}")


# ---------------------------
# Speech recognition
# ---------------------------
recognizer = sr.Recognizer()
mic = sr.Microphone()


# Once at init:
recognizer.pause_threshold = 0.8
recognizer.non_speaking_duration = 0.4
recognizer.energy_threshold = 300


def listen(
    recognizer: sr.Recognizer,
    mic: sr.Microphone,
    *,
    timeout: float = 12,
    phrase_time_limit: float = 10,
    retries: int = 2,
    language: str = "en-US",
    calibrate_duration: float = 0.5,
) -> str | None:
    """Capture a single utterance and return the recognized text, with LED indicating listening state."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.output(LED_PIN, GPIO.LOW)

    for attempt in range(retries + 1):
        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=calibrate_duration)
                print("🎤 Listening… (attempt", attempt + 1, ")")
                GPIO.output(LED_PIN, GPIO.HIGH)
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                GPIO.output(LED_PIN, GPIO.LOW)
            try:
                text = recognizer.recognize_google(audio, language=language)
                text = text.strip().lower()
                if text:
                    print(f"🗣️ You said: {text}")
                    GPIO.cleanup()
                    return text
            except sr.UnknownValueError:
                print("🤔 Sorry—couldn’t understand that.")
            except sr.RequestError as e:
                print(f"⚠️ Google speech service error ({e}). Falling back to offline engine…")
                try:
                    text = recognizer.recognize_sphinx(audio, language=language)
                    text = text.strip().lower()
                    if text:
                        print(f"🗣️ (Offline) You said: {text}")
                        GPIO.cleanup()
                        return text
                except Exception as sphinx_err:
                    print(f"❌ Offline engine failed: {sphinx_err}")
        except sr.WaitTimeoutError:
            print("⏳ Timed out waiting for speech.")
            GPIO.output(LED_PIN, GPIO.LOW)
        except Exception as mic_err:
            print(f"🎤 Mic/Audio error: {mic_err}")
            GPIO.output(LED_PIN, GPIO.LOW)
        if attempt < retries:
            time.sleep(0.5)
    print("😕 No intelligible speech captured.")
    GPIO.output(LED_PIN, GPIO.LOW)
    GPIO.cleanup()
    return None

# Whisper model (optional path)
whisper_model = whisper.load_model("base")

def listen_whisper(duration=1, sample_rate=16000) -> str | None:
    """Capture audio and transcribe using Whisper."""
    print("🎤 Listening with Whisper…")
    audio_path = None
    try:
        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
        sd.wait()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
            scipy.io.wavfile.write(tmpfile.name, sample_rate, recording)
            audio_path = tmpfile.name
        result = whisper_model.transcribe(audio_path)
        text = result.get("text", "").strip().lower()
        if text:
            print(f"🗣️ You said (Whisper): {text}")
            return text
        else:
            print("🤔 No intelligible speech detected.")
            return None
    except Exception as e:
        print(f"❌ Whisper error: {e}")
        return None
    finally:
        try:
            if audio_path:
                os.remove(audio_path)
        except:
            pass

# ---------------------------
# Network helpers
# ---------------------------
def get_ip_address(ifname='wlan0'):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip = socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,
            struct.pack('256s', bytes(ifname[:15], 'utf-8'))
        )[20:24])
        return ip
    except Exception as e:
        logger.warning(f"Error getting IP address for {ifname}: {str(e)}")
        return None

def get_wifi_ssid():
    try:
        result = subprocess.run(['iwgetid', '-r'], capture_output=True, text=True, timeout=5)
        ssid = result.stdout.strip()
        return ssid if ssid else None
    except subprocess.TimeoutExpired:
        logger.warning("Timeout while getting SSID")
        return None
    except Exception as e:
        logger.warning(f"Error getting SSID: {str(e)}")
        return None

# ---------------------------
# Firebase tasks
# ---------------------------
def fetch_user_tasks(user_id):
    """Fetch tasks for the given user from Firebase and return a formatted response."""
    try:
        tasks_ref = db.reference(f'users/{user_id}/tasks')
        tasks = tasks_ref.get()
        if not tasks:
            logger.info(f"No tasks found for user {user_id}")
            return "You have no tasks scheduled."
        current_time = datetime.now(timezone.utc)
        pending_tasks = []
        for task_id, task_data in tasks.items():
            if not task_data.get('completed', False):
                deadline_str = task_data.get('deadline')
                try:
                    deadline = dateutil.parser.isoparse(deadline_str)
                    time_until_deadline = deadline - current_time
                    minutes_until_deadline = int(time_until_deadline.total_seconds() / 60)
                    description = task_data.get('description', 'No description')
                    priority = task_data.get('priority', 'Unknown')
                    reminder_enabled = task_data.get('reminderEnabled', False)
                    reminder_time1 = task_data.get('reminderTime1', None)
                    reminder_time2 = task_data.get('reminderTime2', None)
                    reminder_text = ""
                    if reminder_enabled and (reminder_time1 or reminder_time2):
                        reminders = []
                        if reminder_time1:
                            reminders.append(f"{reminder_time1} minutes before")
                        if reminder_time2:
                            reminders.append(f"{reminder_time2} minutes before")
                        reminder_text = f" with reminders set for {', and '.join(reminders)}"
                    soon = ""
                    try:
                        if (reminder_time1 and minutes_until_deadline <= int(reminder_time1)) or \
                           (reminder_time2 and minutes_until_deadline <= int(reminder_time2)):
                            soon = " It is due soon!"
                    except:
                        pass
                    task_info = (
                        f"{description}, due on {deadline.strftime('%B %d at %I:%M %p')}, "
                        f"priority {priority}{reminder_text}. {soon}"
                    )
                    pending_tasks.append(task_info)
                except ValueError:
                    logger.warning(f"Invalid deadline format for task {task_id}: {deadline_str}")
                    continue
        if not pending_tasks:
            return "You have no pending tasks."
        task_count = len(pending_tasks)
        if task_count == 1:
            response = f"You have one task: {pending_tasks[0]}"
        else:
            response = f"You have {task_count} tasks: {'; '.join(pending_tasks)}"
        return response
    except Exception as e:
        logger.error(f"Error fetching tasks for user {user_id}: {str(e)}")
        return "Sorry, I couldn't retrieve your tasks due to an error."

# ---------------------------
# Reminder file helpers
# ---------------------------
def read_recognition_result(file_path="/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/recognition_result.txt"):
    """Read Name and Emotion from recognition_result.txt with retry on busy file."""
    max_read_retries = 5
    read_retry_delay = 0.5
    for attempt in range(max_read_retries):
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
            name = None
            emotion = None
            for line in lines:
                line = line.strip()
                if line.startswith("Name:"):
                    name = line.replace("Name:", "").strip()
                elif line.startswith("Emotion:"):
                    emotion = line.replace("Emotion:", "").strip()
            if name and emotion:
                return name, emotion
            else:
                print(f"⚠️ Missing Name or Emotion in {file_path}. Using defaults.")
                return None, None
        except FileNotFoundError:
            print(f"⚠️ File {file_path} not found. Using defaults.")
            return None, None
        except IOError as e:
            if e.errno in (errno.EACCES, errno.EBUSY) and attempt < max_read_retries - 1:
                print(f"File busy, retrying in {read_retry_delay}s ({attempt + 1}/{max_read_retries})")
                time.sleep(read_retry_delay)
            else:
                print(f"⚠️ Error reading {file_path} after {max_read_retries} attempts: {e}. Using defaults.")
                return None, None
        except Exception as e:
            print(f"⚠️ Error reading {file_path}: {e}. Using defaults.")
            return None, None

def read_reminder_file(file_path="/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/reminders/reminder_output.txt"):
    """Read the contents of the reminder text file with retry on busy file."""
    max_read_retries = 5
    read_retry_delay = 0.5
    for attempt in range(max_read_retries):
        try:
            with open(file_path, 'r') as file:
                content = file.read().strip()
            return content if content else None
        except FileNotFoundError:
            print(f"⚠️ Reminder file {file_path} not found.")
            return None
        except IOError as e:
            if e.errno in (errno.EACCES, errno.EBUSY) and attempt < max_read_retries - 1:
                print(f"Reminder file busy, retrying in {read_retry_delay}s ({attempt + 1}/{max_read_retries})")
                time.sleep(read_retry_delay)
            else:
                print(f"⚠️ Error reading {file_path} after {max_read_retries} attempts: {e}.")
                return None
        except Exception as e:
            print(f"⚠️ Error reading {file_path}: {e}.")
            return None

def clear_reminder_file(file_path="/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/reminders/reminder_output.txt"):
    """Clear the contents of the reminder text file with retry on busy file."""
    max_write_retries = 5
    write_retry_delay = 0.5
    for attempt in range(max_write_retries):
        try:
            with open(file_path, 'w') as file:
                file.write("")
            print(f"📝 Cleared reminder file {file_path}")
            return True
        except IOError as e:
            if e.errno in (errno.EACCES, errno.EBUSY) and attempt < max_write_retries - 1:
                print(f"Reminder file busy, retrying clear in {write_retry_delay}s ({attempt + 1}/{max_write_retries})")
                time.sleep(write_retry_delay)
            else:
                print(f"⚠️ Error clearing {file_path} after {max_write_retries} attempts: {e}.")
                return False
        except Exception as e:
            print(f"⚠️ Error clearing {file_path}: {e}.")
            return False

def play_reminder_audio(audio_file="/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/reminders/reminder.wav"):
    if not HAS_AUDIO:
        print("[reminder] (no audio) chime skipped")
        return
    try:
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.25)
        pygame.mixer.music.unload()
    except Exception as e:
        print(f"Error playing reminder audio {audio_file}: {e}")


EMOTION_COOLDOWN_SEC = 10
_last_emote_t = 0.0
MATH_STATE = {"last_result": None}
CONT_RE = re.compile(r"(multiply|times|x|divide|over|add|\+|plus|subtract|-|minus)\s+(?:it\s+by\s+)?([\-]?\d+(?:\.\d+)?)", re.IGNORECASE)

def classify_intent(text: str) -> str:
    t = (text or "").lower()
    if re.search(r"show\s+qr|show\s+q\s*r", t):
        return "qr"
    if re.search(r"reminder|task|todo", t):
        return "task"
    if re.search(r"what\s+is\s+.*?(\+|\-|x|×|/)|\d+\s*(\+|\-|x|×|/)\s*\d+", t) or CONT_RE.match(t):
        return "math"
    if re.search(r"play|send message|volume|brightness", t):
        return "command"
    return "chat"

def should_emote(intent: str, explicit_mood: str | None) -> bool:
    global _last_emote_t
    now = time.time()
    if now - _last_emote_t < EMOTION_COOLDOWN_SEC:
        return False
    # Only allow reactions during chat, or when there is an explicit mood during non‑chat
    allow = (intent == "chat" and explicit_mood is not None) or \
            (intent in {"math","task","command","qr"} and explicit_mood is not None)
    if allow:
        _last_emote_t = now
    return allow

def safe_emotion(label: str | None, intent: str) -> str:
    if not label:
        return "Normal"
    if intent in {"math", "task", "command", "qr"} and label == "Love":
        return "Normal"
    return label

def math_continue(text: str) -> str | None:
    m = CONT_RE.match(text or "")
    if not m or MATH_STATE["last_result"] is None:
        return None
    op_word, num = m.groups()
    a = float(MATH_STATE["last_result"])
    x = float(num)
    ow = op_word.lower()
    if ow in {"multiply", "times", "x"}:
        val = a * x
    elif ow in {"divide", "over"}:
        if abs(x) < 1e-12:
            return "Infinity"
        val = a / x
    elif ow in {"add", "+", "plus"}:
        val = a + x
    else:
        val = a - x
    MATH_STATE["last_result"] = val
    iv = int(val)
    return str(iv) if abs(val - iv) < 1e-9 else f"{val:.6g}"

# ---------------------------
# Trigger phrases
# ---------------------------
similar_sounds = [
    "pebo", "vivo", "tivo", "bibo", "pepo", "pipo", "bebo", "tibo", "fibo", "mibo",
    "sibo", "nibo", "vevo", "rivo", "zivo", "pavo", "kibo", "dibo", "lipo", "gibo",
    "zepo", "ripo", "jibo", "wipo", "hipo", "qivo", "xivo", "yibo", "civo", "kivo",
    "nivo", "livo", "sivo", "cepo", "veto", "felo", "melo", "nero", "selo", "telo",
    "dedo", "vepo", "bepo", "tepo", "ribo", "fivo", "gepo", "pobo", "pibo", "google",
    "tune", "tv", "pillow", "people", "keyboard", "pihu", "be bo", "de do", "video",
    "pi lo", "pilo"
]

exit_phrases = ["exit", "shutup", "stop", "shut up"]
exit_pattern = r'\b(goodbye|bye)\s+(' + '|'.join(similar_sounds) + r')\b'

goodbye_messages = [
    "Bye-bye for now! Just whisper my name if needed!",
    "Toodles! I'm just a call away!",
    "Catch you later! I'm only a 'hey PEBO' away!",
    "See ya! I'll be right here if needed!",
    "Bye for now! Ping me anytime!",
    "Going quiet now! Say my name and I'll pop back!",
    "Snuggling into sleep mode... call me if you want to play!",
    "Goodbye for now! Call on me anytime, I'm always listening.",
    "Logging off! Give me a shout and I'll be right there!"
]

# ---------------------------
# Emotion reaction mapping
# ---------------------------

# Unified emotion actions

def normal():
    reset_to_neutral()

# Unified emotion actions
EMO_ACTIONS = {
    "HAPPY":    ("happy",  lambda: run_emotion(express_happy, eyes.Happy)),
    "SAD":      ("sad",    lambda: run_emotion(express_sad,   eyes.Tired)),
    "ANGRY":    ("angry",  lambda: run_emotion(express_angry, eyes.Angry)),
    "LOVE":     ("love",   lambda: run_emotion(express_happy, eyes.Love)),
    "NORMAL":   ("normal", lambda: normal()),
    "TIRED":    ("tired",  lambda: run_emotion(express_tired, eyes.Tired)),
    "CONFUSED": ("normal", lambda: normal()),
    "FEAR":     ("sad",    lambda: run_emotion(express_sad,   eyes.Tired)),
    "STRESSED": ("sad",    lambda: run_emotion(express_sad,   eyes.Tired)),
    "EXCITED":  ("happy",  lambda: run_emotion(express_happy, eyes.Happy)),
}

def react_detected_emotion_label(label: str | None):
    key = (label or "NORMAL").upper()
    _, func = EMO_ACTIONS.get(key, EMO_ACTIONS["NORMAL"])
    return func()
# ---------------------------
# Gemini
# ---------------------------
GOOGLE_API_KEY = "AIzaSyCBkCCR63VV_HCRi_5Qjo9Akx2415eGdp4"
genai.configure(api_key=GOOGLE_API_KEY)

try:
    model = genai.GenerativeModel("gemini-2.0-flash")
except Exception as e:
    print(f"Model initialization failed: {e}")
    model = genai.GenerativeModel("gemini-1.5-flash")

conversation_history = []

async def start_assistant_from_text(prompt_text):
    """Starts Gemini assistant with initial text prompt and controls robot emotions."""
    print(f"💬 Initial Prompt: {prompt_text}")
    conversation_history.clear()

    preface = (
    f"{ROLE_PROMPT}\n"
    "Above is my message. What is your emotion for that message "
    "Happy, Sad, Angry, Normal, or Love? "
    "Only set Love when there is explicit affection toward PEBO "
    "Otherwise choose Happy instead of Love. don't give emojis. "
    "Provide your answer in the format emotion, reply."
    )

    conversation_history.append({"role": "user", "parts": [prompt_text]})

    try:
        response = model.generate_content(conversation_history, generation_config={"max_output_tokens": 40})
    except gcore_exceptions.NotFound as e:
        print(f"Model not found: {e}. Check for deprecation and update model name.")
        response = model.generate_content(conversation_history, generation_config={"max_output_tokens": 40})

    reply = (getattr(response, "text", "") or "").strip()
    emotion = "Normal"
    answer = reply
    try:
        match = re.match(r'\[(Happy|Sad|Angry|Normal|Love),(.+?)\]', reply)
        if match:
            emotion, answer = match.groups()
            print(f"{emotion}: {answer}")
        else:
            print(f"Gemini: {reply} (No emotion detected, assuming Normal)")
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")

    valid_emotions = {"Happy", "Sad", "Angry", "Normal", "Love"}
    emotion_methods = {
        "Happy": happy,
        "Sad": sad,
        "Angry": angry,
        "Normal": normal,
        "Love": love
    }
    emotion_method = emotion_methods.get(emotion if emotion in valid_emotions else "Normal")
    emotion_task = asyncio.to_thread(emotion_method)
    # Before speaking the LLM answer:
    answer = sanitize_llm_text(answer)

    voice_task = speak_text(answer)
    await asyncio.gather(emotion_task, voice_task)
    conversation_history.append({"role": "model", "parts": [prepare_spoken_text(answer)]})

# ---------------------------
# Main conversational loop utilities
# ---------------------------
async def handle_tasks_intent():
    try:
        with open(JSON_CONFIG_PATH, 'r') as config_file:
            config = json.load(config_file)
        user_id = config.get('userId')
        if not user_id:
            logger.error("Missing userId in config file")
            await speak_text("Sorry, I couldn't find your user ID.")
            await asyncio.to_thread(normal)
            return
        task_response = fetch_user_tasks(user_id)
        await asyncio.gather(
            speak_text(task_response),
            asyncio.to_thread(normal)
        )
    except FileNotFoundError:
        logger.error(f"Config file {JSON_CONFIG_PATH} not found")
        await speak_text("Sorry, I couldn't read the user configuration.")
        await asyncio.to_thread(normal)
    except Exception as e:
        logger.error(f"Error fetching tasks: {str(e)}")
        await speak_text("Sorry, there was an error retrieving your tasks.")
        await asyncio.to_thread(normal)

async def handle_song_intent(user_input: str):
    song_match = re.match(r'^play\s+a\s+song\s+(.+)$', user_input, re.IGNORECASE)
    max_song_attempts = 1
    if song_match:
        song_input = song_match.group(1).strip()
    elif user_input in ("play a song", "play song"):
        await speak_text("What song should I play?")
        await asyncio.to_thread(normal)
        song_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
        if song_input is None:
            await speak_text("Sorry, I couldn't get the song name. Let's try something else.")
            await asyncio.to_thread(normal)
            return
    else:
        return

    for attempt in range(max_song_attempts):
        if song_input:
            await speak_text(f"Your song is {song_input}. Is that correct?")
            await asyncio.to_thread(normal)
            confirmation = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
            if confirmation is None:
                if attempt < max_song_attempts - 1:
                    await speak_text(f"I didn't hear you. Is {song_input} the correct song?")
                    await asyncio.to_thread(normal)
                    continue
                else:
                    await speak_text("Sorry, I couldn't confirm the song. Let's try something else.")
                    await asyncio.to_thread(normal)
                    break
            confirmation = confirmation.lower()
            if any(pos in confirmation for pos in ["yes", "yeah", "yep", "correct", "right", "ok", "okay"]):
            # when confirmation is positive and a song should play:
                await asyncio.to_thread(play_music, song_input, None, TOUCH_PIN)
                await asyncio.to_thread(normal)
                break
            elif any(neg in confirmation for neg in ["no", "nope", "not", "wrong", "incorrect"]):
                if attempt < max_song_attempts - 1:
                    await speak_text("Okay, what song should I play?")
                    await asyncio.to_thread(normal)
                    song_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
                    if song_input is None:
                        if attempt < max_song_attempts - 2:
                            await speak_text("I didn't catch that. What song should I play?")
                            await asyncio.to_thread(normal)
                            continue
                        else:
                            await speak_text("Sorry, I couldn't get the song name. Let's try something else.")
                            await asyncio.to_thread(normal)
                            break
                else:
                    await speak_text("Sorry, I couldn't get the right song after a few tries. Let's try something else.")
                    await asyncio.to_thread(normal)
            else:
                if attempt < max_song_attempts - 1:
                    await speak_text(f"I didn't understand. Is {song_input} the correct song?")
                    await asyncio.to_thread(normal)
                    continue
                else:
                    await speak_text("Sorry, I couldn't confirm the song. Let's try something else.")
                    await asyncio.to_thread(normal)
                    break
        else:
            if attempt < max_song_attempts - 1:
                await speak_text("I didn't catch that. What song should I play?")
                await asyncio.to_thread(normal)
                song_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
            else:
                await speak_text("Sorry, I couldn't get the song name. Let's try something else.")
                await asyncio.to_thread(normal)
                break

async def handle_qr_intent():
    try:
        with open("/home/pi/pebo_config.json", 'r') as f:
            config = json.load(f)
        device_id = config.get("deviceId")
        if not str(device_id):
            await speak_text("Error: Invalid device ID in configuration")
            return
    except Exception as e:
        await speak_text(f"Error reading device ID: {str(e)}")
        return

    await asyncio.gather(
        speak_text("Showing QR now, scan this using the user PEBO mobile app"),
        asyncio.to_thread(run_emotion, None, lambda stop_event: eyes.QR(device_id, stop_event=stop_event), duration=15)
    )
    await asyncio.to_thread(normal)

async def handle_interdevice_communication():
    try:
        with open(JSON_CONFIG_PATH, 'r') as config_file:
            config = json.load(config_file)
        current_ssid = config.get('ssid')
        current_device_id = config.get('deviceId')
        user_id = config.get('userId')
        if not current_ssid or not current_device_id or not user_id:
            logger.error("Missing SSID, deviceId, or userId in config file")
            await speak_text("Sorry, I couldn't read the device configuration.")
            await asyncio.to_thread(normal)
            return

        current_ip = get_ip_address()
        if not current_ip:
            logger.error("No Wi-Fi connection detected")
            await speak_text("Cannot initiate communication: Not connected to Wi-Fi.")
            await asyncio.to_thread(normal)
            return

        users_ref = db.reference('users')
        users = users_ref.get()
        if not users:
            logger.info("No users found in Firebase")
            await speak_text("No other devices found.")
            await asyncio.to_thread(normal)
            return

        same_wifi_devices = []
        for uid, user_data in users.items():
            if 'peboDevices' in user_data:
                for device_id, device_data in user_data['peboDevices'].items():
                    if (device_data.get('ssid') == current_ssid and
                        device_data.get('ipAddress') != 'Disconnected' and
                        device_id != current_device_id):
                        same_wifi_devices.append({
                            'user_id': uid,
                            'device_id': device_id,
                            'ip_address': device_data.get('ipAddress'),
                            'location': device_data.get('location', 'Unknown')
                        })

        if not same_wifi_devices:
            logger.info(f"No devices found on SSID {current_ssid}")
            await speak_text(f"No other devices found on Wi-Fi {current_ssid}.")
            await asyncio.to_thread(normal)
            return

        locations = [device['location'] for device in same_wifi_devices]
        if len(locations) == 1:
            locations_str = locations[0]
        else:
            locations_str = ", ".join(locations[:-1]) + f", or {locations[-1]}"
        print(f"Which device would you like to connect in {locations_str}?")
        await speak_text(f"Which device would you like to connect in {locations_str}?")
        await asyncio.to_thread(normal)

        location_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
        if not location_input:
            await speak_text("Sorry, I didn't catch that. Let's try something else.")
            await asyncio.to_thread(normal)
            return

        selected_device = None
        for device in same_wifi_devices:
            if location_input.lower() in device['location'].lower():
                selected_device = device
                break

        if selected_device:
            print(f"Selected Device: Location={selected_device['location']}, IP={selected_device['ip_address']}")
            await speak_text(f"Connected to PEBO in {selected_device['location']}. Double-tap to stop communication.")
            await asyncio.to_thread(normal)

            GPIO.setmode(GPIO.BCM)
            GPIO.setup(TOUCH_PIN, GPIO.IN)

            audiothread = threading.Thread(
                target=start_audio_node,
                args=(8888, selected_device["ip_address"], 8889, TOUCH_PIN),
                daemon=True
            )
            audiothread.start()
            await asyncio.to_thread(audiothread.join)
            await speak_text("Communication stopped. Anything else?")
            await asyncio.to_thread(normal)

        else:
            await speak_text("Sorry, I couldn't find a device in that location. Let's try something else.")
            await asyncio.to_thread(normal)
    except FileNotFoundError:
        logger.error(f"Config file {JSON_CONFIG_PATH} not found")
        await speak_text("Sorry, I couldn't read the device configuration.")
        await asyncio.to_thread(normal)
    except Exception as e:
        logger.error(f"Error in interdevice communication: {str(e)}")
        await speak_text("Sorry, there was an error connecting to other devices.")
        await asyncio.to_thread(normal)

# ---------------------------
# Assistant loop
# ---------------------------
async def start_loop():
    global CURRENT_USER_NAME, LAST_MOOD, LAST_TOPICS
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
            firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
            logger.info("Firebase initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {str(e)}")
        await speak_once("Sorry, I couldn't connect to the device database.")
        await asyncio.to_thread(normal)
        return

    failed_attempts, max_attempts = 0, 5  # keep session alive longer

    # Simple arithmetic fast-path
    MATH_RE = re.compile(r'^\s*(what\s+is\s+)?(-?\d+(\.\d+)?)\s*([+\-*/x])\s*(-?\d+(\.\d+)?)\s*\??\s*$', re.IGNORECASE)
    def quick_math_answer(text: str):
        m = MATH_RE.match(text or "")
        if not m: return None
        a = float(m.group(2)); b = float(m.group(5)); op = m.group(4).lower().replace('x','*')
        try:
            val = a+b if op=='+' else a-b if op=='-' else a*b if op=='*' else a/b
            vi = int(val);  return str(vi) if abs(val-vi) < 1e-9 else f"{val:.6g}"
        except: return None

    while True:
        # Reminders
        reminder_text = read_reminder_file()
        if reminder_text:
            try:
                play_reminder_audio()
                await speak_once(reminder_text)
            finally:
                clear_reminder_file()
            failed_attempts = 0

        # Listen
        user_input = await asyncio.get_event_loop().run_in_executor(
            None, lambda: listen(recognizer, mic, timeout=12, phrase_time_limit=10, retries=2)
        )
        if user_input is None:
            failed_attempts += 1
            if failed_attempts >= max_attempts:
                failed_attempts = 0
            continue
        failed_attempts = 0

        # Intents
        low = (user_input or "").lower().strip()
        if low in ["what are reminders", "list reminders", "show reminders", "tell me my reminders", "show remind", "list remind"]:
            await handle_tasks_intent(); continue
        await handle_song_intent(user_input)
        if low in ["show q r", "show me q r", "show qr", "show me qr", "show me q", "show q"]:
            await handle_qr_intent(); continue
        if low == "send message":
            await handle_interdevice_communication(); continue
        if low in exit_phrases or re.search(exit_pattern, user_input, re.IGNORECASE):
            await speak_once(random.choice(goodbye_messages))
            await asyncio.to_thread(normal)
            break

        # Math fast-path
        ans = quick_math_answer(user_input)
        if ans is not None:
            MATH_STATE["last_result"] = float(ans) if re.match(r'^-?\d+(\.0+)?$', ans) else None
            await asyncio.gather(asyncio.to_thread(normal), speak_once(ans))
            LAST_TOPICS.append(f"math:{user_input.strip()[:30]}"); LAST_TOPICS = LAST_TOPICS[-5:]; save_memory()
            continue

        # Math continuation
        cont = math_continue(user_input)
        if cont is not None:
            await asyncio.gather(asyncio.to_thread(normal), speak_once(cont))
            LAST_TOPICS.append(f"math-continue:{user_input.strip()[:30]}"); LAST_TOPICS = LAST_TOPICS[-5:]; save_memory()
            continue

        # Update name/mood memory from explicit text only
        maybe = extract_name_from_text(user_input)
        if maybe: CURRENT_USER_NAME = maybe
        detected = extract_emotion_from_text(user_input)  # explicit sentiment words only

        # Classify intent
        intent = classify_intent(user_input)  # e.g., "chat","math","task","command","qr"

        # STRICT gating: Only animate if there is an explicit emotion AND it's chat.
        # For non-chat (math/task/command/qr), allow only if explicit emotion exists.
        allow_anim = False
        if detected:
            if intent == "chat":
                allow_anim = True
            elif intent in {"math", "task", "command", "qr"}:
                allow_anim = True

        # Persist last mood only if explicit
        if detected:
            LAST_MOOD = detected
        save_memory()

        # LLM concise, stateless turn — ignore model emotion for animation
        silent_ctx = f"(user_name={CURRENT_USER_NAME or 'Yohan'}) (internal_mood={LAST_MOOD or 'None'}) (topics={';'.join(LAST_TOPICS[-3:])})"
        full_user_input = (
            f"{ROLE_PROMPT}\n{silent_ctx}\n{user_input}\n"
            "Respond empathetically; do not name emotions or describe actions. "
            "Return exactly as [emotion,answer] where emotion ∈ {Happy,Sad,Angry,Normal,Love}."
        )
        response = model.generate_content(
            [{"role": "user", "parts": [full_user_input]}],
            generation_config={"max_output_tokens": 64}
        )
        reply = (getattr(response, "text", "") or "").strip()
        m = re.match(r'\[(Happy|Sad|Angry|Normal|Love),(.+?)\]', reply)
        if not m:
            retry = model.generate_content(
                [{"role":"user","parts":[full_user_input + "\nSTRICT: Output only [emotion,answer]."]}],
                generation_config={"max_output_tokens": 64}
            )
            reply = (getattr(retry, "text", "") or "").strip()
            m = re.match(r'\[(Happy|Sad|Angry|Normal|Love),(.+?)\]', reply)
        model_emotion, answer = (m.groups() if m else ("Normal", reply))
        answer = sanitize_llm_text(answer)

        # Final emotion for animation: ignore model_emotion; only explicit + safe mapping
        final_emotion = safe_emotion(detected, intent) if allow_anim else "Normal"

        # Speak + eyes/hands
        if final_emotion == "Normal":
            await asyncio.gather(asyncio.to_thread(normal), speak_once(answer))
        else:
            await asyncio.gather(
                asyncio.to_thread(react_detected_emotion_label, final_emotion),
                speak_once(answer)
            )

        # Track topic for continuity (short ring buffer)
        LAST_TOPICS.append(user_input.strip()[:50]); LAST_TOPICS = LAST_TOPICS[-5:]; save_memory()


# ---------------------------
# Triggered starts
# ---------------------------
# monitor_for_trigger(): wake on phrase, greet once, then start_loop
# monitor_for_trigger(): wake on phrase, greet once, then start_loop
async def monitor_for_trigger(name, emotion):
    global SESSION_ACTIVE, CURRENT_USER_NAME

    initialize_hardware()
    normal()  # idle eyes at boot

    while True:
        print("🎧 Waiting for trigger phrase (e.g., 'hi PEBO', 'PEBO')...")
        text = listen(recognizer, mic)
        if not text:
            continue

        # Allow QR during idle
        qr_pattern = r"\bshow\s+(?:me\s+)?q\s*r\b|\bshow\s+q\b"
        if re.search(qr_pattern, text, re.IGNORECASE):
            await handle_qr_intent()
            continue

        # If already in a session, ignore further triggers
        if SESSION_ACTIVE:
            continue

        # Require wake phrase to start
        trigger_pattern = r"\b((?:hi|hey|hello)\s+)?(" + "|".join(re.escape(s) for s in similar_sounds) + r")\b"
        if not re.search(trigger_pattern, text, re.IGNORECASE):
            continue

        SESSION_ACTIVE = True
        try:
            # Resolve/remember name
            if name and str(name).lower() != "none":
                CURRENT_USER_NAME = name
            maybe = extract_name_from_text(text)
            if maybe:
                CURRENT_USER_NAME = maybe
            save_memory()

            # Greeting: wave + happy + voice together to reduce latency
            greeting = f"Hi {CURRENT_USER_NAME or 'Yohan'}, I'm your Pebo, how's it going?"
            await asyncio.gather(
                asyncio.to_thread(say_hi),
                asyncio.to_thread(happy),
                speak_once(greeting)
            )

            # Conversation loop (no re-intros)
            await start_loop()

        finally:
            SESSION_ACTIVE = False
            normal()


# monitor_start(): immediate greet on boot-wake, then start_loop
async def monitor_start(name, emotion):
    global SESSION_ACTIVE, CURRENT_USER_NAME

    initialize_hardware()
    normal()
    try:
        print("🎧 Waiting for initial speech input...")

        SESSION_ACTIVE = True
        if name and str(name).lower() != "none":
            CURRENT_USER_NAME = name
        save_memory()

        greeting = f"Hi {CURRENT_USER_NAME or 'Yohan'}, I'm Pebo, your buddy."
        await asyncio.gather(
            asyncio.to_thread(say_hi),
            asyncio.to_thread(happy),
            speak_once(greeting)
        )

        await start_loop()
    finally:
        SESSION_ACTIVE = False
        normal()
        print("🖥️ Cleaning up in monitor_start...")



# monitor_new(): prefer this as the main entry; identical greet-once flow
# monitor_new(): prefer this as the main entry; greet-once flow
async def monitor_new():
    global SESSION_ACTIVE, CURRENT_USER_NAME

    load_memory()
    initialize_hardware()
    normal()

    while True:
        print("🎧 Waiting for trigger phrase (e.g., 'hi PEBO', 'PEBO')...")
        # Optional cam result (ignored if skipping checks)
        cam_name, cam_emotion = (None, None) if SKIP_USER_CHECK else read_recognition_result()

        text = listen(recognizer, mic)
        if not text:
            continue

        # Allow QR during idle
        if re.search(r"\bshow\s+(?:me\s+)?q\s*r\b|\bshow\s+q\b", text, re.IGNORECASE):
            await handle_qr_intent()
            continue

        if SESSION_ACTIVE:
            continue

        # Wake phrase required
        trig = r"\b((?:hi|hey|hello)\s+)?(" + "|".join(re.escape(s) for s in similar_sounds) + r")\b"
        if not re.search(trig, text, re.IGNORECASE):
            continue

        SESSION_ACTIVE = True
        try:
            # Resolve/remember name (camera or speech)
            if cam_name and str(cam_name).lower() != "none":
                CURRENT_USER_NAME = cam_name
            maybe = extract_name_from_text(text)
            if maybe:
                CURRENT_USER_NAME = maybe
            save_memory()

            # Greeting sequence: wave + happy + voice together
            greeting = f"Hi {CURRENT_USER_NAME or 'Yohan'}, I'm Pebo, your buddy."
            await asyncio.gather(
                asyncio.to_thread(say_hi),
                asyncio.to_thread(happy),
                speak_once(greeting)
            )

            # Enter conversation loop
            await start_loop()

        finally:
            SESSION_ACTIVE = False
            normal()

# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    try:
        # Default simulated values; in production these come from recognition_result.txt
        name = "Bhagya"
        emotion = "Happy"
        asyncio.run(monitor_new())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    finally:
        print("Program terminated")

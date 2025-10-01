#!/usr/bin/env python3
"""
PEBO Assistant (stable, emotion-gated, no-repeat)

- Prevents repeated answers: dedupe spoken replies and avoid cached audio replays
- Emotion reactions only when explicitly detected from user speech or camera; otherwise neutral
- Neutral tone for serious intents (math/tasks/commands/QR); empathetic only for emotional chat
- Strict JSON LLM protocol with fallbacks, never speaks emotion labels
- Robust eyes/arms threading, Default idle, and cooldown to avoid spam
- Edge TTS with retry + ffmpeg boost + offline espeak fallback
- Keeps: reminders, tasks (Firebase), QR, inter-device audio, math fast/continue, songs
"""

import os
import re
import time
import json
import errno
import random
import socket
import fcntl
import struct
import asyncio
import logging
import threading
import tempfile
import subprocess
from datetime import datetime, timezone
from collections import deque
from typing import Optional, Tuple

import pygame
import edge_tts
import speech_recognition as sr
import whisper
import sounddevice as sd
import numpy as np
import scipy.io.wavfile
import dateutil.parser

import board
import busio
import smbus
import RPi.GPIO as GPIO

import google.generativeai as genai
from google.api_core import exceptions as gcore_exceptions

import firebase_admin
from firebase_admin import credentials, db

from arms.arms_pwm import (
    say_hi, express_tired, express_happy, express_sad, express_angry,
    reset_to_neutral, scan_i2c_devices, angle_to_pulse_value, set_servos, smooth_move
)
from display.eyes_qr import RoboEyesDual
from interaction.play_song1 import play_music
from Communication.sender import AudioNode, start_audio_node

# ---------------------------
# Logging
# ---------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/ipconfig/store_ip.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------
# Config/Constants
# ---------------------------
ASSISTANT_NAME = "pebo"

# Env flags
SKIP_USER_CHECK = bool(int(os.getenv("PEBO_SKIP_USER_CHECK", "1")))  # 1=skip user gating, 0=enable

# Files
MEM_PATH = "/home/pi/pebo_memory.json"
JSON_CONFIG_PATH = "/home/pi/pebo_config.json"
RECOG_FILE = "/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/recognition_result.txt"
REMINDER_FILE = "/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/reminders/reminder_output.txt"
REMINDER_WAV = "/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/reminders/reminder.wav"

# Firebase
SERVICE_ACCOUNT_PATH = "/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/ipconfig/firebase_config.json"
DATABASE_URL = "https://pebo-task-manager-767f3-default-rtdb.asia-southeast1.firebasedatabase.app"

# GPIO
TOUCH_PIN = 17  # Pin 11
LED_PIN = 18    # Pin 12
GPIO.setmode(GPIO.BCM)
GPIO.setup(TOUCH_PIN, GPIO.IN)

# I2C / Eyes
PCA9685_ADDR = 0x40
LEFT_EYE_ADDRESS = 0x3C
RIGHT_EYE_ADDRESS = 0x3D
i2c = None
eyes = None
current_eye_thread = None
stop_event = None

# Audio init guard
HAS_AUDIO = True
try:
    pygame.mixer.init()
except Exception as e:
    HAS_AUDIO = False
    print(f"[audio] pygame init failed, running degraded: {e}")

# Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
if not GOOGLE_API_KEY:
    logger.warning("GOOGLE_API_KEY not set; configure environment for Gemini access")
genai.configure(api_key=GOOGLE_API_KEY or "DUMMY")
try:
    model = genai.GenerativeModel("gemini-2.0-flash")
except Exception as e:
    print(f"Model initialization failed: {e}")
    model = genai.GenerativeModel("gemini-1.5-flash")

# ---------------------------
# Persona / safety / parsing
# ---------------------------
MAX_SPOKEN_TOKENS = 25
FORBIDDEN_PHRASES = [
    "emotional companion", "therapist", "psychologist",
]
EMOTION_TERMS = [
    "happy", "sad", "angry", "love", "normal", "fear", "confused",
    "emotion", "mood", "feeling", "feelings", "you look", "you sound",
]
EMOTION_COOLDOWN_SEC = 10
_last_emote_t = 0.0

ROLE_PROMPT_NEUTRAL = (
    "Act as 'pebo'â€”concise and neutral; avoid stage directions; "
    "do not use emotional language; answer directly in <=25 tokens."
)
ROLE_PROMPT_EMPATH = (
    "Act as 'pebo'â€”briefly supportive; avoid stage directions; "
    "never name emotions; reply in <=25 tokens with gentle encouragement."
)
JSON_INSTRUCTION = (
    'Return only a minified JSON object: {"emotion":"Happy|Sad|Angry|Normal|Love","answer":"<reply>"} '
    "No extra text."
)
STAGE_RE = re.compile(r"\s*\(*\b(eyes?|hands?|head|nods?|blinks?|gestures?|sighs?|smiles?)\b.*?\)*[.?!]?", re.IGNORECASE)

def sanitize_llm_text(t: str) -> str:
    t = STAGE_RE.sub("", t or "").strip()
    return t if t else "Here to help."

def _remove_forbidden_phrases(text: str) -> str:
    out = text
    for p in FORBIDDEN_PHRASES:
        out = re.sub(re.escape(p), "", out, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", out).strip()

def _sentence_split(text: str):
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p for p in parts if p]

def _redact_emotion_mentions(text: str) -> str:
    sentences = _sentence_split(text)
    kept = []
    for s in sentences:
        if any(re.search(rf"\b{re.escape(term)}\b", s, re.IGNORECASE) for term in EMOTION_TERMS):
            continue
        kept.append(s)
    cleaned = " ".join(kept).strip()
    return cleaned if cleaned else "Okay."

def _trim_to_tokens(text: str, max_tokens: int = MAX_SPOKEN_TOKENS) -> str:
    words = re.findall(r"\S+", text or "")
    if len(words) <= max_tokens:
        return (text or "").strip()
    return " ".join(words[:max_tokens]).rstrip(",.;:") + "â€¦"

def prepare_spoken_text(text: str) -> str:
    text = _remove_forbidden_phrases(text)
    text = _redact_emotion_mentions(text)
    text = _trim_to_tokens(text, MAX_SPOKEN_TOKENS)
    return text

# Recent answers dedupe
RECENT_ANSWERS = deque(maxlen=8)

# Serialize TTS playback
speak_lock = asyncio.Lock()

async def speak_text(text: str):
    safe_text = prepare_spoken_text(text)
    # Deduplicate repeated answers
    if safe_text in RECENT_ANSWERS:
        print(f"[speak] deduped repeat: {safe_text!r}")
        return
    RECENT_ANSWERS.append(safe_text)

    if not HAS_AUDIO:
        print(f"[speak] (no audio) {safe_text}")
        return

    # pad ultraâ€‘short content so Edge returns audio
    if len(re.findall(r"\w", safe_text)) < 2:
        safe_text = f"The answer is {safe_text}."

    voices = ["en-US-JennyNeural", "en-US-GuyNeural", "en-GB-LibbyNeural"]
    # Unique filenames to avoid cached replay
    rnd = str(int(time.time() * 1000)) + "-" + str(random.randint(1000,9999))
    filename = f"response-{rnd}.mp3"
    boosted_file = f"boosted_response-{rnd}.mp3"
    last_err = None

    def amplify_audio(input_file, output_file, gain_db=20):
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_file, "-filter:a", f"volume={gain_db}dB", output_file],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

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
        except Exception as e:
            last_err = e
            await asyncio.sleep(0.2)
            continue

    # Offline fallback
    try:
        fallback_wav = f"fallback_tts-{rnd}.wav"
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
        print(f"[tts] All TTS attempts failed: {last_err} | Fallback error: {e2} | text={safe_text!r}")

async def speak_once(text: str):
    async with speak_lock:
        await speak_text(text)

# ---------------------------
# Speech recognition
# ---------------------------
recognizer = sr.Recognizer()
mic = sr.Microphone()
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
) -> Optional[str]:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.output(LED_PIN, GPIO.LOW)

    for attempt in range(retries + 1):
        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=calibrate_duration)
                print("ðŸŽ¤ Listeningâ€¦ (attempt", attempt + 1, ")")
                GPIO.output(LED_PIN, GPIO.HIGH)
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                GPIO.output(LED_PIN, GPIO.LOW)

            try:
                text = recognizer.recognize_google(audio, language=language)
                text = (text or "").strip().lower()
                if text:
                    print(f"ðŸ—£ï¸ You said: {text}")
                    GPIO.cleanup()
                    return text
            except sr.UnknownValueError:
                print("ðŸ¤” Sorryâ€”couldnâ€™t understand that.")
            except sr.RequestError as e:
                print(f"âš ï¸ Google speech service error ({e}). Falling back to offline engineâ€¦")
                try:
                    text = recognizer.recognize_sphinx(audio, language=language)
                    text = (text or "").strip().lower()
                    if text:
                        print(f"ðŸ—£ï¸ (Offline) You said: {text}")
                        GPIO.cleanup()
                        return text
                except Exception as sphinx_err:
                    print(f"âŒ Offline engine failed: {sphinx_err}")
        except sr.WaitTimeoutError:
            print("â³ Timed out waiting for speech.")
            GPIO.output(LED_PIN, GPIO.LOW)
        except Exception as mic_err:
            print(f"ðŸŽ¤ Mic/Audio error: {mic_err}")
            GPIO.output(LED_PIN, GPIO.LOW)

        if attempt < retries:
            time.sleep(0.5)

    print("ðŸ˜• No intelligible speech captured.")
    GPIO.output(LED_PIN, GPIO.LOW)
    GPIO.cleanup()
    return None

# Optional Whisper capture
whisper_model = whisper.load_model("base")

def listen_whisper(duration=1, sample_rate=16000) -> Optional[str]:
    print("ðŸŽ¤ Listening with Whisperâ€¦")
    audio_path = None
    try:
        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
        sd.wait()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
            scipy.io.wavfile.write(tmpfile.name, sample_rate, recording)
            audio_path = tmpfile.name
        result = whisper_model.transcribe(audio_path)
        text = (result.get("text", "") or "").strip().lower()
        if text:
            print(f"ðŸ—£ï¸ You said (Whisper): {text}")
            return text
        else:
            print("ðŸ¤” No intelligible speech detected.")
            return None
    except Exception as e:
        print(f"âŒ Whisper error: {e}")
        return None
    finally:
        try:
            if audio_path:
                os.remove(audio_path)
        except Exception:
            pass

# ---------------------------
# Eyes / Arms
# ---------------------------
def initialize_hardware():
    global i2c, eyes
    i2c = busio.I2C(board.SCL, board.SDA)
    eyes = RoboEyesDual(LEFT_EYE_ADDRESS, RIGHT_EYE_ADDRESS)
    eyes.begin(128, 64, 40)

def run_emotion(arm_func, eye_func, duration=1.0):
    """Run arm movement and eye expression simultaneously, then return to normal mode."""
    global current_eye_thread, stop_event
    # stop any existing eye animation
    if stop_event:
        try: stop_event.set()
        except Exception: pass
    if current_eye_thread:
        try: current_eye_thread.join(timeout=1.0)
        except Exception: pass
    stop_event = threading.Event()
    current_eye_thread = threading.Thread(target=eye_func, args=(stop_event,))
    current_eye_thread.daemon = True
    current_eye_thread.start()

    if arm_func:
        try: arm_func()
        except Exception as e: print(f"[arms] error: {e}")

    time.sleep(duration)

    # stop that eye animation
    try: stop_event.set()
    except Exception: pass
    if current_eye_thread:
        try: current_eye_thread.join(timeout=1.0)
        except Exception: pass
    current_eye_thread = None
    stop_event = None
    normal()  # return to idle eyes

def normal():
    print("Expressing Normal")
    global current_eye_thread, stop_event
    # stop any running eye thread before starting Default
    if stop_event:
        try: stop_event.set()
        except Exception: pass
    if current_eye_thread:
        try: current_eye_thread.join(timeout=1.0)
        except Exception: pass
    stop_event = threading.Event()
    t = threading.Thread(target=eyes.Default, args=(stop_event,))
    t.daemon = True
    t.start()

def hi():
    print("Expressing Hi")
    run_emotion(say_hi, eyes.Happy)

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
    print(f"Expressing QR with device ID: {device_id}")
    run_emotion(None, lambda se: eyes.QR(device_id, stop_event=se), duration=15)

def cleanup():
    global i2c, eyes, current_eye_thread, stop_event
    print("ðŸ–¥ï¸ Cleaning up resources...")
    try:
        if stop_event:
            stop_event.set()
        if current_eye_thread:
            current_eye_thread.join(timeout=1.0)
            current_eye_thread = None
    except Exception:
        pass
    try:
        reset_to_neutral()
        eyes.display_left.fill(0); eyes.display_left.show()
        eyes.display_right.fill(0); eyes.display_right.show()
        print("ðŸ–¥ï¸ Displays cleared")
    except Exception as e:
        print(f"ðŸ–¥ï¸ Error clearing displays: {e}")
    try:
        i2c.deinit()
        print("ðŸ–¥ï¸ I2C bus deinitialized")
    except Exception as e:
        print(f"ðŸ–¥ï¸ Error deinitializing I2C bus: {e}")
    print("ðŸ–¥ï¸ Cleanup complete")

# ---------------------------
# Memory / name extraction
# ---------------------------
NAME_RE = re.compile(r"\b(my\s+name\s+is|i\s*am|i'm)\s+([A-Za-z]{2,30})\b", re.IGNORECASE)
SESSION_ACTIVE: bool = False
CURRENT_USER_NAME: Optional[str] = None
LAST_MOOD: Optional[str] = None
LAST_TOPICS: list[str] = []

def extract_name_from_text(text: str) -> Optional[str]:
    m = NAME_RE.search(text or "")
    return m.group(2).strip().title() if m else None

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

# ---------------------------
# Reminders
# ---------------------------
def read_recognition_result(file_path=RECOG_FILE):
    max_read_retries = 5
    delay = 0.5
    for attempt in range(max_read_retries):
        try:
            with open(file_path, "r") as file:
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
                print(f"âš ï¸ Missing Name or Emotion in {file_path}. Using defaults.")
                return None, None
        except FileNotFoundError:
            print(f"âš ï¸ File {file_path} not found. Using defaults.")
            return None, None
        except IOError as e:
            if e.errno in (errno.EACCES, errno.EBUSY) and attempt < max_read_retries - 1:
                print(f"File busy, retrying in {delay}s ({attempt + 1}/{max_read_retries})")
                time.sleep(delay)
            else:
                print(f"âš ï¸ Error reading {file_path} after {max_read_retries} attempts: {e}. Using defaults.")
                return None, None
        except Exception as e:
            print(f"âš ï¸ Error reading {file_path}: {e}. Using defaults.")
            return None, None

def read_reminder_file(file_path=REMINDER_FILE):
    max_read_retries = 5
    delay = 0.5
    for attempt in range(max_read_retries):
        try:
            with open(file_path, "r") as file:
                content = file.read().strip()
                return content if content else None
        except FileNotFoundError:
            print(f"âš ï¸ Reminder file {file_path} not found.")
            return None
        except IOError as e:
            if e.errno in (errno.EACCES, errno.EBUSY) and attempt < max_read_retries - 1:
                print(f"Reminder file busy, retrying in {delay}s ({attempt + 1}/{max_read_retries})")
                time.sleep(delay)
            else:
                print(f"âš ï¸ Error reading {file_path} after {max_read_retries} attempts: {e}.")
                return None
        except Exception as e:
            print(f"âš ï¸ Error reading {file_path}: {e}.")
            return None

def clear_reminder_file(file_path=REMINDER_FILE):
    max_write_retries = 5
    delay = 0.5
    for attempt in range(max_write_retries):
        try:
            with open(file_path, "w") as file:
                file.write("")
            print(f"ðŸ“ Cleared reminder file {file_path}")
            return True
        except IOError as e:
            if e.errno in (errno.EACCES, errno.EBUSY) and attempt < max_write_retries - 1:
                print(f"Reminder file busy, retrying clear in {delay}s ({attempt + 1}/{max_write_retries})")
                time.sleep(delay)
            else:
                print(f"âš ï¸ Error clearing {file_path} after {max_write_retries} attempts: {e}.")
                return False
        except Exception as e:
            print(f"âš ï¸ Error clearing {file_path}: {e}.")
            return False

def play_reminder_audio(audio_file=REMINDER_WAV):
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

                    reminders = []
                    if reminder_enabled and (reminder_time1 or reminder_time2):
                        if reminder_time1:
                            reminders.append(f"{reminder_time1} minutes before")
                        if reminder_time2:
                            reminders.append(f"{reminder_time2} minutes before")
                    reminder_text = f" with reminders set for {', and '.join(reminders)}" if reminders else ""

                    soon = ""
                    try:
                        if (reminder_time1 and minutes_until_deadline <= int(reminder_time1)) or \
                           (reminder_time2 and minutes_until_deadline <= int(reminder_time2)):
                            soon = " It is due soon!"
                    except Exception:
                        pass

                    task_info = (
                        f"{description}, due on {deadline.strftime('%B %d at %I:%M %p')}, "
                        f"priority {priority}{reminder_text}.{soon}"
                    )
                    pending_tasks.append(task_info)
                except ValueError:
                    logger.warning(f"Invalid deadline format for task {task_id}: {deadline_str}")
                    continue

        if not pending_tasks:
            return "You have no pending tasks."
        task_count = len(pending_tasks)
        if task_count == 1:
            return f"You have one task: {pending_tasks[0]}"
        else:
            return f"You have {task_count} tasks: {'; '.join(pending_tasks)}"
    except Exception as e:
        logger.error(f"Error fetching tasks for user {user_id}: {str(e)}")
        return "Sorry, I couldn't retrieve your tasks due to an error."


async def start_assistant_from_text(prompt_text):
    """Starts Gemini assistant with initial prompt and controls robot emotions."""
    print(f"\U0001F4AC Initial Prompt: {prompt_text}")
    conversation_history.clear()

    full_prompt = (
        f"{prompt_text}\n"
        "Above is my message. What is your emotion for that message "
        "(Happy, Sad, Angry, Normal, or Love)? If my message includes words "
        "like 'love', 'loving', 'beloved', 'adore', 'affection', 'cute', "
        "'adorable', 'sweet', or 'charming', or if the overall sentiment feels "
        "loving or cute, set your emotion to Love. Otherwise, determine the "
        "appropriate emotion based on the message's context. Provide your answer "
        "in the format [emotion, reply], where 'emotion' is one of the specified "
        "emotions and 'reply' is your response to my message."
    )
    conversation_history.append({"role": "user", "parts": [full_prompt]})

    try:
        response = model.generate_content(conversation_history, generation_config={"max_output_tokens": 20})
    except google.api_core.exceptions.NotFound as e:
        print(f"Model not found: {e}. Check for deprecation and update model name.")
        return

    reply = response.text.strip()

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

    emotion_method = emotion_methods.get(emotion if emotion in valid_emotions else "Normal")
    emotion_task = asyncio.to_thread(emotion_method)
    voice_task = speak_text(answer)
    await asyncio.gather(emotion_task, voice_task)

    conversation_history.append({"role": "model", "parts": [answer]})

    # Initialize Firebase
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
            firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
            logger.info("Firebase initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {str(e)}")
        await speak_text("Sorry, I couldn't connect to the device database.")
        await asyncio.to_thread(normal)
        return

    failed_attempts = 0
    max_attempts = 1
    positive_responses = ["yes", "yeah", "yep", "correct", "right", "ok", "okay"]
    negative_responses = ["no", "nope", "not", "wrong", "incorrect"]

    while failed_attempts < max_attempts:
        reminder_text = read_reminder_file()
        if reminder_text:
            print(f"📝 Found reminder: {reminder_text}")
            play_reminder_audio()
            await speak_text(reminder_text)
            play_reminder_audio()
            await speak_text(reminder_text)
            if not clear_reminder_file():
                logger.error("Failed to clear reminder file, proceeding anyway")
            failed_attempts = 0  # Reset after processing reminder
        else:
            print("📝 Reminder file is empty or not found, proceeding with normal loop")

        user_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))

        if user_input is None:
            failed_attempts += 1
            print(f"\U0001F615 Failed attempt {failed_attempts}/{max_attempts}.")
            if failed_attempts >= max_attempts:
                print(f"\U0001F615 No speech detected after {max_attempts} attempts. Exiting assistant.")
                message = random.choice(goodbye_messages)
                await speak_text(message)
                normal()
                break

        # GPIO setup reinitialization
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(TOUCH_PIN, GPIO.IN)
        failed_attempts = 0  # Reset on valid input

        # Handle task reminders, music playing, QR code commands, interdevice communication, and exit commands here
        # (implementation continues as in your full function)

        # Example for task reminder check:
        if user_input.lower() in ["what are reminders", "list reminders", "show reminders"]:
            # (Fetch and speak tasks)

            continue

        # Example for playing song, showing QR, inter-device communication, etc.

    # Clean up Firebase app and assistant
    try:
        firebase_admin.delete_app(firebase_admin.get_app())
        logger.info("Firebase app cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up Firebase app: {str(e)}")

    cleanup()
    print("Assistant shutdown complete")
    await asyncio.sleep(1)
    
# ---------------------------
# Emotion extraction and policy
# ---------------------------
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

def extract_emotion_from_text(text: str) -> Optional[str]:
    t = (text or "").lower()
    if re.search(r"\bnot\s+(sad|angry|mad|upset|depressed|happy|in love|loving|scared|afraid|anxious|nervous|tired)\b", t):
        return None
    for label, pattern in EMO_REGEX.items():
        if re.search(pattern, t, re.IGNORECASE):
            return label
    return None

def should_emote(intent: str, explicit_mood: Optional[str]) -> bool:
    global _last_emote_t
    now = time.time()
    if now - _last_emote_t < EMOTION_COOLDOWN_SEC:
        return False
    # Only allow reactions when an explicit mood signal exists
    allow = explicit_mood is not None and (intent == "chat" or intent in {"math","task","command","qr"})
    if allow:
        _last_emote_t = now
    return allow

def safe_emotion(label: Optional[str], intent: str) -> str:
    if not label:
        return "Normal"
    if intent in {"math", "task", "command", "qr"} and label == "Love":
        return "Normal"
    return label

EMO_ACTIONS = {
    "HAPPY":    happy,
    "SAD":      sad,
    "ANGRY":    angry,
    "LOVE":     love,
    "NORMAL":   normal,
    "TIRED":    sad,       # map to tired eyes
    "CONFUSED": normal,
    "FEAR":     sad,
    "STRESSED": sad,
    "EXCITED":  happy,
}

def react_detected_emotion_label(label: Optional[str]):
    key = (label or "Normal").upper()
    func = EMO_ACTIONS.get(key, normal)
    try:
        func()
    except Exception as e:
        print(f"[emote] error running {key}: {e}")

# ---------------------------
# Intent and math helpers
# ---------------------------
CONT_RE = re.compile(r"(multiply|times|x|divide|over|add|\+|plus|subtract|-|minus)\s+(?:it\s+by\s+)?([\-\+]?\d+(?:\.\d+)?)", re.IGNORECASE)
MATH_RE = re.compile(r'^\s*(what\s+is\s+)?(-?\d+(\.\d+)?)\s*([+\-*/x])\s*(-?\d+(\.\d+)?)\s*\??\s*$', re.IGNORECASE)
MATH_STATE = {"last_result": None}

def classify_intent(text: str) -> str:
    t = (text or "").lower()
    if re.search(r"show\s+qr|show\s+q\s*r", t):
        return "qr"
    if re.search(r"reminder|task|todo", t):
        return "task"
    if re.search(r"what\s+is\s+.*?(\+|\-|x|Ã—|/)|\d+\s*(\+|\-|x|Ã—|/)\s*\d+", t) or CONT_RE.match(t):
        return "math"
    if re.search(r"\b(play|send message|volume|brightness)\b", t):
        return "command"
    return "chat"

def quick_math_answer(text: str):
    m = MATH_RE.match(text or "")
    if not m: 
        return None
    a = float(m.group(2)); b = float(m.group(5)); op = m.group(4).lower().replace('x','*')
    try:
        val = a+b if op=='+' else a-b if op=='-' else a*b if op=='*' else a/b
        vi = int(val)
        return str(vi) if abs(val-vi) < 1e-9 else f"{val:.6g}"
    except Exception:
        return None

def math_continue(text: str) -> Optional[str]:
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
# LLM prompt/parse (JSON only)
# ---------------------------
def llm_prompt(user_text: str, neutral: bool) -> str:
    role = ROLE_PROMPT_NEUTRAL if neutral else ROLE_PROMPT_EMPATH
    return f"{role}\nUser: {user_text}\n{JSON_INSTRUCTION}"

def parse_model_emotion_and_answer(raw: str) -> Tuple[Optional[str], str]:
    txt = (raw or "").strip()
    # JSON-first
    try:
        m = re.search(r'\{.*\}', txt, re.DOTALL)
        obj = json.loads(m.group(0) if m else txt)
        emo = obj.get("emotion")
        ans = obj.get("answer", "")
        if emo and ans:
            return emo, ans
    except Exception:
        pass
    # [Emotion,Answer]
    m = re.match(r'\[\s*(Happy|Sad|Angry|Normal|Love)\s*,\s*(.+?)\s*\]$', txt, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).title(), m.group(2)
    # Loose 'Emotion, Answer'
    m = re.match(r'^\s*(Happy|Sad|Angry|Normal|Love)\s*[,:]\s*(.+)$', txt, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).title(), m.group(2)
    return None, txt

async def llm_emotion_and_answer(user_text: str, neutral: bool) -> Tuple[Optional[str], str]:
    prompt = llm_prompt(user_text, neutral)
    try:
        resp = model.generate_content([{"role": "user", "parts": [prompt]}], generation_config={"max_output_tokens": 96})
        raw = (getattr(resp, "text", "") or "").strip()
        emo, ans = parse_model_emotion_and_answer(raw)
        if emo is not None and ans:
            return emo, ans
        # retry harder
        resp2 = model.generate_content(
            [{"role": "user", "parts": [prompt + "\nSTRICT: Only the JSON object, nothing else."]}],
            generation_config={"max_output_tokens": 96}
        )
        raw2 = (getattr(resp2, "text", "") or "").strip()
        emo, ans = parse_model_emotion_and_answer(raw2)
        if emo is not None and ans:
            return emo, ans
        return None, raw2 or raw or "Okay."
    except Exception:
        return None, "Okay."

# ---------------------------
# Intent handlers
# ---------------------------
async def handle_tasks_intent():
    try:
        with open(JSON_CONFIG_PATH, 'r') as config_file:
            config = json.load(config_file)
        user_id = config.get('userId')
        if not user_id:
            logger.error("Missing userId in config file")
            await speak_once("Sorry, I couldn't find your user ID.")
            await asyncio.to_thread(normal)
            return
        task_response = fetch_user_tasks(user_id)
        await asyncio.gather(
            speak_once(task_response),
            asyncio.to_thread(normal)
        )
    except FileNotFoundError:
        logger.error(f"Config file {JSON_CONFIG_PATH} not found")
        await speak_once("Sorry, I couldn't read the user configuration.")
        await asyncio.to_thread(normal)
    except Exception as e:
        logger.error(f"Error fetching tasks: {str(e)}")
        await speak_once("Sorry, there was an error retrieving your tasks.")
        await asyncio.to_thread(normal)

async def handle_song_intent(user_input: str):
    song_match = re.match(r'^play\s+a\s+song\s+(.+)$', user_input, re.IGNORECASE)
    max_song_attempts = 1
    if song_match:
        song_input = song_match.group(1).strip()
    elif user_input in ("play a song", "play song"):
        await speak_once("What song should I play?")
        await asyncio.to_thread(normal)
        song_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
        if song_input is None:
            await speak_once("Sorry, I couldn't get the song name. Let's try something else.")
            await asyncio.to_thread(normal)
            return
    else:
        return

    for attempt in range(max_song_attempts):
        if song_input:
            await speak_once(f"Your song is {song_input}. Is that correct?")
            await asyncio.to_thread(normal)
            confirmation = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
            if confirmation is None:
                if attempt < max_song_attempts - 1:
                    await speak_once(f"I didn't hear you. Is {song_input} the correct song?")
                    await asyncio.to_thread(normal)
                    continue
                else:
                    await speak_once("Sorry, I couldn't confirm the song. Let's try something else.")
                    await asyncio.to_thread(normal)
                    break
            confirmation = confirmation.lower()
            if any(pos in confirmation for pos in ["yes", "yeah", "yep", "correct", "right", "ok", "okay"]):
                await asyncio.to_thread(play_music, song_input, None, TOUCH_PIN)
                await asyncio.to_thread(normal)
                break
            elif any(neg in confirmation for neg in ["no", "nope", "not", "wrong", "incorrect"]):
                if attempt < max_song_attempts - 1:
                    await speak_once("Okay, what song should I play?")
                    await asyncio.to_thread(normal)
                    song_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
                    if song_input is None:
                        if attempt < max_song_attempts - 2:
                            await speak_once("I didn't catch that. What song should I play?")
                            await asyncio.to_thread(normal)
                            continue
                        else:
                            await speak_once("Sorry, I couldn't get the song name. Let's try something else.")
                            await asyncio.to_thread(normal)
                            break
                else:
                    await speak_once("Sorry, I couldn't get the right song after a few tries. Let's try something else.")
                    await asyncio.to_thread(normal)
            else:
                if attempt < max_song_attempts - 1:
                    await speak_once(f"I didn't understand. Is {song_input} the correct song?")
                    await asyncio.to_thread(normal)
                    continue
                else:
                    await speak_once("Sorry, I couldn't confirm the song. Let's try something else.")
                    await asyncio.to_thread(normal)
                    break
        else:
            if attempt < max_song_attempts - 1:
                await speak_once("I didn't catch that. What song should I play?")
                await asyncio.to_thread(normal)
                song_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
            else:
                await speak_once("Sorry, I couldn't get the song name. Let's try something else.")
                await asyncio.to_thread(normal)
                break

async def handle_qr_intent():
    try:
        with open("/home/pi/pebo_config.json", 'r') as f:
            config = json.load(f)
        device_id = config.get("deviceId")
        if not str(device_id):
            await speak_once("Error: Invalid device ID in configuration")
            return
    except Exception as e:
        await speak_once(f"Error reading device ID: {str(e)}")
        return
    await asyncio.gather(
        speak_once("Showing QR now, scan this using the user PEBO mobile app"),
        asyncio.to_thread(run_emotion, None, lambda se: eyes.QR(device_id, stop_event=se), 15)
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
            await speak_once("Sorry, I couldn't read the device configuration.")
            await asyncio.to_thread(normal)
            return

        current_ip = get_ip_address()
        if not current_ip:
            logger.error("No Wi-Fi connection detected")
            await speak_once("Cannot initiate communication: Not connected to Wi-Fi.")
            await asyncio.to_thread(normal)
            return

        users_ref = db.reference('users')
        users = users_ref.get()
        if not users:
            logger.info("No users found in Firebase")
            await speak_once("No other devices found.")
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
                            'location': device_data.get('location', 'Unknown'),
                        })

        if not same_wifi_devices:
            logger.info(f"No devices found on SSID {current_ssid}")
            await speak_once(f"No other devices found on Wi-Fi {current_ssid}.")
            await asyncio.to_thread(normal)
            return

        locations = [device['location'] for device in same_wifi_devices]
        locations_str = locations[0] if len(locations) == 1 else ", ".join(locations[:-1]) + f", or {locations[-1]}"

        print(f"Which device would you like to connect in {locations_str}?")
        await speak_once(f"Which device would you like to connect in {locations_str}?")
        await asyncio.to_thread(normal)

        location_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
        if not location_input:
            await speak_once("Sorry, I didn't catch that. Let's try something else.")
            await asyncio.to_thread(normal)
            return

        selected_device = None
        for device in same_wifi_devices:
            if location_input.lower() in device['location'].lower():
                selected_device = device
                break

        if selected_device:
            print(f"Selected Device: Location={selected_device['location']}, IP={selected_device['ip_address']}")
            await speak_once(f"Connected to PEBO in {selected_device['location']}. Double-tap to stop communication.")
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
            await speak_once("Communication stopped. Anything else?")
            await asyncio.to_thread(normal)
        else:
            await speak_once("Sorry, I couldn't find a device in that location. Let's try something else.")
            await asyncio.to_thread(normal)
    except FileNotFoundError:
        logger.error(f"Config file {JSON_CONFIG_PATH} not found")
        await speak_once("Sorry, I couldn't read the device configuration.")
        await asyncio.to_thread(normal)
    except Exception as e:
        logger.error(f"Error in interdevice communication: {str(e)}")
        await speak_once("Sorry, there was an error connecting to other devices.")
        await asyncio.to_thread(normal)

# ---------------------------
# Assistant loop
# ---------------------------
async def start_loop():
    global CURRENT_USER_NAME, LAST_MOOD, LAST_TOPICS
    # Firebase init once
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

    failed_attempts, max_attempts = 0, 5

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

        low = (user_input or "").lower().strip()

        # Tasks
        if low in ["what are reminders","list reminders","show reminders","tell me my reminders","show remind","list remind"]:
            await handle_tasks_intent()
            continue

        # Songs
        await handle_song_intent(user_input)

        # QR
        if low in ["show q r", "show me q r", "show qr", "show me qr", "show me q", "show q"]:
            await handle_qr_intent()
            continue

        # Inter-device audio
        if low == "send message":
            await handle_interdevice_communication()
            continue

        # Exit
        if low in exit_phrases or re.search(exit_pattern, user_input, re.IGNORECASE):
            await speak_once(random.choice(goodbye_messages))
            await asyncio.to_thread(normal)
            break

        # Math quick
        ans = quick_math_answer(user_input)
        if ans is not None:
            try:
                MATH_STATE["last_result"] = float(ans)
            except Exception:
                MATH_STATE["last_result"] = None
            await asyncio.gather(asyncio.to_thread(normal), speak_once(ans))
            LAST_TOPICS.append(f"math:{user_input.strip()[:30]}"); LAST_TOPICS = LAST_TOPICS[-5:]; save_memory()
            continue

        # Math continue
        cont = math_continue(user_input)
        if cont is not None:
            await asyncio.gather(asyncio.to_thread(normal), speak_once(cont))
            LAST_TOPICS.append(f"math-continue:{user_input.strip()[:30]}"); LAST_TOPICS = LAST_TOPICS[-5:]; save_memory()
            continue

        # Update memory from explicit text
        maybe = extract_name_from_text(user_input)
        if maybe:
            CURRENT_USER_NAME = maybe
        detected = extract_emotion_from_text(user_input)

        # Classify intent and decide if animation allowed
        intent = classify_intent(user_input)
        allow_anim = should_emote(intent, detected)

        if detected:
            LAST_MOOD = detected
        save_memory()

        # Neutral for serious intents; brief empathy only for chat with explicit emotion
        neutral_mode = (intent in {"math","task","command","qr"}) or (intent == "chat" and not detected)

        # LLM with strict schema (JSON); model emotion ignored for animation
        emo_from_model, answer = await llm_emotion_and_answer(user_input, neutral=neutral_mode)
        answer = sanitize_llm_text(answer)

        # Final animation uses explicit user sentiment, not modelâ€™s
        final_emotion = safe_emotion(detected, intent) if allow_anim else "Normal"

        if final_emotion == "Normal":
            await asyncio.gather(asyncio.to_thread(normal), speak_once(answer))
        else:
            await asyncio.gather(
                asyncio.to_thread(react_detected_emotion_label, final_emotion),
                speak_once(answer)
            )

        LAST_TOPICS.append(user_input.strip()[:50]); LAST_TOPICS = LAST_TOPICS[-5:]; save_memory()


# ---------------------------
# Monitors
# ---------------------------
async def monitor_for_trigger(name, emotion):
    global SESSION_ACTIVE, CURRENT_USER_NAME
    initialize_hardware()
    normal()
    while True:
        print("ðŸŽ§ Waiting for trigger phrase (e.g., 'hi PEBO', 'PEBO')...")
        text = listen(recognizer, mic)
        if not text:
            continue

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

            # Greeting: wave + happy + voice together
            greeting = f"Hi {CURRENT_USER_NAME or 'Yohan'}, I'm Pebo, your buddy."
            await asyncio.gather(
                asyncio.to_thread(say_hi),
                asyncio.to_thread(happy),
                speak_once(greeting),
            )

            # Conversation loop (no re-intros)
            await start_loop()

        finally:
            SESSION_ACTIVE = False
            normal()


# Immediate greet on boot-wake, then start_loop
async def monitor_start(name, emotion):
    global SESSION_ACTIVE, CURRENT_USER_NAME

    initialize_hardware()
    normal()
    try:
        print("ðŸŽ§ Waiting for initial speech input...")

        SESSION_ACTIVE = True
        if name and str(name).lower() != "none":
            CURRENT_USER_NAME = name
        save_memory()

        greeting = f"Hi {CURRENT_USER_NAME or 'Yohan'}, I'm Pebo, your buddy."
        await asyncio.gather(
            asyncio.to_thread(say_hi),
            asyncio.to_thread(happy),
            speak_once(greeting),
        )

        await start_loop()
    finally:
        SESSION_ACTIVE = False
        normal()
        print("ðŸ–¥ï¸ Cleaning up in monitor_start...")


# Preferred main entry; greet-once flow with optional camera recognition
async def monitor_new():
    global SESSION_ACTIVE, CURRENT_USER_NAME

    load_memory()
    initialize_hardware()
    normal()

    while True:
        print("ðŸŽ§ Waiting for trigger phrase (e.g., 'hi PEBO', 'PEBO')...")
        # Optional cam result (ignored if skipping checks)
        cam_name, cam_emotion = (None, None) if SKIP_USER_CHECK else read_recognition_result()

        text = listen(recognizer, mic)
        if not text:
            continue

        # Allow QR during idle
        if re.search(r"\bshow\s+(?:me\s+)?q\s*r\b|\bshow\s+q\b", text, re.IGNORECASE):
            await handle_qr_intent()
            continue

        # Ignore new triggers while active
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
                speak_once(greeting),
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
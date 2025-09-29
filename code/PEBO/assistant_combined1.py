#!/usr/bin/env python3
"""
PEBO Voice Assistant with Robot Control
- Listens for trigger phrases (robust "PEBO" similar-sounding list for noisy pickup)
- Detects emotion with Gemini, expresses emotion first (arms/eyes), then speaks emotionally
- Integrates reminders, tasks, music, QR, and inter-device comms
- All awaits are inside async functions (no top-level await)
"""

import os
import re
import time
import json
import errno
import fcntl
import socket
import struct
import random
import asyncio
import logging
import threading
import tempfile
import subprocess
from datetime import datetime, timezone

import pygame
import edge_tts
import google.generativeai as genai
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

from arms.arms_pwm import (
    say_hi, express_tired, express_happy, express_sad,
    express_angry, reset_to_neutral, scan_i2c_devices,
    angle_to_pulse_value, set_servos, smooth_move
)
from display.eyes_qr import RoboEyesDual
from interaction.play_song1 import play_music
from Communication.sender import start_audio_node

import firebase_admin
from firebase_admin import credentials, db

# ---------------------- Logging ----------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------------- Constants/Config ----------------------
LED_PIN = 18
TOUCH_PIN = 17

LEFT_EYE_ADDRESS = 0x3C
RIGHT_EYE_ADDRESS = 0x3D

SERVICE_ACCOUNT_PATH = '/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/ipconfig/firebase_config.json'
DATABASE_URL = 'https://pebo-task-manager-767f3-default-rtdb.asia-southeast1.firebasedatabase.app'
JSON_CONFIG_PATH = "/home/pi/pebo_config.json"

GOOGLE_API_KEY = "AIzaSyCBkCCR63VV_HCRi_5Qjo9Akx2415eGdp4"

# ---------------------- Globals ----------------------
i2c = None
eyes = None
current_eye_thread = None
stop_event = None

recognizer = sr.Recognizer()
mic = sr.Microphone()

# An aggressively comprehensive similar-sounds list for "PEBO" (noisy pickup friendly)
similar_sounds = [
    # Canonical
    "pebo", "peebo", "pee bo", "pe bo", "p e b o", "pibo", "pi bo", "pibo", "pibo", "pibo bot",
    # Common mishears
    "bebo", "be bo", "bee bo", "bebo bot", "pepo", "pe po", "pepper", "pebble", "pebble bot",
    "pivo", "pivo bot", "pibo bot", "pablo", "pablo bot", "pika", "pika bot",
    "pillow", "pilo", "pilo bot", "pillow bot", "people", "people bot",
    "keyboard", "kibo", "kivo", "kibo bot", "kivo bot", "tibo", "tivo", "tebo", "teebo",
    "debo", "dibo", "jibo", "geebo", "gebo", "gibo", "libo", "lebo", "livo", "nebo", "nibo",
    "fibo", "feebo", "vebo", "vevo", "rebo", "ribo", "zeebo", "zibo",
    "papo", "pobo", "pibo", "pibo", "pabo", "pabo bot",
    # Split/space/compound forms
    "pee bow", "pea bow", "pea bo", "pea bow bot", "bee bow", "bee bo", "bee bow bot",
    "pay bo", "pay bow", "paybo", "paybow", "p o", "p o bot", "p o bo",
    "pee boy", "pe boy", "pee boo", "pee boo bot",
    # Accent drifts and vowels
    "pabo", "pibo", "pibo", "peebu", "pibu", "pabu", "pebu", "pivu", "pavu",
    # With greetings
    "hi pebo", "hey pebo", "hello pebo", "hi pibo", "hey pibo", "hello pibo",
    "hi bebo", "hey bebo", "hello bebo", "hi pillow", "hey pillow", "hello pillow",
    # Homophones/near-phonemes
    "pebow", "peebo", "pipo", "pipo bot", "peepo", "peepo bot", "pipo pebo",
    # Words ASR often confuses in room noise
    "people", "pillow", "piano", "pebble", "paper", "paypal", "pivot", "table",
    "keyboard", "kibo", "kilo", "bible", "bebo", "bebop", "bebo bot",
    # Sri Lankan accent drifts (approx)
    "peh bo", "pee boh", "pee bah", "peh boh", "piboah",
    # Additions
    "bebo", "bebo robot", "pebo robot", "pebo bot", "bebo bot"
]

# Regex-style phonetic variants (covers many unlisted combos)
pattern_variants = [
    r"p[ei]b[o0]",         # pebo, pibo, pebo, p1bo-like
    r"b[ei]b[o0]",         # bebo, bibo
    r"pe+ ?b[o0u]",        # peebo, pee bo, peebu
    r"pi+ ?b[o0u]",        # piibo, pii bo, pibu
    r"be+ ?b[o0u]",        # beebo, bee bo, bebu
    r"p[eai] ?bo[t]?",     # pea bo, pai bo, pe bo, pebot
    r"p[eai] ?bow",        # pea bow, pe bow
    r"pe+ ?boo",           # peeboo, pee boo
]

# Exit phrases
exit_phrases = ["exit", "shutup", "stop", "shut up", "goodbye", "bye", "bye pebo", "bye pibo", "bye bebo"]
exit_pattern = r'\b(goodbye|bye)\s+(' + '|'.join([re.escape(s) for s in similar_sounds]) + r')\b'

goodbye_messages = [
    "Bye-bye for now! Just whisper my name if needed!",
    "Toodles! I’m only a ‘hey PEBO’ away!",
    "Catch you later! Call me anytime!",
    "See ya! I’ll be right here if you need anything!",
    "Bye for now! Ping me if you need some robot magic!",
    "Going quiet now! But say my name and I’ll wag my circuits!",
    "Snuggling into sleep mode... call me if you want to play!",
    "Goodbye for now! Call on me anytime, I’m always listening.",
    "Logging off! But give me a shout and I’ll be right there!"
]

# ---------------------- Init: Pygame + Gemini + Whisper ----------------------
pygame.mixer.init()

genai.configure(api_key=GOOGLE_API_KEY)
try:
    model = genai.GenerativeModel("gemini-2.0-flash")
except Exception as e:
    logger.error(f"Gemini init failed: {e}")
    model = None

try:
    whisper_model = whisper.load_model("base")
except Exception as e:
    logger.warning(f"Whisper model load failed: {e}")
    whisper_model = None

# ---------------------- Hardware/Eyes Helpers ----------------------
def initialize_hardware():
    global i2c, eyes
    i2c = busio.I2C(board.SCL, board.SDA)
    eyes = RoboEyesDual(LEFT_EYE_ADDRESS, RIGHT_EYE_ADDRESS)
    eyes.begin(128, 64, 40)
    logger.info("Hardware initialized.")

def run_emotion(arm_func, eye_func, duration=2):
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
    stop_event = None
    normal()

def hi():
    logger.info("Expressing Hi")
    run_emotion(say_hi, eyes.Happy)

def normal():
    logger.info("Expressing Normal")
    global current_eye_thread, stop_event
    stop_event = threading.Event()
    current_eye_thread = threading.Thread(target=eyes.Default, args=(stop_event,))
    current_eye_thread.daemon = True
    current_eye_thread.start()
    stop_event = None

def happy():
    logger.info("Expressing Happy")
    run_emotion(express_happy, eyes.Happy)

def sad():
    logger.info("Expressing Sad")
    run_emotion(express_sad, eyes.Tired)

def angry():
    logger.info("Expressing Angry")
    run_emotion(express_angry, eyes.Angry)

def love():
    logger.info("Expressing Love")
    run_emotion(express_happy, eyes.Love)

def qr(device_id):
    logger.info(f"Displaying QR for device: {device_id}")
    run_emotion(None, lambda se: eyes.QR(device_id, stop_event=se), duration=15)

def cleanup():
    global i2c, eyes, current_eye_thread, stop_event
    logger.info("Cleaning up resources...")
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
        logger.info("Displays cleared")
    except Exception as e:
        logger.warning(f"Error clearing displays: {e}")
    try:
        i2c.deinit()
        logger.info("I2C bus deinitialized")
    except Exception as e:
        logger.warning(f"Error deinitializing I2C: {e}")
    logger.info("Cleanup complete")

# ---------------------- File/Reminder Utilities ----------------------
def read_recognition_result(file_path="/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/recognition_result.txt"):
    max_read_retries = 5
    read_retry_delay = 0.5
    for attempt in range(max_read_retries):
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            name = None; emotion = None
            for line in lines:
                line = line.strip()
                if line.startswith("Name:"):
                    name = line.replace("Name:", "").strip()
                elif line.startswith("Emotion:"):
                    emotion = line.replace("Emotion:", "").strip()
            if name and emotion:
                return name, emotion
            else:
                logger.warning(f"Missing Name/Emotion in {file_path}.")
                return None, None
        except FileNotFoundError:
            logger.warning(f"File {file_path} not found.")
            return None, None
        except IOError as e:
            if e.errno in (errno.EACCES, errno.EBUSY) and attempt < max_read_retries - 1:
                time.sleep(read_retry_delay)
            else:
                logger.error(f"Error reading {file_path}: {e}")
                return None, None
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None, None

def read_reminder_file(file_path="/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/reminders/reminder_output.txt"):
    max_read_retries = 5
    read_retry_delay = 0.5
    for attempt in range(max_read_retries):
        try:
            with open(file_path, 'r') as file:
                content = file.read().strip()
                return content if content else None
        except FileNotFoundError:
            return None
        except IOError as e:
            if e.errno in (errno.EACCES, errno.EBUSY) and attempt < max_read_retries - 1:
                time.sleep(read_retry_delay)
            else:
                return None
        except Exception:
            return None

def clear_reminder_file(file_path="/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/reminders/reminder_output.txt"):
    max_write_retries = 5
    write_retry_delay = 0.5
    for attempt in range(max_write_retries):
        try:
            with open(file_path, 'w') as file:
                file.write("")
            return True
        except IOError as e:
            if e.errno in (errno.EACCES, errno.EBUSY) and attempt < max_write_retries - 1:
                time.sleep(write_retry_delay)
            else:
                return False
        except Exception:
            return False

def play_reminder_audio(audio_file="/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/reminders/reminder.wav"):
    try:
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.set_volume(1.0)
        for _ in range(2):
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.25)
        pygame.mixer.music.unload()
    except Exception as e:
        logger.warning(f"Reminder audio error: {e}")

# ---------------------- Audio/TTS/Listen ----------------------
def amplify_audio(input_file, output_file, gain_db=10):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", input_file,
        "-filter:a", f"volume={gain_db}dB",
        output_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

async def speak_text(text):
    voice = "en-US-JennyNeural"
    filename = "response.mp3"
    boosted_file = "boosted_response.mp3"
    tts = edge_tts.Communicate(text, voice)
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

def listen(
    recognizer: sr.Recognizer,
    mic: sr.Microphone,
    *, timeout: float = 8,
    phrase_time_limit: float = 6,
    retries: int = 2,
    language: str = "en-US",
    calibrate_duration: float = 0.5,
) -> str | None:
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
                print(f"⚠️ Google speech service error ({e}).")
        except sr.WaitTimeoutError:
            print("⌛ Timed out waiting for speech.")
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

def listen_whisper(duration=1, sample_rate=16000) -> str | None:
    if whisper_model is None:
        return None
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
            print(f"📝 You said (Whisper): {text}")
            return text
        else:
            print("🤔 No intelligible speech detected.")
            return None
    except Exception as e:
        print(f"❌ Whisper error: {e}")
        return None
    finally:
        try:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception:
            pass

# ---------------------- Network/Tasks ----------------------
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

def fetch_user_tasks(user_id):
    try:
        tasks_ref = db.reference(f'users/{user_id}/tasks')
        tasks = tasks_ref.get()
        if not tasks:
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
                        if reminder_time1 and minutes_until_deadline <= int(reminder_time1):
                            soon = " It is due soon!"
                        if reminder_time2 and minutes_until_deadline <= int(reminder_time2):
                            soon = " It is due soon!"
                    except Exception:
                        pass
                    task_info = (f"{description}, due on {deadline.strftime('%B %d at %I:%M %p')}, "
                                 f"priority {priority}{reminder_text}.{soon}")
                    pending_tasks.append(task_info)
                except Exception:
                    continue
        if not pending_tasks:
            return "You have no pending tasks."
        if len(pending_tasks) == 1:
            return f"You have one task: {pending_tasks[0]}"
        else:
            return f"You have {len(pending_tasks)} tasks: {'; '.join(pending_tasks)}"
    except Exception as e:
        logger.error(f"Error fetching tasks for user {user_id}: {str(e)}")
        return "Sorry, I couldn't retrieve your tasks due to an error."

# ---------------------- Emotion Methods Map ----------------------
emotion_methods = {
    "Happy": happy,
    "Sad": sad,
    "Angry": angry,
    "Normal": normal,
    "Love": love,
}
valid_emotions = set(emotion_methods.keys())

# ---------------------- Core: Emotion + Answer ----------------------
async def start_assistant_from_text(prompt_text: str):
    """
    - Reinforce PEBO identity
    - Ask Gemini for Emotion,Reply
    - Express emotion first (arms/eyes), then speak emotionally
    - Initialize Firebase (if needed) inside async scope
    """
    logger.info(f"Prompt: {prompt_text}")

    # Initialize Firebase safely here
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
            firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
            logger.info("Firebase initialized successfully")
    except Exception as e:
        logger.error(f"Failed Firebase init: {str(e)}")
        await speak_text("Sorry, I couldn't connect to the device database.")
        await asyncio.to_thread(normal)
        return

    full_prompt = (
        "You are PEBO, an emotional assistant and companion.\n"
        f"User message: \"{prompt_text}\"\n"
        "Determine emotion: Happy, Sad, Angry, Normal, Love.\n"
        "Respond exactly: Emotion, your reply."
    )

    # Gemini inference
    try:
        response = model.generate_content(
            [{"role": "user", "parts": [full_prompt]}],
            generation_config={"max_output_tokens": 60}
        )
        reply = (response.text if hasattr(response, 'text') else str(response)).strip()
        match = re.match(r"(Happy|Sad|Angry|Normal|Love)[,:\-\s]+(.+)", reply, re.IGNORECASE)
        if match:
            emotion, answer = match.groups()
            emotion = emotion.capitalize()
            answer = answer.strip()
            logger.info(f"Emotion detected: {emotion} | Answer: {answer}")
        else:
            emotion, answer = "Normal", reply
            logger.info("Emotion not detected; defaulting to Normal")
    except Exception as e:
        logger.error(f"Gemini error: {str(e)}")
        await speak_text("Sorry, I cannot respond right now.")
        await asyncio.to_thread(normal)
        return

    # Express + speak concurrently
    emotion_method = emotion_methods.get(emotion if emotion in valid_emotions else "Normal")
    await asyncio.gather(
        asyncio.to_thread(emotion_method),
        speak_text(answer)
    )

# ---------------------- Extended Post-Response Loop (optional) ----------------------
async def handle_post_response_loop():
    """
    Optional continuous loop for reminders, tasks, music, QR, inter-device messaging,
    kept inside async function to avoid top-level awaits.
    """
    failed_attempts = 0
    max_attempts = 1
    positive_responses = ["yes", "yeah", "yep", "correct", "right", "ok", "okay"]
    negative_responses = ["no", "nope", "not", "wrong", "incorrect"]

    while failed_attempts < max_attempts:
        reminder_text = read_reminder_file()
        if reminder_text:
            play_reminder_audio()
            await speak_text(reminder_text)
            play_reminder_audio()
            await speak_text(reminder_text)
            clear_reminder_file()
            failed_attempts = 0
        else:
            logger.info("Reminder file empty or not found, continuing...")

        user_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))

        if user_input is None:
            failed_attempts += 1
            logger.info(f"Failed attempt {failed_attempts}/{max_attempts}")
            if failed_attempts >= max_attempts:
                message = random.choice(goodbye_messages)
                await speak_text(message)
                await asyncio.to_thread(normal)
                break
            continue

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(TOUCH_PIN, GPIO.IN)
        failed_attempts = 0

        # Commands
        if user_input.lower() in ["what are reminders", "list reminders", "show reminders", "tell me my reminders", "show remind", "list remind"]:
            try:
                with open(JSON_CONFIG_PATH, 'r') as config_file:
                    config = json.load(config_file)
                    user_id = config.get('userId')
                if not user_id:
                    await speak_text("Sorry, I couldn't find your user ID.")
                    await asyncio.to_thread(normal)
                    continue
                task_response = fetch_user_tasks(user_id)
                await asyncio.gather(
                    speak_text(task_response),
                    asyncio.to_thread(normal)
                )
                continue
            except FileNotFoundError:
                await speak_text("Sorry, I couldn't read the user configuration.")
                await asyncio.to_thread(normal)
                continue
            except Exception:
                await speak_text("Sorry, there was an error retrieving your tasks.")
                await asyncio.to_thread(normal)
                continue

        song_match = re.match(r'^play\s+a\s+song\s+(.+)$', user_input, re.IGNORECASE)
        if song_match or user_input in ["play a song", "play song"]:
            if song_match:
                song_input = song_match.group(1).strip()
            else:
                await speak_text("What song should I play?")
                await asyncio.to_thread(normal)
                song_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
                if song_input is None:
                    await speak_text("Sorry, I couldn't get the song name. Let's try something else.")
                    await asyncio.to_thread(normal)
                    continue

            if song_input:
                await speak_text(f"Your song is {song_input}. Is that correct?")
                await asyncio.to_thread(normal)
                confirmation = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
                if confirmation is None:
                    await speak_text("Sorry, I couldn't confirm the song. Let's try something else.")
                    await asyncio.to_thread(normal)
                else:
                    confirmation = confirmation.lower()
                    if any(pos in confirmation for pos in positive_responses):
                        await play_music(song_input, None, TOUCH_PIN)
                        await asyncio.to_thread(normal)
                    elif any(neg in confirmation for neg in negative_responses):
                        await speak_text("Okay, what song should I play?")
                        await asyncio.to_thread(normal)
                    else:
                        await speak_text("Sorry, I couldn't confirm the song. Let's try something else.")
                        await asyncio.to_thread(normal)
            continue

        if user_input.lower() in ["show q r", "show me q r", "show qr", "show me qr", "show me q", "show q"]:
            try:
                with open("/home/pi/pebo_config.json", 'r') as f:
                    config = json.load(f)
                    device_id = config.get("deviceId")
                    if not str(device_id):
                        await speak_text("Error: Invalid device ID in configuration")
                        continue
            except Exception as e:
                await speak_text(f"Error reading device ID: {str(e)}")
                continue

            await asyncio.gather(
                speak_text("Showing QR now, scan this using the user PEBO mobile app"),
                asyncio.to_thread(run_emotion, None, lambda se: eyes.QR(device_id, stop_event=se), 15)
            )
            await asyncio.to_thread(normal)
            continue

        if user_input == "send message":
            try:
                with open(JSON_CONFIG_PATH, 'r') as config_file:
                    config = json.load(config_file)
                    current_ssid = config.get('ssid')
                    current_device_id = config.get('deviceId')
                    user_id = config.get('userId')
                if not current_ssid or not current_device_id or not user_id:
                    await speak_text("Sorry, I couldn't read the device configuration.")
                    await asyncio.to_thread(normal)
                    continue

                current_ip = get_ip_address()
                if not current_ip:
                    await speak_text("Cannot initiate communication: Not connected to Wi-Fi.")
                    await asyncio.to_thread(normal)
                    continue

                users_ref = db.reference('users')
                users = users_ref.get()
                if not users:
                    await speak_text("No other devices found.")
                    await asyncio.to_thread(normal)
                    continue

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
                    await speak_text(f"No other devices found on Wi-Fi {current_ssid}.")
                    await asyncio.to_thread(normal)
                    continue

                locations = [device['location'] for device in same_wifi_devices]
                if len(locations) > 1:
                    locations_str = ", ".join(locations[:-1]) + f", or {locations[-1]}"
                else:
                    locations_str = locations[0]
                await speak_text(f"Which device would you like to connect in {locations_str}?")
                await asyncio.to_thread(normal)

                location_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
                if not location_input:
                    await speak_text("Sorry, I didn't catch that. Let's try something else.")
                    await asyncio.to_thread(normal)
                    continue

                selected_device = None
                for device in same_wifi_devices:
                    if location_input.lower() in device['location'].lower():
                        selected_device = device
                        break

                if selected_device:
                    await speak_text(f"Connected to PEBO in {selected_device['location']}. Double-tap to stop communication.")
                    await asyncio.to_thread(normal)
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setup(TOUCH_PIN, GPIO.IN)
                    audio_thread = threading.Thread(
                        target=start_audio_node,
                        args=(8888, selected_device['ip_address'], 8889, TOUCH_PIN)
                    )
                    audio_thread.daemon = True
                    audio_thread.start()
                    audio_thread.join()
                    await speak_text("Communication stopped. Anything else?")
                    await asyncio.to_thread(normal)
                else:
                    await speak_text("Sorry, I couldn't find a device in that location. Let's try something else.")
                    await asyncio.to_thread(normal)
            except FileNotFoundError:
                await speak_text("Sorry, I couldn't read the device configuration.")
                await asyncio.to_thread(normal)
            except Exception as e:
                await speak_text("Sorry, there was an error connecting to other devices.")
                await asyncio.to_thread(normal)
            continue

        if user_input in exit_phrases or re.search(exit_pattern, user_input, re.IGNORECASE):
            message_exit = random.choice(goodbye_messages)
            await speak_text(message_exit)
            await asyncio.to_thread(normal)
            break

        # If none of the commands matched, run normal emotion+TTS flow:
        await start_assistant_from_text(user_input)

# ---------------------- Trigger Loop ----------------------
def build_trigger_regex():
    items = [re.escape(s) for s in similar_sounds]
    items.extend(pattern_variants)
    return r"\b((?:hi|hey|hello)\s+)?(?:" + "|".join(items) + r")\b"

async def monitor_new():
    initialize_hardware()
    normal()
    trigger_regex = build_trigger_regex()
    while True:
        logger.info("🎧 Waiting for trigger phrase (e.g., 'hi PEBO', 'PEBO')...")
        text = listen(recognizer, mic)
        if text and re.search(trigger_regex, text, re.IGNORECASE):
            await asyncio.gather(
                asyncio.to_thread(hi),
                speak_text("Hello! I'm PEBO, your emotional assistant and companion.")
            )
            # Main interaction loop
            while True:
                logger.info("🎤 Listening for your message ('exit' to quit)...")
                user_message = listen(recognizer, mic)
                if user_message is None or user_message.lower() in ['exit', 'quit', 'bye']:
                    await speak_text("Goodbye! Talk to you later.")
                    await asyncio.to_thread(normal)
                    break
                await start_assistant_from_text(user_message)
                await handle_post_response_loop()
        else:
            logger.info("No trigger detected.")

# ---------------------- Main ----------------------
if __name__ == "__main__":
    try:
        asyncio.run(monitor_new())
    except KeyboardInterrupt:
        logger.info("Program terminated by user.")
    finally:
        try:
            reset_to_neutral()
        except Exception:
            pass
        cleanup()

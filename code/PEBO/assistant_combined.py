#!/usr/bin/env python3
"""
Assistant with robust Gemini and TTS:
- Prefers gemini-1.5-flash, auto-falls back to an accessible model from list_models.
- safe_generate returns a small object with .text on all errors (no crashes).
- Edge TTS retries a different voice on NoAudioReceived and falls back to eSpeak offline.
"""

import os
import re
import json
import time
import errno
import random
import locale
import asyncio
import logging
import tempfile
import subprocess
import threading
from datetime import datetime, timezone

import numpy as np
import pygame
import whisper
import edge_tts
import sounddevice as sd
import scipy.io.wavfile
import speech_recognition as sr

import board
import busio
import smbus
import RPi.GPIO as GPIO

import google.generativeai as genai
from google.api_core.exceptions import NotFound, PermissionDenied, GoogleAPICallError
from edge_tts.exceptions import NoAudioReceived

from arms.arms_pwm import (
    say_hi, express_tired, express_happy, express_sad, express_angry,
    reset_to_neutral, scan_i2c_devices, angle_to_pulse_value, set_servos, smooth_move
)
from display.eyes_qr import RoboEyesDual
from interaction.play_song1 import play_music
from Communication.sender import start_audio_node

import dateutil.parser
import firebase_admin
from firebase_admin import credentials, db

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)
try: locale.setlocale(locale.LC_ALL, "")
except Exception: pass
os.environ.setdefault("PYTHONUTF8", "1")

# GPIO / HW
TOUCH_PIN = 17
LED_PIN = 18
LEFT_EYE_ADDRESS = 0x3C
RIGHT_EYE_ADDRESS = 0x3D

GPIO.setwarnings(False)
if not GPIO.getmode():
    GPIO.setmode(GPIO.BCM)
GPIO.setup(TOUCH_PIN, GPIO.IN)

i2c = None
eyes = None
current_eye_thread = None
stop_event = None

# Pygame audio
try:
    pygame.mixer.init()
except Exception as e:
    logger.warning(f"pygame.mixer.init failed: {e}")

# Gemini
GOOGLE_API_KEY = "AIzaSyBHA2bpUAVXLCosf7W2S_-dcnWoFQwx0-E"
if not GOOGLE_API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY env")
genai.configure(api_key=GOOGLE_API_KEY)

def _pick_accessible_model(preferred=("gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro")) -> str:
    names = []
    try:
        for m in genai.list_models():
            n = getattr(m, "name", "") or ""
            if n:
                names.append(n)
    except Exception as e:
        logger.warning(f"list_models failed: {e}")
        return preferred[0]
    # exact or fully-qualified
    for want in preferred:
        if want in names:
            return want
        for n in names:
            if n.endswith("/" + want) or n.endswith("/models/" + want):
                return n
    # fallback: first 'flash' or 'pro'
    for n in names:
        if "flash" in n:
            return n
    for n in names:
        if "pro" in n:
            return n
    return preferred[0]

_MODEL_NAME = _pick_accessible_model()
logger.info(f"Using Gemini model: {_MODEL_NAME}")
model = genai.GenerativeModel(_MODEL_NAME)

def safe_generate(ch, max_tokens=60):
    class _F:
        def __init__(self, t):
            self.text = t
    try:
        return model.generate_content(ch, generation_config={"max_output_tokens": max_tokens})
    except (NotFound, PermissionDenied) as e:
        logger.error(f"Gemini access error: {e}")
        return _F("[Normal,Sorry, the AI response service version is unavailable right now.]")
    except GoogleAPICallError as e:
        logger.error(f"Gemini API call failed: {e}")
        return _F("[Normal,Having trouble reaching the AI service at the moment.]")
    except Exception as e:
        logger.exception(f"Gemini unexpected error: {e}")
        return _F("[Normal,An unexpected error occurred while generating a reply.]")

# Firebase
SERVICE_ACCOUNT_PATH = '/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/ipconfig/firebase_config.json'
DATABASE_URL = 'https://pebo-task-manager-767f3-default-rtdb.asia-southeast1.firebasedatabase.app'
JSON_CONFIG_PATH = "/home/pi/pebo_config.json"

# Conversation + ASR
conversation_history = []
recognizer = sr.Recognizer()
mic = sr.Microphone()

similar_sounds = ["pebo","vivo","tivo","bibo","pepo","pipo","bebo","tibo","fibo","mibo","sibo","nibo","vevo","rivo",
                  "zivo","pavo","kibo","dibo","lipo","gibo","zepo","ripo","jibo","wipo","hipo","qivo","xivo","yibo",
                  "civo","kivo","nivo","livo","sivo","cepo","veto","felo","melo","nero","selo","telo","dedo","vepo",
                  "bepo","tepo","ribo","fivo","gepo","pobo","pibo","google","tune","tv","pillow","people","keyboard",
                  "pihu","be bo","de do","video","pi lo","pilo"]
exit_phrases = ["exit","shutup","stop","shut up"]
exit_pattern = r'\b(goodbye|bye)\s+(' + '|'.join(similar_sounds) + r')\b'
goodbye_messages = [
    "Bye-bye for now! Just whisper my name if needed!",
    "Toodles! Just a call away if missed!",
    "Catch you later! Only a ‘hey PEBO’ away!",
    "See ya! Right here if anything’s needed!",
    "Bye for now! Ping for robot magic!",
    "Going quiet… say my name and I’ll wag circuits!",
    "Snuggling into sleep mode... call to play!",
    "Goodbye for now! Call anytime, always listening.",
    "Logging off! Give a shout and I’ll be there!"
]

# Eyes helpers
def initialize_hardware():
    global i2c, eyes
    i2c = busio.I2C(board.SCL, board.SDA)
    eyes = RoboEyesDual(LEFT_EYE_ADDRESS, RIGHT_EYE_ADDRESS)
    eyes.begin(128, 64, 40)

def run_emotion(arm_func, eye_func, duration=1):
    global current_eye_thread, stop_event
    if stop_event:
        stop_event.set()
    if current_eye_thread and current_eye_thread.is_alive():
        current_eye_thread.join(timeout=1.0)
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
    print("Expressing Hi")
    run_emotion(say_hi, eyes.Happy)

def normal():
    print("Expressing Normal")
    global current_eye_thread, stop_event
    if stop_event:
        stop_event.set()
    if current_eye_thread and current_eye_thread.is_alive():
        current_eye_thread.join(timeout=1.0)
    stop_event = threading.Event()
    current_eye_thread = threading.Thread(target=eyes.Default, args=(stop_event,))
    current_eye_thread.daemon = True
    current_eye_thread.start()

def happy():  run_emotion(express_happy, eyes.Happy)
def sad():    run_emotion(express_sad, eyes.Tired)
def angry():  run_emotion(express_angry, eyes.Angry)
def love():   run_emotion(express_happy, eyes.Love)

def qr(device_id):
    print(f"Expressing QR with device ID: {device_id}")
    run_emotion(None, lambda stop_event: eyes.QR(device_id, stop_event=stop_event), duration=15)

def cleanup():
    global i2c, eyes, current_eye_thread, stop_event
    print("Cleaning up resources...")
    if stop_event:
        stop_event.set()
    if current_eye_thread:
        current_eye_thread.join(timeout=1.0)
        current_eye_thread = None
    try:
        reset_to_neutral()
        eyes.display_left.fill(0); eyes.display_left.show()
        eyes.display_right.fill(0); eyes.display_right.show()
    except Exception as e:
        print(f"Error clearing displays: {e}")
    try:
        i2c.deinit()
    except Exception as e:
        print(f"Error deinitializing I2C: {e}")
    print("Cleanup complete")

# Reminders helpers (same as previous; omitted here for brevity)
def read_recognition_result(file_path="/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/recognition_result.txt"):
    try:
        with open(file_path,'r') as f:
            lines = f.readlines()
        name = None; emotion = None
        for line in lines:
            s=line.strip()
            if s.startswith("Name:"): name=s.replace("Name:","").strip()
            elif s.startswith("Emotion:"): emotion=s.replace("Emotion:","").strip()
        return (name,emotion) if (name and emotion) else (None,None)
    except Exception:
        return (None,None)

def read_reminder_file(file_path="/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/reminders/reminder_output.txt"):
    try:
        with open(file_path,'r') as f:
            t=f.read().strip()
        return t if t else None
    except Exception:
        return None

def clear_reminder_file(file_path="/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/reminders/reminder_output.txt"):
    try:
        with open(file_path,'w') as f:
            f.write("")
        return True
    except Exception:
        return False

def amplify_audio(input_file, output_file, gain_db=10):
    subprocess.run(["ffmpeg","-y","-i",input_file,"-filter:a",f"volume={gain_db}dB",output_file],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# TTS
async def pick_edge_voice(preferred="en-US-AnaNeural"):
    try:
        voices = await edge_tts.list_voices()
        shortnames = {v.get("ShortName") for v in voices if v.get("ShortName")}
        if preferred in shortnames:
            return preferred
        for v in voices:
            if v.get("Locale") == "en-US" and v.get("ShortName"):
                return v["ShortName"]
        return next(iter(shortnames)) if shortnames else preferred
    except Exception:
        return preferred

async def speak_text(text: str):
    voice = await pick_edge_voice("en-US-AnaNeural")
    filename = "response.mp3"
    boosted = "boosted_response.mp3"

    for attempt in (1, 2):
        try:
            tts = edge_tts.Communicate(text, voice=voice, rate="+0%", pitch="+0Hz")
            await tts.save(filename)

            amplify_audio(filename, boosted, gain_db=20)

            try:
                pygame.mixer.music.load(boosted)
                pygame.mixer.music.set_volume(1.0)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    await asyncio.sleep(0.25)
            finally:
                try:
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()
                except Exception:
                    pass

            for f in (filename, boosted):
                try:
                    os.remove(f)
                except Exception:
                    pass
            return
        except NoAudioReceived:
            # Pick a different voice and retry once
            try:
                voices = await edge_tts.list_voices()
                alt = None
                for v in voices:
                    sn = v.get("ShortName")
                    if v.get("Locale") == "en-US" and sn and sn != voice:
                        alt = sn
                        break
                if not alt and voices:
                    for v in voices:
                        sn = v.get("ShortName")
                        if sn and sn != voice:
                            alt = sn
                            break
                if alt:
                    voice = alt
                    continue  # retry
            except Exception:
                pass
            break
        except Exception:
            break

    # Offline fallback (espeak)
    try:
        offline_wav = "response_offline.wav"
        subprocess.run(
            ["espeak", "-v", "en-us", "-w", offline_wav, text],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        amplify_audio(offline_wav, boosted, gain_db=15)

        try:
            pygame.mixer.music.load(boosted)
            pygame.mixer.music.set_volume(1.0)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.25)
        finally:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"TTS fallback failed: {e}")
    finally:
        for f in (filename, boosted, "response_offline.wav"):
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass

# Networking helpers (omitted for brevity; identical to previous working version)

# Firebase tasks (unchanged from previous working version)

# Assistant logic
async def start_assistant_from_text(prompt_text):
    print(f"💬 Initial Prompt: {prompt_text}")
    conversation_history.clear()
    full_prompt = (
        f"{prompt_text}\n"
        "Above is my message. What is your emotion for that message (Happy, Sad, Angry, Normal, or Love)? "
        "If my message includes words like 'love', 'loving', 'beloved', 'adore', 'affection', 'cute', "
        "'adorable', 'sweet', or 'charming', or if the overall sentiment feels loving or cute, set your "
        "emotion to Love. Otherwise, determine the appropriate emotion based on the message's context. "
        "Provide your answer in the format [emotion, reply], where 'emotion' is one of the specified "
        "emotions and 'reply' is your response to my message."
    )
    conversation_history.append({"role":"user","parts":[full_prompt]})
    response = safe_generate(conversation_history, max_tokens=20)
    reply = getattr(response,"text","").strip()

    emotion="Normal"; answer=reply
    m=re.match(r'\[(Happy|Sad|Angry|Normal|Love),(.+?)\]', reply)
    if m: emotion,answer=m.groups()

    emotion_methods={"Happy":happy,"Sad":sad,"Angry":angry,"Normal":normal,"Love":love}
    asyncio.ensure_future(asyncio.to_thread(emotion_methods.get(emotion,"Normal")))
    await speak_text(answer)
    conversation_history.append({"role":"model","parts":[answer]})

# Listening
def listen(recognizer: sr.Recognizer, mic: sr.Microphone, timeout=8, phrase_time_limit=6, retries=2, language="en-US", calibrate_duration=0.5) -> str|None:
    GPIO.setup(LED_PIN, GPIO.OUT); GPIO.output(LED_PIN, GPIO.LOW)
    for attempt in range(retries+1):
        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=calibrate_duration)
                print(f"🎤 Listening… (attempt {attempt+1})")
                GPIO.output(LED_PIN, GPIO.HIGH)
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                GPIO.output(LED_PIN, GPIO.LOW)
            try:
                text = recognizer.recognize_google(audio, language=language).strip().lower()
                if text: print(f"🗣️ You said: {text}"); return text
            except sr.UnknownValueError: print("🤔 Sorry—couldn’t understand that.")
            except sr.RequestError as e: print(f"⚠️ Google speech service error ({e}).")
        except sr.WaitTimeoutError: print("⌛ Timed out waiting for speech."); GPIO.output(LED_PIN, GPIO.LOW)
        except Exception as e: print(f"🎤 Mic/Audio error: {e}"); GPIO.output(LED_PIN, GPIO.LOW)
        if attempt<retries: time.sleep(0.5)
    print("😕 No intelligible speech captured."); GPIO.output(LED_PIN, GPIO.LOW); return None

# Monitors (simplified)
async def monitor_new():
    initialize_hardware()
    normal()
    while True:
        print("📻 Waiting for trigger phrase (e.g., 'hi PEBO', 'PEBO')...")
        name_read, emotion_read = read_recognition_result()
        name_local = name_read or "User"
        emotion_local = emotion_read or "Normal"
        text = listen(recognizer, mic)
        if not text: continue
        trigger_pattern = r'\b((?:hi|hey|hello)\s+)?(' + '|'.join(re.escape(s) for s in similar_sounds) + r')\b'
        if re.search(trigger_pattern, text, re.IGNORECASE):
            print("✅ Trigger phrase detected! Starting assistant...")
            await speak_text("Hello! I'm your pebo.")
            await start_assistant_from_text(f"I am {name_local}. I need your assist.")

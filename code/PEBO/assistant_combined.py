#!/usr/bin/env python3
"""
Voice Assistant with Robot Control
Listens for trigger phrases and controls robot emotions with simultaneous arm/eye expressions and voice output
Integrated with standalone functions for arm and eye movements
Includes song playback functionality triggered by 'play song' or 'play song <song name>' command in the main loop
"""

import google.generativeai as genai
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
from arms.arms_pwm import (say_hi, express_tired, express_happy, express_sad, express_angry,
                           reset_to_neutral, scan_i2c_devices, angle_to_pulse_value, set_servos, smooth_move)
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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/ipconfig/store_ip.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Pin configuration for touch sensor
TOUCH_PIN = 17  # GPIO pin number (Pin 11)

# Setup GPIO
GPIO.setmode(GPIO.BCM)  # Use BCM numbering
GPIO.setup(TOUCH_PIN, GPIO.IN)  # Set pin as input

# Constants for I2C addresses
PCA9685_ADDR = 0x40
LEFT_EYE_ADDRESS = 0x3C
RIGHT_EYE_ADDRESS = 0x3D

# Global variables for hardware control
i2c = None
eyes = None
current_eye_thread = None
stop_event = None

# LED pin configuration
LED_PIN = 18  # GPIO pin number (Pin 12)

# Firebase configuration
SERVICE_ACCOUNT_PATH = '/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/ipconfig/firebase_config.json'
DATABASE_URL = 'https://pebo-task-manager-767f3-default-rtdb.asia-southeast1.firebasedatabase.app'
JSON_CONFIG_PATH = "/home/pi/pebo_config.json"

def initialize_hardware():
    """Initialize I2C and eyes globally."""
    global i2c, eyes
    i2c = busio.I2C(board.SCL, board.SDA)
    eyes = RoboEyesDual(LEFT_EYE_ADDRESS, RIGHT_EYE_ADDRESS)
    eyes.begin(128, 64, 40)

def run_emotion(arm_func, eye_func, duration=1):
    """Run arm movement and eye expression simultaneously, then return to normal mode"""
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
    # ~ print("Expressing Hi")
    run_emotion(say_hi, eyes.Happy)

def normal():
    # ~ print("Expressing Normal")
    global current_eye_thread, stop_event
    stop_event = threading.Event()
    current_eye_thread = threading.Thread(target=eyes.Default, args=(stop_event,))
    current_eye_thread.daemon = True
    current_eye_thread.start()
    stop_event = None

def happy():
    # ~ print("Expressing Happy")
    run_emotion(express_happy, eyes.Happy)

def sad():
    # ~ print("Expressing Sad")
    run_emotion(express_sad, eyes.Tired)

def angry():
    # ~ print("Expressing Angry")
    run_emotion(express_angry, eyes.Angry)

def love():
    # ~ print("Expressing Love")
    run_emotion(express_happy, eyes.Love)
    
def qr(device_id):
    """Express QR code with the specified device ID"""
    # ~ print(f"Expressing QR with device ID: {device_id}")
    run_emotion(None, lambda stop_event: eyes.QR(device_id, stop_event=stop_event), duration=15)

def cleanup():
    """Clean up resources, clear displays, and deinitialize I2C bus."""
    global i2c, eyes, current_eye_thread, stop_event
    print("Cleaning up resources...")
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
        print("Displays cleared")
    except Exception as e:
        print(f"Error clearing displays: {e}")
    try:
        i2c.deinit()
        print("️I2C bus deinitialized, SCL and SDA cleared")
    except Exception as e:
        print(f"Error deinitializing I2C bus: {e}")
    print("Cleanup complete")

# Initialize pygame
pygame.mixer.init()

# Gemini API 
GOOGLE_API_KEY = "AIzaSyDlpxPAgmv5rHPs4hkVoKFiUdCCXuhakbY"

genai.configure(api_key=GOOGLE_API_KEY)

try:
    model = genai.GenerativeModel("gemini-2.0-flash")
except Exception as e:
    print(f"Model initialization failed: {e}")
    # Fallback to another model or offline logic
    
# Gemini memory
conversation_history = []

# Speech recognizer
recognizer = sr.Recognizer()
mic = sr.Microphone()

# List of similar sounds to "PEBO"
similar_sounds = [
    "pebo", "vivo", "tivo", "bibo", "pepo", "pipo", "bebo", "tibo", "fibo", "mibo",
    "sibo", "nibo", "vevo", "rivo", "zivo", "pavo", "kibo", "dibo", "lipo", "gibo",
    "zepo", "ripo", "jibo", "wipo", "hipo", "qivo", "xivo", "yibo", "civo", "kivo",
    "nivo", "livo", "sivo", "cepo", "veto", "felo", "melo", "nero", "selo", "telo",
    "dedo", "vepo", "bepo", "tepo", "ribo", "fivo", "gepo", "pobo", "pibo", "google",
    "tune", "tv", "pillow", "people", "keyboard", "pihu", "be bo", "de do", "video",
    "pi lo", "pilo"
]

# Exit phrases
exit_phrases = ["exit", "shutup", "stop", "shut up"]
exit_pattern = r'\b(goodbye|bye)\s+(' + '|'.join(similar_sounds) + r')\b'

goodbye_messages = [
    "Bye-bye for now! Just whisper my name if you need me!",
    "Toodles! I’m just a call away if you miss me!",
    "Catch you later! I’m only a ‘hey PEBO’ away!",
    "See ya! I’ll be right here if you need anything!",
    "Bye for now! Ping me if you need some robot magic!",
    "Going quiet now! But say my name and I’ll wag my circuits!",
    "Snuggling into sleep mode... call me if you want to play!",
    "Goodbye for now! Call on me anytime, I’m always listening.",
    "Logging off! But give me a shout and I’ll be right there!"
]

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
    """Play the reminder audio file twice."""
    try:
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.set_volume(1.0)
        for _ in range(2):
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.25)
        pygame.mixer.music.unload()
        print(f"Played reminder audio {audio_file} twice")
    except Exception as e:
        print(f"❌ Error playing reminder audio {audio_file}: {e}")

def amplify_audio(input_file, output_file, gain_db=10):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", input_file,
        "-filter:a", f"volume={gain_db}dB",
        output_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

async def speak_text(text):
    """Speak using Edge TTS."""
    # ~ voice = "en-US-SoniaNeural" #error voicec
    voice = "en-US-AnaNeural"  # child voice
    # ~ voice = "en-US-JennyNeural" #female voice
    filename = "response.mp3"
    # ~ boosted_file = "boosted_response.mp3"

    tts = edge_tts.Communicate(text, voice)
    await tts.save(filename)

    # ~ amplify_audio(filename, boosted_file, gain_db=20)
    # ~ pygame.mixer.music.load(boosted_file)
    pygame.mixer.music.load(filename)
    
    pygame.mixer.music.set_volume(1.0)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.05)

    pygame.mixer.music.stop()
    pygame.mixer.music.unload()

    os.remove(filename)
    # ~ os.remove(boosted_file)

def listen(
        recognizer: sr.Recognizer,
        mic: sr.Microphone,
        *,
        timeout: float = 8,
        phrase_time_limit: float = 6,
        retries: int = 2,
        language: str = "en-US",
        calibrate_duration: float = 0.5,
) -> str | None:
    """Capture a single utterance and return the recognized text, with LED indicating listening state."""
    # Setup GPIO
    GPIO.setmode(GPIO.BCM)  # Use BCM numbering
    GPIO.setup(LED_PIN, GPIO.OUT)  # Set LED pin as output
    GPIO.output(LED_PIN, GPIO.LOW)  # Ensure LED is off initially

    for attempt in range(retries + 1):

        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=calibrate_duration)
                print("Listening… (attempt", attempt + 1, ")")
                GPIO.output(LED_PIN, GPIO.HIGH)  # Turn on LED
                audio = recognizer.listen(source,
                                          timeout=timeout,
                                          phrase_time_limit=phrase_time_limit)
                GPIO.output(LED_PIN, GPIO.LOW)  # Turn off LED after listening

            try:
                text = recognizer.recognize_google(audio, language=language)
                text = text.strip().lower()
                if text:
                    print(f"You said: {text}")
                    GPIO.cleanup()  # Clean up GPIO
                    return text
            except sr.UnknownValueError:
                print("Sorry—couldn’t understand that.")
            except sr.RequestError as e:
                print(f"Google speech service error ({e}). Falling back to offline engine…")
                try:
                    text = recognizer.recognize_sphinx(audio, language=language)
                    text = text.strip().lower()
                    if text:
                        print(f"(Offline) You said: {text}")
                        GPIO.cleanup()  # Clean up GPIO
                        return text
                except Exception as sphinx_err:
                    print(f"Offline engine failed: {sphinx_err}")

        except sr.WaitTimeoutError:
            print("Timed out waiting for speech.")
            GPIO.output(LED_PIN, GPIO.LOW)  # Turn off LED on timeout
        except Exception as mic_err:
            print(f"Mic/Audio error: {mic_err}")
            GPIO.output(LED_PIN, GPIO.LOW)  # Turn off LED on error

        if attempt < retries:
            time.sleep(0.5)

    print("No intelligible speech captured.")
    GPIO.output(LED_PIN, GPIO.LOW)  # Ensure LED is off
    GPIO.cleanup()  # Clean up GPIO
    return None

# Get IP address of a network interface
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

# Get current Wi-Fi SSID
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

                    # Format task details
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

                    task_info = (f"{description}, due on {deadline.strftime('%B %d at %I:%M %p')}, "
                                f"priority {priority}{reminder_text}. "
                                f"{'It is due soon!' if minutes_until_deadline <= reminder_time1 or minutes_until_deadline <= reminder_time2 else ''}")
                    pending_tasks.append(task_info)
                except ValueError:
                    logger.warning(f"Invalid deadline format for task {task_id}: {deadline_str}")
                    continue

        if not pending_tasks:
            return "You have no pending tasks."

        # Sort tasks by deadline
        #pending_tasks.sort(key=lambda x: dateutil.parser.isoparse(tasks[list(tasks.keys())[pending_tasks.index(x)]].get('deadline')))
        
        # Format response
        task_count = len(pending_tasks)
        if task_count == 1:
            response = f"You have one task: {pending_tasks[0]}"
        else:
            response = f"You have {task_count} tasks: {'; '.join(pending_tasks)}"
        return response

    except Exception as e:
        logger.error(f"Error fetching tasks for user {user_id}: {str(e)}")
        return "Sorry, I couldn't retrieve your tasks due to an error."

# ~ async def start_assistant_from_text(prompt_text):
    # ~ """Starts Gemini assistant with initial text prompt and controls robot emotions."""
    # ~ print(f"\U0001F4AC Initial Prompt: {prompt_text}")
    # ~ conversation_history.clear()
    
    # ~ full_prompt = f"{prompt_text}\nAbove is my message. What is your emotion for that message (Happy, Sad, Angry, Normal, or Love)? If my message includes words like 'love', 'loving', 'beloved', 'adore', 'affection', 'cute', 'adorable', 'sweet', or 'charming', or if the overall sentiment feels loving or cute, set your emotion to Love. Otherwise, determine the appropriate emotion based on the message's context. Provide your answer in the format [emotion, reply], where 'emotion' is one of the specified emotions and 'reply' is your response to my message."
    # ~ conversation_history.append({"role": "user", "parts": [full_prompt]})
    
    # ~ try:
        # ~ response = model.generate_content(conversation_history, generation_config={"max_output_tokens": 20})
    # ~ except google.api_core.exceptions.NotFound as e:
        # ~ print(f"Model not found: {e}. Check for deprecation and update model name.")
    # ~ # Add retry logic or fallback prompt
    # ~ # response = model.generate_content(conversation_history, generation_config={"max_output_tokens": 20})
    # ~ reply = response.text.strip()

    # ~ emotion = "Normal"
    # ~ answer = reply
    # ~ try:
        # ~ match = re.match(r'\[(Happy|Sad|Angry|Normal|Love),(.+?)\]', reply)
        # ~ match = re.match(r'\[(Happy|Sad|Angry|Normal|Love),\s*([^\]]*?)(?:\]|$)', reply, re.DOTALL))
        # ~ if match:
            # ~ emotion, answer = match.groups()
            # ~ print(f"{emotion}: {answer}")
        # ~ else:
            # ~ print(f"Gemini: {reply} (No emotion detected, assuming Normal)")
    # ~ except Exception as e:
        # ~ print(f"Error parsing Gemini response: {e}")

    # ~ valid_emotions = {"Happy", "Sad", "Angry", "Normal", "Love"}
    # ~ emotion_methods = {
        # ~ "Happy": happy,
        # ~ "Sad": sad,
        # ~ "Angry": angry,
        # ~ "Normal": normal,
        # ~ "Love": love
    # ~ }
    # ~ emotion_method = emotion_methods.get(emotion if emotion in valid_emotions else "Normal")
    
    # ~ emotion_task = asyncio.to_thread(emotion_method)
    # ~ voice_task = speak_text(answer)
    # ~ await asyncio.gather(emotion_task, voice_task)
    
    # ~ conversation_history.append({"role": "model", "parts": [answer]})

import google.api_core.exceptions

async def start_assistant_from_text(prompt_text):
    """Starts Gemini assistant with initial text prompt and controls robot emotions."""
    print(f"Initial Prompt: {prompt_text}")
    conversation_history.clear()
    
    full_prompt = f"""
{prompt_text}
Above is my message. Your name is "PEBO". If my message above you, say you are "PEBO". What is your emotion for that message (Happy, Sad, Angry, Normal, or Love)? 
If my message includes words like 'love', 'loving', 'beloved', 'adore', 'affection', 'cute', 'adorable', 'sweet', or 'charming', 
or if the overall sentiment feels loving or cute, set your emotion to Love. 
Otherwise, determine the appropriate emotion based on the message's context. 
Provide your answer in the format [emotion, reply], where 'emotion' is one of the specified emotions and 'reply' is your response to my message. Ensure the response is complete with a closing bracket ].
"""
    conversation_history.append({"role": "user", "parts": [full_prompt]})
    
    max_tokens = 20  # Increased to prevent truncation
    retry_attempts = 3
    attempt = 0
    reply = None
    
    while attempt < retry_attempts:
        try:
            response = model.generate_content(
                conversation_history,
                generation_config={"max_output_tokens": max_tokens}
            )
            reply = response.text.strip()
            # ~ print(f"DEBUG: Raw Gemini response: '{reply}'")  # Log raw response for debugging
            break  # Exit retry loop on successful response
        except google.api_core.exceptions.NotFound as e:
            print(f"Model not found: {e}. Check for deprecation and update model name.")
            return
        except Exception as e:
            print(f"Error generating response (attempt {attempt + 1}/{retry_attempts}): {e}")
            attempt += 1
            max_tokens += 50  # Increase token limit for retry
            if attempt == retry_attempts:
                print("Max retries reached. Falling back to Normal emotion.")
                reply = "[Normal, Could not process the response due to an error.]"
                break
            time.sleep(0.5)  # Brief delay before retry

    if reply is None:
        print("No response received from Gemini. Falling back to Normal emotion.")
        reply = "[Normal, No response from assistant.]"

    emotion = "Normal"
    answer = reply
    try:
        # Match [emotion, reply] with optional closing bracket
        # ~ print(f"Reply Debug:{reply}")
        match = re.match(r'\[(Happy|Sad|Angry|Normal|Love),\s*([^\]]*?)(?:\]|$)', reply, re.DOTALL)
        if match:
            emotion, answer = match.groups()
            print(f"{emotion}: {answer}")
            if not reply.endswith(']'):
                print("Warning: Response missing closing bracket. Parsed anyway.")
        else:
            # ~ print(f"Gemini: {reply} (No emotion detected, assuming Normal)")
            if not reply.startswith('['):
                print("Warning: Response format invalid. Expected [emotion, reply].")
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        print(f"Raw response: {reply}")

    valid_emotions = {"Happy", "Sad", "Angry", "Normal", "Love"}
    emotion_methods = {
        "Happy": happy,
        "Sad": sad,
        "Angry": angry,
        "Normal": normal,
        "Love": love
    }
    emotion_method = emotion_methods.get(emotion if emotion in valid_emotions else "Normal")
    
    # Run emotion and voice tasks
    try:
        emotion_task = asyncio.to_thread(emotion_method)
        voice_task = speak_text(answer)
        await asyncio.gather(emotion_task, voice_task)
    except Exception as e:
        print(f"Error executing emotion or voice task: {e}")

    # Append the full response to conversation history
    conversation_history.append({"role": "model", "parts": [reply]})


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
        # Check reminder file
        reminder_text = read_reminder_file()
        if reminder_text:
            print(f"Found reminder: {reminder_text}")
            # Speak the reminder text
            play_reminder_audio()
            await speak_text(reminder_text)
            # Play reminder audio twice
            play_reminder_audio()
            await speak_text(reminder_text)
            # Clear the reminder file
            if not clear_reminder_file():
                logger.error("Failed to clear reminder file, proceeding anyway")
            # Continue with the loop
            failed_attempts = 0  # Reset failed attempts after processing reminder
        else:
            print("📝 Reminder file is empty or not found, proceeding with normal loop")

        user_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
        # user_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen_whisper())
        # Uncomment to use Whisper instead

        if user_input is None:
            failed_attempts += 1
            print(f"Failed attempt {failed_attempts}/{max_attempts}.")
            if failed_attempts >= max_attempts:
                print(f"No speech detected after {max_attempts} attempts. Exiting assistant.")
                message = random.choice(goodbye_messages)
                await speak_text(message)
                normal()
                break
        GPIO.setmode(GPIO.BCM)  # Reinitialize GPIO mode
        GPIO.setup(TOUCH_PIN, GPIO.IN)  # Reinitialize touch pin
        failed_attempts = 0  # Reset on valid input
        
        # Check for "what are my tasks"
        if user_input.lower() in ["what are reminders", "list reminders", "show reminders", "tell me my reminders","show remind","list remind"]:
            try:
                # Read user ID from pebo_config.json
                with open(JSON_CONFIG_PATH, 'r') as config_file:
                    config = json.load(config_file)
                    user_id = config.get('userId')
                
                if not user_id:
                    logger.error("Missing userId in config file")
                    await speak_text("Sorry, I couldn't find your user ID.")
                    await asyncio.to_thread(normal)
                    continue

                # Fetch tasks from Firebase
                task_response = fetch_user_tasks(user_id)
                await asyncio.gather(
                    speak_text(task_response),
                    asyncio.to_thread(normal)  # Express normal emotion for tasks
                )
                continue

            except FileNotFoundError:
                logger.error(f"Config file {JSON_CONFIG_PATH} not found")
                await speak_text("Sorry, I couldn't read the user configuration.")
                await asyncio.to_thread(normal)
                continue
            except Exception as e:
                logger.error(f"Error fetching tasks: {str(e)}")
                await speak_text("Sorry, there was an error retrieving your tasks.")
                await asyncio.to_thread(normal)
                continue

        # Check for "play song" with or without a song name
        song_match = re.match(r'^play\s+a\s+song\s+(.+)$', user_input, re.IGNORECASE)
        if song_match or user_input == "play a song" or user_input == "play song":
            max_song_attempts = 1
            if song_match:
                song_input = song_match.group(1).strip()  # Extract song name
            else:
                await speak_text("What song should I play?")
                await asyncio.to_thread(normal)  # Set arms to neutral and eyes to normal
                song_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
                if song_input is None:
                    await speak_text("Sorry, I couldn't get the song name. Let's try something else.")
                    await asyncio.to_thread(normal)  # Set arms to neutral and eyes to normal
                    continue

            for attempt in range(max_song_attempts):
                if song_input:
                    await speak_text(f"Your song is {song_input}. Is that correct?")
                    await asyncio.to_thread(normal)  # Set arms to neutral and eyes to normal
                    confirmation = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
                    
                    if confirmation is None:
                        if attempt < max_song_attempts - 1:
                            await speak_text(f"I didn't hear you. Is {song_input} the correct song?")
                            await asyncio.to_thread(normal)  # Set arms to neutral and eyes to normal
                            continue
                        else:
                            await speak_text("Sorry, I couldn't confirm the song. Let's try something else.")
                            await asyncio.to_thread(normal)  # Set arms to neutral and eyes to normal
                            break

                    confirmation = confirmation.lower()
                    if any(pos in confirmation for pos in positive_responses):
                        await play_music(song_input, None, TOUCH_PIN)  # Pass TOUCH_PIN
                        await asyncio.to_thread(normal)
                        break
                    elif any(neg in confirmation for neg in negative_responses):
                        if attempt < max_song_attempts - 1:
                            await speak_text("Okay, what song should I play?")
                            await asyncio.to_thread(normal)  # Set arms to neutral and eyes to normal
                            song_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
                            if song_input is None:
                                if attempt < max_song_attempts - 2:
                                    await speak_text("I didn't catch that. What song should I play?")
                                    await asyncio.to_thread(normal)  # Set arms to neutral and eyes to normal
                                    continue
                                else:
                                    await speak_text("Sorry, I couldn't get the song name. Let's try something else.")
                                    await asyncio.to_thread(normal)  # Set arms to neutral and eyes to normal
                                    break
                        else:
                            await speak_text("Sorry, I couldn't get the right song after a few tries. Let's try something else.")
                            await asyncio.to_thread(normal)  # Set arms to neutral and eyes to normal
                    else:
                        if attempt < max_song_attempts - 1:
                            await speak_text(f"I didn't understand. Is {song_input} the correct song?")
                            await asyncio.to_thread(normal)  # Set arms to neutral and eyes to normal
                            continue
                        else:
                            await speak_text("Sorry, I couldn't confirm the song. Let's try something else.")
                            await asyncio.to_thread(normal)  # Set arms to neutral and eyes to normal
                            break
                else:
                    if attempt < max_song_attempts - 1:
                        await speak_text("I didn't catch that. What song should I play?")
                        await asyncio.to_thread(normal)  # Set arms to neutral and eyes to normal
                        song_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
                    else:
                        await speak_text("Sorry, I couldn't get the song name. Let's try something else.")
                        await asyncio.to_thread(normal)  # Set arms to neutral and eyes to normal
                        break
            continue  # Continue listening after song handling
            
        # Show QR to scanner
        if user_input.lower() in ["show q r", "show me q r", "show qr", "show me qr", "show me q", "show q"]:
            try:
                # Read device ID from pebo_config.json
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
                asyncio.to_thread(run_emotion, None, lambda stop_event: eyes.QR(device_id, stop_event=stop_event), duration=15)
            )
            await asyncio.to_thread(normal)
            continue
            
        # Inter-device communication part
        if user_input == "send message":
            try:
                # Read pebo_config.json to get the current device's SSID, deviceId, and userId
                with open(JSON_CONFIG_PATH, 'r') as config_file:
                    config = json.load(config_file)
                    current_ssid = config.get('ssid')
                    current_device_id = config.get('deviceId')
                    user_id = config.get('userId')
                
                if not current_ssid or not current_device_id or not user_id:
                    logger.error("Missing SSID, deviceId, or userId in config file")
                    await speak_text("Sorry, I couldn't read the device configuration.")
                    await asyncio.to_thread(normal)
                    continue

                # Get current IP address
                current_ip = get_ip_address()
                if not current_ip:
                    logger.error("No Wi-Fi connection detected")
                    await speak_text("Cannot initiate communication: Not connected to Wi-Fi.")
                    await asyncio.to_thread(normal)
                    continue

                # Query Firebase for devices on the same SSID, excluding this device
                users_ref = db.reference('users')
                users = users_ref.get()
                if not users:
                    logger.info("No users found in Firebase")
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
                    logger.info(f"No devices found on SSID {current_ssid}")
                    await speak_text(f"No other devices found on Wi-Fi {current_ssid}.")
                    await asyncio.to_thread(normal)
                    continue

                # Prepare list of locations for user prompt
                locations = [device['location'] for device in same_wifi_devices]
                locations_str = ", ".join(locations[:-1]) + (f", or {locations[-1]}" if len(locations) > 1 else locations[0])
                print(f"Which device would you like to connect in {locations_str}?")
                await speak_text(f"Which device would you like to connect in {locations_str}?")
                
                await asyncio.to_thread(normal)

                # Get user input for device location
                location_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
                if not location_input:
                    await speak_text("Sorry, I didn't catch that. Let's try something else.")
                    await asyncio.to_thread(normal)
                    continue

                # Find the device matching the user's input
                selected_device = None
                for device in same_wifi_devices:
                    if location_input.lower() in device['location'].lower():
                        selected_device = device
                        break

                if selected_device:
                    print(f"Selected Device: Location={selected_device['location']}, IP={selected_device['ip_address']}")
                    await speak_text(f"Connected to PEBO in {selected_device['location']}. Double-tap to stop communication.")
                    await asyncio.to_thread(normal)
                    # Reinitialize GPIO before starting audio node
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setup(TOUCH_PIN, GPIO.IN)
                    # Run start_audio_node in a separate thread to allow async continuation
                    audio_thread = threading.Thread(
                        target=start_audio_node,
                        args=(8888, selected_device['ip_address'], 8889, TOUCH_PIN)
                    )
                    audio_thread.daemon = True
                    audio_thread.start()
                    audio_thread.join()  # Wait for audio node to complete (stops on double-tap)
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
            continue

        if user_input in exit_phrases or re.search(exit_pattern, user_input, re.IGNORECASE):
            print("Exiting assistant.")
            message_exit = random.choice(goodbye_messages)
            await speak_text(message_exit)
            normal()
            break

        full_user_input = f"{user_input}\nAbove is my conversation part. What is your emotion for that conversation (Happy, Sad, Angry, Normal, or Love)? If my conversation includes words like 'love', 'loving', 'beloved', 'adore', 'affection', 'cute', 'adorable', 'sweet', or 'charming', or if the overall sentiment feels loving or cute, set your emotion to Love. Otherwise, determine the appropriate emotion based on the conversation's context. Your emotion is [emotion] and your answer for above conversation is [answer]. Give your answer as [emotion,answer]"
        conversation_history.append({"role": "user", "parts": [full_user_input]})
        response = model.generate_content(conversation_history, generation_config={"max_output_tokens": 20})
        reply = response.text.strip()

        emotion = "Normal"
        answer = reply
        try:
            match = re.match(r'\[(Happy|Sad|Angry|Normal|Love),\s*([^\]]*?)(?:\]|$)', reply)
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
    
    # Clean up Firebase app
    try:
        firebase_admin.delete_app(firebase_admin.get_app())
        logger.info("Firebase app cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up Firebase app: {str(e)}")
    
    cleanup()
    print("this in assistant")
    await asyncio.sleep(0.5)

async def monitor_for_trigger(name, emotion):
    initialize_hardware()
    normal()
    
    while True:
        print("🎧 Waiting for trigger phrase (e.g., 'hi PEBO', 'PEBO')...")
        text = listen(recognizer, mic)
        if text:
            trigger_pattern = r'\b((?:hi|hey|hello)\s+)?(' + '|'.join(re.escape(s) for s in similar_sounds) + r')\b'
            if re.search(trigger_pattern, text, re.IGNORECASE):
                print("✅ Trigger phrase detected! Starting assistant...")
                print(f"Using: Name={name}, Emotion={emotion}")
                if name and name.lower() != "none":
                    hi_task = asyncio.to_thread(hi)
                    voice_task = speak_text("Hello!")
                    await asyncio.gather(hi_task, voice_task)
                    if emotion.upper() in {"SAD", "HAPPY", "CONFUSED", "FEAR", "ANGRY"}:
                        await start_assistant_from_text(f"I am {name}. I look {emotion}. Ask why.")

                    else:
                        await start_assistant_from_text(f"I am {name}. I need your assist.")
     
                else:
                    await speak_text("I can't identify you as my user")
            else:
                continue
        
        print("🖥️ Cleaning up in monitor_for_trigger: Clearing displays and I2C bus...")

async def monitor_start():
    initialize_hardware()
    normal()
    
    try:
        print("🎧 Waiting for initial speech input...")
        print(f"Using: Name={name}, Emotion={emotion}")
        if name and name.lower() != "none":
            hi_task = asyncio.to_thread(hi)
            voice_task = speak_text("Hello!")
            await asyncio.gather(hi_task, voice_task)
            await start_assistant_from_text(f"I am {name}. I look {emotion}. Ask why.")
            
        else:
            await speak_text("I can't identify you as my user")
            
    finally:
        print("🖥️ Cleaning up in monitor_start: Clearing displays and I2C bus...")
        

async def monitor_new():
    initialize_hardware()
    normal()
    
    while True:
        print("🎧 Waiting for trigger phrase (e.g., 'hi PEBO', 'PEBO')...")

        name, emotion = read_recognition_result()
        
        if emotion.upper() in {"SAD", "HAPPY", "CONFUSED", "FEAR", "ANGRY"}:
            hi_task = asyncio.to_thread(hi)
            voice_task = speak_text("Hello!")
            await asyncio.gather(hi_task, voice_task)
            await start_assistant_from_text(f"I am {name}. I look {emotion}. Ask why.")
                
        else:
            text = listen(recognizer, mic)
            if text:
            
                trigger_pattern = r'\b((?:hi|hey|hello)\s+)?(' + '|'.join(re.escape(s) for s in similar_sounds) + r')\b'
                qr_pattern = r'\bshow\s+(me\s+)?q\s*r\b|\bshow\s+q\b'  # Matches "show qr", "show me qr", "show q"
                if re.search(trigger_pattern, text, re.IGNORECASE):
                    print("✅ Trigger phrase detected! Starting assistant...")
                    print(f"Using: Name={name}, Emotion={emotion}")
                    if name and name.lower() != "none":
                        hi_task = asyncio.to_thread(hi)
                        voice_task = speak_text("Hello! ")
                        await asyncio.gather(hi_task, voice_task)
                        if emotion.upper() in {"SAD", "HAPPY", "CONFUSED", "FEAR", "ANGRY"}:
                            await start_assistant_from_text(f"I am {name}. I look {emotion}. Ask why.")

                        else:
                            await start_assistant_from_text(f"I am {name}. I need your assist.")
             
                    else:
                        await speak_text("I can't identify you as my user")
                        
                # Check for QR code display
                if re.search(qr_pattern, text, re.IGNORECASE):
                    try:
                        # Read device ID from pebo_config.json
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
                        asyncio.to_thread(run_emotion, None, lambda stop_event: eyes.QR(device_id, stop_event=stop_event), duration=15)
                    )
                    await asyncio.to_thread(normal)  # Return to normal state
                    continue
            
            else:
                continue
        
        print("🖥️ Cleaning up in monitor_new: Clearing displays and I2C bus...")
        
if __name__ == "__main__":
    try:
        name = "Bhagya"
        emotion = "Happy"
        asyncio.run(monitor_new())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    finally:
        print("Program terminated")

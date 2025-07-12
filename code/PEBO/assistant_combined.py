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
from display.eyes import RoboEyesDual
from interaction.play_song import play_music

# Constants for I2C addresses
PCA9685_ADDR = 0x40
LEFT_EYE_ADDRESS = 0x3D
RIGHT_EYE_ADDRESS = 0x3C

# Global variables for hardware control
i2c = None
eyes = None
current_eye_thread = None
stop_event = None


# LED pin configuration
LED_PIN = 18  # GPIO pin number (Pin 12)

def initialize_hardware():
    """Initialize I2C and eyes globally."""
    global i2c, eyes
    i2c = busio.I2C(board.SCL, board.SDA)
    eyes = RoboEyesDual(LEFT_EYE_ADDRESS, RIGHT_EYE_ADDRESS)
    eyes.begin(128, 64, 40)

def run_emotion(arm_func, eye_func):
    """Run arm movement and eye expression simultaneously, then return to normal mode"""
    global current_eye_thread, stop_event
    stop_event = threading.Event()
    
    current_eye_thread = threading.Thread(target=eye_func, args=(stop_event,))
    current_eye_thread.daemon = True
    current_eye_thread.start()
    
    arm_func()
    
    time.sleep(1)
    
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
    stop_event = threading.Event()
    current_eye_thread = threading.Thread(target=eyes.Default, args=(stop_event,))
    current_eye_thread.daemon = True
    current_eye_thread.start()
    stop_event = None

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

# Initialize pygame
pygame.mixer.init()

# Gemini API setup
GOOGLE_API_KEY = "AIzaSyDjx04eYTq-09j7kzd24NeZfwYZ7eu3w9Q"  # Replace with your actual API key
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

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

def amplify_audio(input_file, output_file, gain_db=10):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", input_file,
        "-filter:a", f"volume={gain_db}dB",
        output_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

async def speak_text(text):
    """Speak using Edge TTS."""
    voice = "en-GB-SoniaNeural"
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

    os.remove(filename)
    os.remove(boosted_file)

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
                print("\U0001F3A4 Listening… (attempt", attempt + 1, ")")
                GPIO.output(LED_PIN, GPIO.HIGH)  # Turn on LED
                audio = recognizer.listen(source,
                                          timeout=timeout,
                                          phrase_time_limit=phrase_time_limit)
                GPIO.output(LED_PIN, GPIO.LOW)  # Turn off LED after listening

            try:
                text = recognizer.recognize_google(audio, language=language)
                text = text.strip().lower()
                if text:
                    print(f"\U0001F5E3️ You said: {text}")
                    GPIO.cleanup()  # Clean up GPIO
                    return text
            except sr.UnknownValueError:
                print("\U0001F914 Sorry—couldn’t understand that.")
            except sr.RequestError as e:
                print(f"\u26A0\uFE0F Google speech service error ({e}). Falling back to offline engine…")
                try:
                    text = recognizer.recognize_sphinx(audio, language=language)
                    text = text.strip().lower()
                    if text:
                        print(f"\U0001F5E3️ (Offline) You said: {text}")
                        GPIO.cleanup()  # Clean up GPIO
                        return text
                except Exception as sphinx_err:
                    print(f"\u274C Offline engine failed: {sphinx_err}")

        except sr.WaitTimeoutError:
            print("\u231B Timed out waiting for speech.")
            GPIO.output(LED_PIN, GPIO.LOW)  # Turn off LED on timeout
        except Exception as mic_err:
            print(f"\U0001F3A4 Mic/Audio error: {mic_err}")
            GPIO.output(LED_PIN, GPIO.LOW)  # Turn off LED on error

        if attempt < retries:
            time.sleep(0.5)

    print("\U0001F615 No intelligible speech captured.")
    GPIO.output(LED_PIN, GPIO.LOW)  # Ensure LED is off
    GPIO.cleanup()  # Clean up GPIO
    return None

# Load the Whisper model once
whisper_model = whisper.load_model("base")

def listen_whisper(duration=1, sample_rate=16000) -> str | None:
    """Capture audio and transcribe using Whisper."""
    print("🎤 Listening with Whisper…")

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
            os.remove(audio_path)
        except:
            pass

import firebase_admin
from firebase_admin import credentials, db
import json
import socket
import fcntl
import struct
import subprocess
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

# Firebase configuration
SERVICE_ACCOUNT_PATH = '/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/ipconfig/firebase_config.json'
DATABASE_URL = 'https://pebo-task-manager-767f3-default-rtdb.asia-southeast1.firebasedatabase.app'
JSON_CONFIG_PATH = "/home/pi/pebo_config.json"

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

async def start_assistant_from_text(prompt_text):
    """Starts Gemini assistant with initial text prompt and controls robot emotions."""
    print(f"\U0001F4AC Initial Prompt: {prompt_text}")
    conversation_history.clear()
    
    full_prompt = f"{prompt_text}\nAbove is my message. What is your emotion for that message (Happy, Sad, Angry, Normal, or Love)? If my message includes words like 'love', 'loving', 'beloved', 'adore', 'affection', 'cute', 'adorable', 'sweet', or 'charming', or if the overall sentiment feels loving or cute, set your emotion to Love. Otherwise, determine the appropriate emotion based on the message's context. Provide your answer in the format [emotion, reply], where 'emotion' is one of the specified emotions and 'reply' is your response to my message."
    conversation_history.append({"role": "user", "parts": [full_prompt]})

    response = model.generate_content(conversation_history, generation_config={"max_output_tokens": 60})
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
        user_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
        # user_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen_whisper())
        # Uncomment to use Whisper instead

        if user_input is None:
            failed_attempts += 1
            print(f"\U0001F615 Failed attempt {failed_attempts}/{max_attempts}.")
            if failed_attempts >= max_attempts:
                print(f"\U0001F615 No speech detected after {max_attempts} attempts. Exiting assistant.")
                message = random.choice(goodbye_messages)
                await speak_text(message)
                normal()
                break
            continue

        failed_attempts = 0  # Reset on valid input
        
        # Check for "play song" with or without song name
        song_match = re.match(r'^play\s+a\s+song\s+(.+)$', user_input, re.IGNORECASE)
        if song_match or user_input == "play a song" or user_input == "play song":
            max_song_attempts = 3
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
                        await play_music(song_input, None)  # Pass None for controller
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
                    await speak_text(f"Selected device in {selected_device['location']} with IP {selected_device['ip_address']}.")
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
            print("\U0001F44B Exiting assistant.")
            message_exit = random.choice(goodbye_messages)
            await speak_text(message_exit)
            normal()
            break

        full_user_input = f"{user_input}\nAbove is my conversation part. What is your emotion for that conversation (Happy, Sad, Angry, Normal, or Love)? If my conversation includes words like 'love', 'loving', 'beloved', 'adore', 'affection', 'cute', 'adorable', 'sweet', or 'charming', or if the overall sentiment feels loving or cute, set your emotion to Love. Otherwise, determine the appropriate emotion based on the conversation's context. Your emotion is [emotion] and your answer for above conversation is [answer]. Give your answer as [emotion,answer]"
        conversation_history.append({"role": "user", "parts": [full_user_input]})
        response = model.generate_content(conversation_history, generation_config={"max_output_tokens": 60})
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
    
    # Clean up Firebase app
    try:
        firebase_admin.delete_app(firebase_admin.get_app())
        logger.info("Firebase app cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up Firebase app: {str(e)}")
    
    cleanup()
    print("this in assistant")
    await asyncio.sleep(1)

async def monitor_for_trigger(name, emotion):
    initialize_hardware()
    normal()
    
    print("🎧 Waiting for trigger phrase (e.g., 'hi PEBO', 'PEBO')...")
    text = listen(recognizer, mic)
    if text:
        trigger_pattern = r'\b((?:hi|hey|hello)\s+)?(' + '|'.join(re.escape(s) for s in similar_sounds) + r')\b'
        if re.search(trigger_pattern, text, re.IGNORECASE):
            print("✅ Trigger phrase detected! Starting assistant...")
            print(f"Using: Name={name}, Emotion={emotion}")
            if name and name.lower() != "none":
                hi_task = asyncio.to_thread(hi)
                voice_task = speak_text("Hello! I'm your pebo.")
                await asyncio.gather(hi_task, voice_task)
                if emotion.upper() in {"SAD", "HAPPY", "CONFUSED", "FEAR", "ANGRY"}:
                    await start_assistant_from_text(f"I am {name}. I look {emotion}. Ask why.")
                else:
                    await start_assistant_from_text(f"I am {name}. I need your assist.")
            else:
                await speak_text("I can't identify you as my user")
        await asyncio.sleep(0.5)
    
    print("🖥️ Cleaning up in monitor_for_trigger: Clearing displays and I2C bus...")
    cleanup()
    await asyncio.sleep(0.5)
        
async def monitor_start(name, emotion):
    """Run once to initialize the assistant with a single speech input."""
    initialize_hardware()
    normal()
    
    try:
        print("🎧 Waiting for initial speech input...")
        print(f"Using: Name={name}, Emotion={emotion}")
        if name and name.lower() != "none":
            hi_task = asyncio.to_thread(hi)
            voice_task = speak_text("Hello! I'm your pebo.")
            await asyncio.gather(hi_task, voice_task)
            await start_assistant_from_text(f"I am {name}. I look {emotion}. Ask why.")
        else:
            await speak_text("I can't identify you as my user")
    finally:
        print("🖥️ Cleaning up in monitor_start: Clearing displays and I2C bus...")
        cleanup()
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    try:
        name = "Bhagya"
        emotion = "Clam"
        asyncio.run(monitor_for_trigger(name, emotion))
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    finally:
        print("Program terminated")

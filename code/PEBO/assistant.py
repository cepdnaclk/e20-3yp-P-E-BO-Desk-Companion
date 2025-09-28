#!/usr/bin/env python3
"""
Voice Assistant with Robot Control
Listens for trigger phrases and controls robot emotions with simultaneous arm/eye expressions and voice output
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
from arm_eyes import RobotController  # Import RobotController from arm_eyes.py

# Initialize pygame
pygame.mixer.init()

# Gemini API setup
GOOGLE_API_KEY = "AIzaSyB1JOAtxltrujUYSXVWD4GAa4pv2N3N4PM"  # Replace with your actual API key
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
    read_retry_delay = 0.5  # seconds

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

async def speak_text(text, controller):
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
        await asyncio.sleep(0.25)  # Use asyncio.sleep for non-blocking

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
    """
    Capture a single utterance and return the recognized text.
    """
    for attempt in range(retries + 1):
        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=calibrate_duration)
                print("\U0001F3A4 Listening… (attempt", attempt + 1, ")")
                audio = recognizer.listen(source,
                                          timeout=timeout,
                                          phrase_time_limit=phrase_time_limit)

            try:
                text = recognizer.recognize_google(audio, language=language)
                text = text.strip().lower()
                if text:
                    print(f"\U0001F5E3️  You said: {text}")
                    return text
            except sr.UnknownValueError:
                print("\U0001F914  Sorry—couldn’t understand that.")
            except sr.RequestError as e:
                print(f"\u26A0\uFE0F  Google speech service error ({e}). Falling back to offline engine…")
                try:
                    text = recognizer.recognize_sphinx(audio, language=language)
                    text = text.strip().lower()
                    if text:
                        print(f"\U0001F5E3️  (Offline) You said: {text}")
                        return text
                except Exception as sphinx_err:
                    print(f"\u274C  Offline engine failed: {sphinx_err}")

        except sr.WaitTimeoutError:
            print("\u231B Timed out waiting for speech.")
        except Exception as mic_err:
            print(f"\U0001F3A4 Mic/Audio error: {mic_err}")

        if attempt < retries:
            time.sleep(0.5)

    print("\U0001F615  No intelligible speech captured.")
    return None

# Load the Whisper model once
whisper_model = whisper.load_model("base")  # Try "tiny" or "small" if Pi is slow

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
            print(f"🗣️  You said (Whisper): {text}")
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

async def start_assistant_from_text(prompt_text, controller):
    """Starts Gemini assistant with initial text prompt and controls robot emotions."""
    print(f"\U0001F4AC Initial Prompt: {prompt_text}")
    conversation_history.clear()
    # Append emotion prompt
    full_prompt = f"{prompt_text}\n{prompt_text} Above is my message. What is your emotion for that message (Happy, Sad, Angry, Normal, or Love)? If my message includes words like 'love', 'loving', 'beloved', 'adore', 'affection', 'cute', 'adorable', 'sweet', or 'charming', or if the overall sentiment feels loving or cute, set your emotion to Love. Otherwise, determine the appropriate emotion based on the message's context. Provide your answer in the format [emotion, reply], where 'emotion' is one of the specified emotions and 'reply' is your response to my message."
    conversation_history.append({"role": "user", "parts": [full_prompt]})

    # Generate response from Gemini
    response = model.generate_content(conversation_history, generation_config={"max_output_tokens": 60})
    reply = response.text.strip()

    # Parse response to extract emotion and answer
    emotion = "Normal"  # Default emotion for Gemini response
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

    # Trigger robot emotion and voice output simultaneously
    valid_emotions = {"Happy", "Sad", "Angry", "Normal", "Love"}
    emotion_methods = {
        "Happy": controller.happy,
        "Sad": controller.sad,
        "Angry": controller.angry,
        "Normal": controller.normal,
        "Love": controller.love
    }
    # Use Normal for arm/eye if emotion is not in valid_emotions
    emotion_method = emotion_methods.get(emotion if emotion in valid_emotions else "Normal")
    
    # Start emotion expression and voice output concurrently
    emotion_task = asyncio.to_thread(emotion_method)  # Run emotion in a thread
    voice_task = speak_text(answer, controller)  # Run voice output
    await asyncio.gather(emotion_task, voice_task)  # Run both tasks simultaneously
    
    conversation_history.append({"role": "model", "parts": [answer]})

    failed_attempts = 0
    max_attempts = 1

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
                await speak_text(message, controller)
                controller.normal()
                break
            continue

        failed_attempts = 0  # Reset on valid input

        if user_input in exit_phrases or re.search(exit_pattern, user_input, re.IGNORECASE):
            print("\U0001F44B Exiting assistant.")
            await speak_text("Goodbye!", controller)
            controller.normal()
            break

        # Append emotion prompt
        full_user_input = f"{user_input}\nAbove is my conversation part. What is your emotion for that conversation (Happy, Sad, Angry, Normal, or Love)? If my conversation includes words like 'love', 'loving', 'beloved', 'adore', 'affection', 'cute', 'adorable', 'sweet', or 'charming', or if the overall sentiment feels loving or cute, set your emotion to Love. Otherwise, determine the appropriate emotion based on the conversation's context. Your emotion is [emotion] and your answer for above conversation is [answer]. Give your answer as [emotion,answer]"
        conversation_history.append({"role": "user", "parts": [full_user_input]})
        response = model.generate_content(conversation_history, generation_config={"max_output_tokens": 60})
        reply = response.text.strip()

        # Parse response
        emotion = "Normal"
        answer = reply
        try:
            match = re.match(r'\[(Happy|Sad|Angry|Normal|Love),(.+?)\]', reply)
            if match:
                emotion, answer = match.groups()
                print(f"{emotion} : {answer}")
            else:
                print(f"Gemini: {reply} (No emotion detected, assuming Normal)")
        except Exception as e:
            print(f"Error parsing Gemini response: {e}")

        # Trigger robot emotion and voice output simultaneously
        emotion_method = emotion_methods.get(emotion if emotion in valid_emotions else "Normal")
        emotion_task = asyncio.to_thread(emotion_method)  # Run emotion in a thread
        voice_task = speak_text(answer, controller)  # Run voice output
        await asyncio.gather(emotion_task, voice_task)  # Run both tasks simultaneously
        
        conversation_history.append({"role": "model", "parts": [answer]})
    controller.cleanup()
    print("this in assistant")
    await asyncio.sleep(1)

async def monitor_for_trigger(name, emotion):
    controller = RobotController()
    controller.normal()
    
    
    print("🎧 Waiting for trigger phrase (e.g., 'hi PEBO', 'PEBO')...")
    text = listen(recognizer, mic)
    if text:
        trigger_pattern = r'\b((hi|hey|hello)\s+)?(' + '|'.join(similar_sounds) + r')\b'
        if re.search(trigger_pattern, text, re.IGNORECASE):
            print("✅ Trigger phrase detected! Starting assistant...")
            print(f"Using: Name={name}, Emotion={emotion}")
            if name and name.lower() != "none":
                hi_task = asyncio.to_thread(controller.hi)
                voice_task = speak_text("Hello! I'm your pebo.", controller)
                await asyncio.gather(hi_task, voice_task)
                if emotion.upper() in {"SAD", "HAPPY", "CONFUSED", "FEAR", "ANGRY"}:
                    await start_assistant_from_text(f"I am {name}. I look {emotion}. Ask why.", controller)
                else:
                    await start_assistant_from_text(f"I am {name}. I need your assist.", controller)
            else:
                await speak_text("I can't identify you as my user", controller)
        await asyncio.sleep(0.5)
    
    print("🖥️ Cleaning up in monitor_for_trigger: Clearing displays and I2C bus...")
        # ~ controller.cleanup()  # Clear displays, reset arms, and deinitialize I2C bus
        # ~ await asyncio.sleep(0.5)
    controller.cleanup()
    await asyncio.sleep(0.5)
        
async def monitor_start(name, emotion):
    """Run once to initialize the assistant with a single speech input."""
    controller = RobotController()
    controller.normal()
    
    try:
        print("🎧 Waiting for initial speech input...")
        print(f"Using: Name={name}, Emotion={emotion}")
        if name and name.lower() != "none":
            hi_task = asyncio.to_thread(controller.hi)
            voice_task = speak_text("Hello! I'm your pebo.", controller)
            await asyncio.gather(hi_task, voice_task)
            await start_assistant_from_text(f"I am {name}. I look {emotion}. Ask why.", controller)
        else:
            await speak_text("I can't identify you as my user", controller)
    finally:
        print("🖥️ Cleaning up in monitor_start: Clearing displays and I2C bus...")
        controller.cleanup()  # Clear displays, reset arms, and deinitialize I2C bus
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    try:
        name = "Bhagya"
        emotion = "Sad"
        asyncio.run(monitor_start(name, emotion))
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    finally:
        print("Program terminated")

import google.generativeai as genai
import pygame
import time
import os
import asyncio
import edge_tts
import speech_recognition as sr
import threading
import subprocess
import json
import queue
import signal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize pygame for audio playback
pygame.mixer.init()

# Set up Google Gemini API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-pro")
conversation_history = []

# Queues
trigger_queue = queue.Queue()
command_queue = queue.Queue()

# Helper function to play TTS using edge_tts
async def speak_text(text):
    communicate = edge_tts.Communicate(text, voice="en-US-SaraNeural")
    await communicate.save("response.mp3")
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()
    pygame.mixer.music.load("response.mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
    os.remove("response.mp3")

# Speech recognition function
def recognize_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening for command...")
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
            text = recognizer.recognize_google(audio)
            print("Recognized:", text)
            return text.lower()
        except (sr.UnknownValueError, sr.RequestError, sr.WaitTimeoutError):
            print("Speech not recognized.")
            return ""

# Wake word detection
def listen_for_wake_word():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening for wake word...")
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=4)
            text = recognizer.recognize_google(audio).lower()
            print("Heard:", text)
            if "hey pebo" in text:
                trigger_queue.put("WAKE")
        except Exception:
            pass

# Face tracking thread
face_tracking_active = False
def face_tracking_thread_function():
    global face_tracking_active
    face_tracking_active = True
    try:
        process = subprocess.Popen(["python3", "face_tracking.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while True:
            output = process.stdout.readline()
            if output:
                decoded = output.decode("utf-8").strip()
                print("Face Tracking Output:", decoded)
                if decoded == "FACE_DETECTED":
                    trigger_queue.put("FACE_DETECTED")
            if process.poll() is not None:
                break
    except Exception as e:
        print("Face tracking thread error:", e)
    finally:
        face_tracking_active = False

def user_identifier_thread_function():
    try:
        subprocess.run(["python3", "user_identifier.py"])
    except Exception as e:
        print("User identifier thread error:", e)

# Audio message sending
def send_audio_message():
    try:
        receiver_ip = os.getenv("RECEIVER_IP", "192.168.1.100")
        subprocess.run(["python3", "inter_device_communication_send_audio.py", receiver_ip])
    except Exception as e:
        print("Audio send error:", e)

# Graceful shutdown
stop_event = threading.Event()
def signal_handler(sig, frame):
    stop_event.set()
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Main loop
def main():
    print("PEBO Assistant Ready")
    while not stop_event.is_set():
        if not face_tracking_active:
            threading.Thread(target=listen_for_wake_word).start()

        try:
            trigger = trigger_queue.get(timeout=1)
            if trigger == "WAKE":
                response_text = "Hello, how can I help you?"
                asyncio.run(speak_text(response_text))
                command = recognize_speech()

                if command:
                    command_queue.put(command)

                    if "send message" in command:
                        threading.Thread(target=send_audio_message).start()
                        asyncio.run(speak_text("Sending your message."))

                    elif "stop tracking" in command:
                        stop_event.set()

                    elif "exit" in command:
                        asyncio.run(speak_text("Goodbye!"))
                        stop_event.set()

                    else:
                        conversation_history.append({"role": "user", "parts": [command]})
                        response = model.generate_content(conversation_history[-5:])
                        reply = response.text
                        print("Gemini:", reply)
                        asyncio.run(speak_text(reply))

                        # Start face tracking if needed
                        if not face_tracking_active:
                            threading.Thread(target=face_tracking_thread_function).start()

            elif trigger == "FACE_DETECTED":
                asyncio.run(speak_text("I see a face. Let me identify who it is."))
                threading.Thread(target=user_identifier_thread_function).start()

        except queue.Empty:
            continue

if __name__ == "__main__":
    main()

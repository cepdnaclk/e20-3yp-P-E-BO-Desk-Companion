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
        time.sleep(0.25)
    pygame.mixer.music.stop()
    pygame.mixer.music.unload()  # Unload before deleting
    os.remove(filename)  # Safe to delete now

def listen_continuously(stop_event, wake_words=None):
    """
    Continuously listen for the wake word and put commands in the queue.
    This function runs in its own thread.
    """
    if wake_words is None:
        wake_words = ["hey bebo", "hey pebo", "bebo", "pebo"]
    print("Listening for wake word...")
    
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
    
    while not stop_event.is_set():
        try:
            with mic as source:
                print("Listening for wake word...")
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=5)
            
            try:
                text = recognizer.recognize_google(audio).lower()
                print(f"Heard: {text}")
                
                # Check for wake word
                if wake_word in text:
                    command_queue.put(("WAKE", None))
                    
                    # After wake word detected, listen for a command
                    with mic as source:
                        print("Wake word detected! Listening for command...")
                        command_audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                    try:
                        command = recognizer.recognize_google(command_audio).lower()
                        print(f"Command: {command}")
                        command_queue.put(("COMMAND", command))
                    except sr.UnknownValueError:
                        print("Couldn't understand command.")
                        command_queue.put(("ERROR", "command_not_understood"))
                    except sr.RequestError:
                        print("Google Speech Recognition service unavailable")
                
            except sr.UnknownValueError:
                # No speech detected, continue listening
                pass
            except sr.RequestError:
                print("Google Speech Recognition service unavailable")
                time.sleep(2)  # Wait before retrying
                
        except Exception as e:
            print(f"Error in listen_continuously: {e}")
            time.sleep(1)  # Prevent tight loop in case of repeated errors

def face_tracking_thread_function(stop_event):
    """Run face tracking in a separate thread and detect when a face is found."""
    global face_tracking_active, face_detected
    
    print("Starting face tracking thread...")
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

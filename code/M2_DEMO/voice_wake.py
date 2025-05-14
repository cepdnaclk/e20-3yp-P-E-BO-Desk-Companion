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

# Initialize pygame for audio playback
pygame.mixer.init()

# Set up Google Gemini API key
GOOGLE_API_KEY = "AIzaSyDjx04eYTq-09j7kzd24NeZfwYZ7eu3w9Q"
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize the Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")

# Conversation history for context
conversation_history = []

# Initialize speech recognizer
recognizer = sr.Recognizer()
mic = sr.Microphone()

# Communication queue between threads
command_queue = queue.Queue()
response_queue = queue.Queue()

# Set paths to the scripts
FACE_TRACKING_SCRIPT = "face_tracking.py"
USER_IDENTIFIER_SCRIPT = "user_identifier.py"
INTER_DEVICE_COMM_SCRIPT = "inter_device_communication_send_audio.py"

# Global state flags
face_tracking_active = False
face_detected = False

async def speak_text(text):
    """Convert text to speech using Edge TTS and play it."""
    voice = "en-US-AriaNeural"  # Change voice if needed (e.g., "en-GB-RyanNeural")
    filename = "response.mp3"
    
    tts = edge_tts.Communicate(text, voice)
    await tts.save(filename)
    pygame.mixer.music.load(filename)
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
        # Use Popen instead of run to be able to monitor output in real-time
        process = subprocess.Popen(
            ["python3", FACE_TRACKING_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor the output of the face tracking script for face detection
        while not stop_event.is_set() and process.poll() is None:
            output = process.stdout.readline().strip()
            if output:
                print(f"Face tracking: {output}")
                
                # Check if a face was detected
                if "FaceMatches" in output or "face detected" in output.lower():
                    if not face_detected:
                        face_detected = True
                        # Signal to the main thread that a face was detected
                        command_queue.put(("FACE_DETECTED", None))
                
                # Check if face detection was lost
                if "No face detected" in output:
                    if face_detected:
                        face_detected = False
        
        # Make sure we terminate the process when stopping
        if process.poll() is None:
            process.terminate()
            
    except Exception as e:
        print(f"Error in face tracking thread: {e}")
    finally:
        face_tracking_active = False
        face_detected = False
        print("Face tracking thread ended")

def identify_user_thread():
    """Run the user identification script in a separate thread."""
    print("Identifying user...")
    try:
        # Run the user identifier script
        result = subprocess.run(
            ["python3", USER_IDENTIFIER_SCRIPT],
            capture_output=True,
            text=True,
            check=True
        )
        
        output = result.stdout
        print(f"User identification output: {output}")
        
        # Process the result to extract user information
        user_info = None
        match_found = False
        
        # Look for a match in the output
        if "Match:" in output:
            match_found = True
            # Extract user name (assuming format "Match: user_NAME.jpg with XX.XX% similarity")
            try:
                name_part = output.split("Match:")[1].split("with")[0].strip()
                if "user_" in name_part:
                    user_name = name_part.split("user_")[1].split(".jpg")[0]
                    user_info = {"name": user_name, "match": True}
                    
                    # Look for emotion data
                    if "Detected Emotion:" in output:
                        emotion = output.split("Detected Emotion:")[1].split("\n")[0].strip()
                        user_info["emotion"] = emotion
            except:
                user_info = {"match": True, "name": "unknown"}
        else:
            user_info = {"match": False}
            
        # Put the result in the queue for the main thread
        response_queue.put(("USER_INFO", user_info))
        
    except subprocess.CalledProcessError as e:
        print(f"User identification error: {e}")
        response_queue.put(("ERROR", "user_identification_failed"))
    except Exception as e:
        print(f"Unexpected error in user identification: {e}")
        response_queue.put(("ERROR", "unexpected_error"))

def send_message_thread(receiver_ip=None):
    """Run the message sending script in a separate thread."""
    print("Starting message sending process...")
    try:
        # If receiver_ip is provided, pass it to the script via environment variable
        env = os.environ.copy()
        if receiver_ip:
            env["RECEIVER_IP"] = receiver_ip
        
        subprocess.run(
            ["python3", INTER_DEVICE_COMM_SCRIPT],
            env=env,
            check=True
        )
        
        # Notify main thread that message was sent
        response_queue.put(("MESSAGE_SENT", None))
        
    except subprocess.CalledProcessError as e:
        print(f"Message sending error: {e}")
        response_queue.put(("ERROR", "message_send_failed"))
    except Exception as e:
        print(f"Unexpected error in message sending: {e}")
        response_queue.put(("ERROR", "unexpected_error"))
def process_command(command):
    """Process voice commands and trigger appropriate actions."""
    global face_tracking_active
    
    if command is None:
        return
    
    command = command.lower()
    
    if "send message" in command:
        # Default receiver IP (could be replaced with a lookup from a contacts list)
        receiver_ip = "192.168.1.100"  
        
        # Notify user
        asyncio.run(speak_text("Starting message recording. Please speak your message."))
        
        # Start message sending in a new thread
        thread = threading.Thread(target=send_message_thread, args=(receiver_ip,))
        thread.daemon = True
        thread.start()
        return True
        
    elif "stop tracking" in command or "stop following" in command:
        if face_tracking_active:
            # Will be handled in main loop to stop the tracking thread
            command_queue.put(("STOP_TRACKING", None))
            return True
        
    # For other commands, handle with Gemini AI
    conversation_history.append({"role": "user", "parts": ["Answer briefly with max two sentences: " + command]})
    
    # Generate response from Gemini
    response = model.generate_content(conversation_history, generation_config={"max_output_tokens": 50}) 
    ai_response = response.text
    
    # Print and speak Gemini's response
    print(f"Gemini: {ai_response}")
    asyncio.run(speak_text(ai_response))
    
    # Append AI response to conversation history
    conversation_history.append({"role": "model", "parts": [ai_response]})
    
    return False  # Not a special command

async def main():
    global face_tracking_active, face_detected
    
    print("PEBO Assistant is starting...")
    await speak_text("Hello, I am PEBO, your desk companion. I'm listening for commands.")
    
    # Create a stop event for the threads
    stop_event = threading.Event()
    
    # Start the continuous listening thread
    listen_thread = threading.Thread(target=listen_continuously, args=(stop_event,))
    listen_thread.daemon = True
    listen_thread.start()
    
    # Create variables for tracking threads
    face_tracking_thread = None
    
    try:
        while True:
            # Check for commands in the queue
            try:
                command_type, command_data = command_queue.get(timeout=0.5)
                
                if command_type == "WAKE":
                    await speak_text("I'm listening.")
                
                elif command_type == "COMMAND":
                    if command_data == "exit":
                        await speak_text("Goodbye!")
                        break
                    else:
                        process_command(command_data)
                
                elif command_type == "FACE_DETECTED" and face_tracking_active:
                    print("Face detected! Capturing image for identification...")
                    await speak_text("Face detected. Let me see who you are.")
                    
                    # Pause briefly to allow the camera to stabilize on the face
                    time.sleep(1)
                    
                    # Start user identification in a new thread
                    id_thread = threading.Thread(target=identify_user_thread)
                    id_thread.daemon = True
                    id_thread.start()
                
                elif command_type == "STOP_TRACKING":
                    if face_tracking_thread and face_tracking_thread.is_alive():
                        stop_event.set()
                        face_tracking_thread.join(timeout=2)
                        stop_event.clear()
                        await speak_text("Face tracking stopped.")
                        face_tracking_active = False
                
            except queue.Empty:
                # No commands in the queue
                pass
            
            # Check for responses
            try:
                response_type, response_data = response_queue.get_nowait()
                
                if response_type == "USER_INFO":
                    if response_data and response_data.get("match", False):
                        # User was recognized
                        user_name = response_data.get("name", "friend")
                        emotion = response_data.get("emotion", "neutral")
                        
                        # Customize greeting based on detected emotion
                        greeting = f"Hello {user_name}!"
                        if emotion == "HAPPY":
                            greeting += " You seem happy today!"
                        elif emotion == "SAD":
                            greeting += " Are you feeling okay today?"
                        
                        await speak_text(greeting)
                    else:
                        # New user
                        await speak_text("I don't recognize you yet. Nice to meet you!")
                
                elif response_type == "MESSAGE_SENT":
                    await speak_text("Your message has been sent.")
                
                elif response_type == "ERROR":
                    if response_data == "user_identification_failed":
                        await speak_text("I had trouble identifying you. Please try again later.")
                    elif response_data == "message_send_failed":
                        await speak_text("I couldn't send your message. Please try again.")
                
            except queue.Empty:
                # No responses in the queue
                pass
            
            # Handle wake word "hey pebo" to start face tracking
            if not face_tracking_active:
                try:
                    command_type, _ = command_queue.get_nowait()
                    if command_type == "WAKE":
                        await speak_text("Starting face tracking mode.")
                        
                        # Start face tracking in a new thread
                        face_tracking_active = True
                        face_detected = False
                        face_tracking_thread = threading.Thread(target=face_tracking_thread_function, args=(stop_event,))
                        face_tracking_thread.daemon = True
                        face_tracking_thread.start()
                except queue.Empty:
                    pass
                    
    except KeyboardInterrupt:
        print("Program interrupted by user")
    finally:
        # Clean up
        stop_event.set()
        if face_tracking_thread and face_tracking_thread.is_alive():
            face_tracking_thread.join(timeout=2)
        if listen_thread and listen_thread.is_alive():
            listen_thread.join(timeout=2)
        print("Cleanup complete")

if __name__ == "__main__":
    asyncio.run(main())

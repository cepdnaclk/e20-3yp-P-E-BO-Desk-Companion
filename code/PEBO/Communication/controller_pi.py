# controller_pi.py
import subprocess
import speech_recognition as sr
import time
import os
import signal

# Path to your sender script
SENDER_SCRIPT = "code/PEBO/Communication/sender.py"
process = None

def start_script(script_path):
    global process
    print(f"[STARTING] {script_path}")
    process = subprocess.Popen(["python", script_path])

def stop_script():
    global process
    if process and process.poll() is None:
        print("[STOPPING] Communication")
        process.terminate()
        process.wait()
        process = None

def listen_commands():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("[SYSTEM READY] Say 'send message' to start or 'end communication' to stop")
    while True:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source)
            print("[LISTENING] Speak a command...")
            try:
                audio = recognizer.listen(source, timeout=5)
                command = recognizer.recognize_google(audio).lower()
                print(f"[RECOGNIZED] Command: {command}")
                
                if "send message" in command:
                    if process is None:
                        start_script(SENDER_SCRIPT)
                    else:
                        print("[INFO] Communication already active.")
                elif "end communication" in command:
                    stop_script()
                elif "exit" in command:
                    stop_script()
                    print("[EXITING]")
                    break

            except sr.UnknownValueError:
                print("[ERROR] Could not understand audio.")
            except sr.RequestError as e:
                print(f"[ERROR] Recognition request failed: {e}")
            except sr.WaitTimeoutError:
                print("[ERROR] Listening timed out.")

if __name__ == "__main__":
    listen_commands()

import subprocess
import speech_recognition as sr
import signal
import time
import os

# Keep reference to subprocess
process = None

# Path to the audio node script (either sender or receiver, both now handle full duplex)
AUDIO_NODE_SCRIPT =  "code/PEBO/Communication/audio_node.py"  # Or use "receiver.py" depending on the device

def listen_command():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("[LISTENING] Speak a command...")
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=5)
        except sr.WaitTimeoutError:
            print("[TIMEOUT] No speech detected.")
            return ""
    try:
        command = r.recognize_google(audio).lower()
        print(f"[RECOGNIZED] Command: {command}")
        return command
    except sr.UnknownValueError:
        print("[ERROR] Could not understand audio.")
        return ""
    except sr.RequestError as e:
        print(f"[ERROR] Speech Recognition service error: {e}")
        return ""

def start_script(script_name):
    global process
    if process is None or process.poll() is not None:
        print(f"[STARTING] {script_name}")
        process = subprocess.Popen(["python", script_name])  # Use "python3" if needed
    else:
        print("[INFO] Communication is already running.")

def stop_script():
    global process
    if process and process.poll() is None:
        print("[STOPPING] Communication process...")
        process.send_signal(signal.SIGINT)
        time.sleep(1)
        if process.poll() is None:
            process.terminate()
        process = None
    else:
        print("[INFO] No active communication to stop.")

def main():
    print("[SYSTEM READY] Say 'send message' to start or 'end communication' to stop")
    while True:
        try:
            cmd = listen_command()
            if "send message" in cmd:
                start_script(AUDIO_NODE_SCRIPT)
            elif "end communication" in cmd:
                stop_script()
        except KeyboardInterrupt:
            stop_script()
            print("[EXIT] Controller stopped.")
            break

if __name__ == "__main__":
    main()

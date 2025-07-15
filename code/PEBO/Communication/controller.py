# controller.py
import speech_recognition as sr
from audio_node import AudioNode
import time

# Modify these IPs depending on the device
MY_IP = "192.168.124.94"         # This device's IP
OTHER_PEBO_IP = "192.168.124.182"  # The other device's IP

MY_LISTEN_PORT = 8889
OTHER_PEBO_PORT = 8888

audio_node = None

def listen_command():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("[COMMAND] Listening...")
        audio = r.listen(source, timeout=5, phrase_time_limit=5)
    try:
        command = r.recognize_google(audio).lower()
        print("[COMMAND] Recognized:", command)
        return command
    except sr.UnknownValueError:
        print("[COMMAND] Could not understand")
        return ""
    except sr.RequestError:
        print("[COMMAND] API unavailable")
        return ""

def main():
    global audio_node
    print("[SYSTEM] Say 'send message', 'answer', or 'end communication'")
    while True:
        try:
            cmd = listen_command()
            if "send message" in cmd or "answer" in cmd:
                if not audio_node:
                    audio_node = AudioNode(
                        listen_port=MY_LISTEN_PORT,
                        target_host=OTHER_PEBO_IP,
                        target_port=OTHER_PEBO_PORT
                    )
                    audio_node.start()
                else:
                    print("[INFO] Already in communication")
            elif "end communication" in cmd:
                if audio_node:
                    audio_node.stop()
                    audio_node = None
                else:
                    print("[INFO] No active communication to stop")
        except KeyboardInterrupt:
            if audio_node:
                audio_node.stop()
            break

if __name__ == "__main__":
    main()

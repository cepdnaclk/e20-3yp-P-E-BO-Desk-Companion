import speech_recognition as sr
import subprocess
import os
from audio_controller import AudioCommunicationController, NodeType

# Set node type: LAPTOP or PI
NODE_TYPE = NodeType.LAPTOP  # Change to NodeType.PI on Raspberry Pi

controller = AudioCommunicationController(
    node_type=NODE_TYPE,
    laptop_ip='192.168.124.94',     # Set correct laptop IP
    pi_ip='192.168.124.182',        # Set correct Pi IP
    laptop_port=8889,
    pi_port=8888
)

def listen_and_recognize(recognizer, mic):
    with mic as source:
        print("[LISTENING] Speak a command...")
        audio = recognizer.listen(source, phrase_time_limit=5)

    try:
        command = recognizer.recognize_google(audio).lower()
        print(f"[RECOGNIZED] Command: {command}")
        return command
    except sr.UnknownValueError:
        print("[ERROR] Could not understand audio.")
        return None
    except sr.RequestError as e:
        print(f"[ERROR] Speech recognition failed: {e}")
        return None

def main_loop():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("[SYSTEM READY] Say 'send message' to start or 'end communication' to stop")

    while True:
        command = listen_and_recognize(recognizer, mic)

        if not command:
            continue

        if "send message" in command:
            if controller.running:
                print("[INFO] Communication already active.")
            else:
                controller.start_communication()

        elif "end communication" in command or "stop message" in command:
            if controller.running:
                controller.stop_communication()
            else:
                print("[INFO] No communication to stop.")

        elif "microphone" in command:
            controller.toggle_microphone()

        elif "speaker" in command:
            controller.toggle_speaker()

        elif "status" in command:
            controller.print_status()

        elif "exit" in command or "quit" in command:
            print("[EXITING]")
            controller.stop_communication()
            break

if __name__ == "__main__":
    main_loop()

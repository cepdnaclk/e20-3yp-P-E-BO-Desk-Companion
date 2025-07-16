import speech_recognition as sr
from sender import AudioNode
import threading
import time

LAPTOP_IP = "192.168.124.182"  # Replace with Device 2 IP

class VoiceControlledAudio:
    def __init__(self):
        self.node = None
        self.node_thread = None
        self.is_running = False

    def start_audio_node(self):
        if not self.is_running:
            print("[SYSTEM] Starting audio communication...")
            self.node = AudioNode(
                listen_port=8888,
                target_host=LAPTOP_IP,
                target_port=8889
            )
            self.node_thread = threading.Thread(target=self.node.start)
            self.node_thread.start()
            self.is_running = True

    def stop_audio_node(self):
        if self.node and self.is_running:
            print("[SYSTEM] Ending communication...")
            self.node.running = False
            self.is_running = False

    def listen_for_commands(self):
        recognizer = sr.Recognizer()
        mic = sr.Microphone()
        print("[VOICE] Say 'send message' to start. Say 'end communication' to stop.")

        while True:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source)
                print("[VOICE] Listening...")
                audio = recognizer.listen(source)

            try:
                command = recognizer.recognize_google(audio).lower()
                print(f"[VOICE] Heard: {command}")

                if "send message" in command and not self.is_running:
                    self.start_audio_node()

                elif "end communication" in command and self.is_running:
                    self.stop_audio_node()

            except sr.UnknownValueError:
                print("[VOICE] Could not understand. Try again.")
            except Exception as e:
                print(f"[ERROR] {e}")
            time.sleep(1)

if __name__ == "__main__":
    controller = VoiceControlledAudio()
    controller.listen_for_commands()

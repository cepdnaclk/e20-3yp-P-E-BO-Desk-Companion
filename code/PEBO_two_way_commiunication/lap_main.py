import speech_recognition as sr
from sender_node import AudioNode
import threading
import time
import socket
import subprocess

# === Configuration ===
IS_PI = False

MY_TRIGGER_PORT = 8890
PEER_TRIGGER_PORT = 8891
PEER_IP = "192.168.124.94"  # Pi IP

class VoiceControlledAudio:
    def __init__(self):
        self.node = None
        self.node_thread = None
        self.is_running = False

        self.trigger_thread = threading.Thread(target=self.wait_for_trigger)
        self.trigger_thread.daemon = True
        self.trigger_thread.start()

    def start_audio_node(self):
        if not self.is_running:
            print("[SYSTEM] Starting audio communication...")
            self.node = AudioNode(
                listen_port=8889,
                target_host=PEER_IP,
                target_port=8888
            )
            self.node_thread = threading.Thread(target=self.node.start)
            self.node_thread.daemon = True
            self.node_thread.start()
            self.is_running = True

    def stop_audio_node(self):
        if self.node and self.is_running:
            print("[SYSTEM] Ending communication...")
            self.node.running = False
            self.is_running = False

    def send_trigger_to_peer(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((PEER_IP, PEER_TRIGGER_PORT))
                s.sendall(b'start')
                print(f"[SYSTEM] Trigger signal sent to {PEER_IP}:{PEER_TRIGGER_PORT}")
        except Exception as e:
            print(f"[ERROR] Failed to send trigger signal: {e}")

    def wait_for_trigger(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('0.0.0.0', MY_TRIGGER_PORT))
            s.listen(1)
            print(f"[TRIGGER] Listening on port {MY_TRIGGER_PORT} for start signal...")
            while True:
                conn, addr = s.accept()
                with conn:
                    print(f"[TRIGGER] Connection from {addr}")
                    data = conn.recv(1024)
                    if data == b'start':
                        print("[TRIGGER] Start signal received. Launching receiver...")
                        subprocess.Popen(['python', 'receiver.py'])

    def listen_for_commands(self):
        recognizer = sr.Recognizer()
        mic = sr.Microphone()
        print("[VOICE] Say 'send message' to start or 'end communication' to stop.")
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
                    self.send_trigger_to_peer()

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

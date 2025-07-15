import subprocess
import threading
import time
import speech_recognition as sr
import os
import signal

class AudioControl:
    def __init__(self, role='pi'):  # 'pi' or 'laptop'
        self.role = role
        self.proc = None
        self.running = False

    def recognize_command(self, timeout=5):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("Listening for command...")
            recognizer.adjust_for_ambient_noise(source)
            try:
                audio = recognizer.listen(source, timeout=timeout)
                command = recognizer.recognize_google(audio).lower()
                print(f"Recognized: {command}")
                return command
            except Exception as e:
                print(f"Error: {e}")
                return ""

    def start_node(self):
        if self.running:
            print("Already running.")
            return

        file = "sender.py" if self.role == 'pi' else "receiver.py" # Adjust based on your file names
        print(f"Starting {file}...")

        # Start the subprocess and keep a reference
        self.proc = subprocess.Popen(["python3", file])
        self.running = True

    def stop_node(self):
        if self.proc:
            print("Stopping audio node...")
            os.kill(self.proc.pid, signal.SIGINT)
            self.proc.wait()
            self.proc = None
            self.running = False
        else:
            print("Audio node not running.")

    def run_control_loop(self):
        print("Voice-controlled audio comms. Say 'start communication' or 'stop communication'.")

        try:
            while True:
                command = self.recognize_command()
                if "start communication" in command:
                    self.start_node()
                elif "stop communication" in command:
                    self.stop_node()
                elif "exit" in command:
                    self.stop_node()
                    print("Exiting control...")
                    break
                else:
                    print("Say 'start communication', 'stop communication', or 'exit'.")
        except KeyboardInterrupt:
            self.stop_node()

if __name__ == "__main__":
    # Set 'pi' or 'laptop' depending on the device
    controller = AudioControl(role='pi')  # Change to 'laptop' for laptop
    controller.run_control_loop()

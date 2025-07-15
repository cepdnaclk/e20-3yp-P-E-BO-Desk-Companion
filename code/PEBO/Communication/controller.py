# pebo_controller.py - Main controller for Pebo communication system
import speech_recognition as sr
import pyttsx3
import socket
import threading
import time
import subprocess
import sys
import os
import signal
from enum import Enum

class PeboState(Enum):
    IDLE = "idle"
    CALLING = "calling"
    RINGING = "ringing"
    CONNECTED = "connected"

class PeboController:
    def __init__(self, device_id, partner_ip, my_ip="0.0.0.0"):
        self.device_id = device_id  # "pebo1" or "pebo2"
        self.partner_ip = partner_ip
        self.my_ip = my_ip
        self.state = PeboState.IDLE
        self.audio_process = None
        self.ring_thread = None
        self.running = True
        
        # Audio settings
        self.ring_port = 9999
        self.control_port = 9998
        
        # Initialize TTS and voice recognition
        self.tts = pyttsx3.init()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Setup voice recognition
        self.setup_voice_recognition()
        
        # Start control listener
        self.start_control_listener()
        
    def setup_voice_recognition(self):
        """Setup voice recognition with ambient noise adjustment"""
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            
    def speak(self, text):
        """Text to speech output"""
        print(f"[{self.device_id}] Speaking: {text}")
        self.tts.say(text)
        self.tts.runAndWait()
        
    def listen_for_command(self, timeout=5):
        """Listen for voice commands"""
        try:
            with self.microphone as source:
                print(f"[{self.device_id}] Listening for command...")
                audio = self.recognizer.listen(source, timeout=timeout)
                
            command = self.recognizer.recognize_google(audio).lower()
            print(f"[{self.device_id}] Heard: {command}")
            return command
            
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"[{self.device_id}] Speech recognition error: {e}")
            return None
            
    def send_ring_signal(self):
        """Send ring signal to partner device"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.partner_ip, self.ring_port))
            sock.send(b"RING")
            sock.close()
            print(f"[{self.device_id}] Ring signal sent to {self.partner_ip}")
        except Exception as e:
            print(f"[{self.device_id}] Failed to send ring signal: {e}")
            
    def send_control_signal(self, command):
        """Send control signal to partner device"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.partner_ip, self.control_port))
            sock.send(command.encode())
            sock.close()
            print(f"[{self.device_id}] Control signal sent: {command}")
        except Exception as e:
            print(f"[{self.device_id}] Failed to send control signal: {e}")
            
    def start_control_listener(self):
        """Start listening for control signals from partner"""
        def control_listener():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((self.my_ip, self.control_port))
                sock.listen(1)
                sock.settimeout(1)
                
                while self.running:
                    try:
                        conn, addr = sock.accept()
                        data = conn.recv(1024).decode()
                        conn.close()
                        
                        if data == "END_CALL":
                            self.handle_end_call()
                            
                    except socket.timeout:
                        continue
                    except Exception as e:
                        if self.running:
                            print(f"[{self.device_id}] Control listener error: {e}")
                            
            except Exception as e:
                print(f"[{self.device_id}] Control listener setup error: {e}")
                
        thread = threading.Thread(target=control_listener)
        thread.daemon = True
        thread.start()
        
    def start_ring_listener(self):
        """Start listening for ring signals"""
        def ring_listener():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((self.my_ip, self.ring_port))
                sock.listen(1)
                sock.settimeout(1)
                
                while self.running:
                    try:
                        conn, addr = sock.accept()
                        data = conn.recv(1024)
                        conn.close()
                        
                        if data == b"RING":
                            self.handle_incoming_ring()
                            
                    except socket.timeout:
                        continue
                    except Exception as e:
                        if self.running:
                            print(f"[{self.device_id}] Ring listener error: {e}")
                            
            except Exception as e:
                print(f"[{self.device_id}] Ring listener setup error: {e}")
                
        self.ring_thread = threading.Thread(target=ring_listener)
        self.ring_thread.daemon = True
        self.ring_thread.start()
        
    def handle_incoming_ring(self):
        """Handle incoming ring from partner"""
        if self.state == PeboState.IDLE:
            self.state = PeboState.RINGING
            self.speak("Incoming call! Say 'answer' to accept.")
            print(f"[{self.device_id}] State changed to RINGING")
            
    def start_audio_communication(self):
        """Start the audio communication process"""
        try:
            if self.device_id == "pebo1":
                # Pebo1 uses sender code
                cmd = [sys.executable, "pi_audio_node.py"]
            else:
                # Pebo2 uses receiver code
                cmd = [sys.executable, "laptop_audio_node.py"]
                
            self.audio_process = subprocess.Popen(cmd)
            print(f"[{self.device_id}] Audio communication started")
            
        except Exception as e:
            print(f"[{self.device_id}] Failed to start audio communication: {e}")
            
    def stop_audio_communication(self):
        """Stop the audio communication process"""
        if self.audio_process:
            try:
                self.audio_process.terminate()
                self.audio_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.audio_process.kill()
            except Exception as e:
                print(f"[{self.device_id}] Error stopping audio process: {e}")
            finally:
                self.audio_process = None
                
    def handle_send_message_command(self):
        """Handle 'send message' command from pebo1"""
        if self.device_id != "pebo1":
            return
            
        if self.state == PeboState.IDLE:
            self.state = PeboState.CALLING
            self.speak("Calling pebo2...")
            self.send_ring_signal()
            
            # Wait for answer with timeout
            start_time = time.time()
            while self.state == PeboState.CALLING and time.time() - start_time < 30:
                time.sleep(0.5)
                
            if self.state == PeboState.CALLING:
                self.speak("No answer. Call ended.")
                self.state = PeboState.IDLE
                
    def handle_answer_command(self):
        """Handle 'answer' command from pebo2"""
        if self.device_id != "pebo2":
            return
            
        if self.state == PeboState.RINGING:
            self.state = PeboState.CONNECTED
            self.speak("Call answered. You can now talk.")
            self.start_audio_communication()
            
    def handle_end_call(self):
        """Handle call end from either device"""
        if self.state == PeboState.CONNECTED:
            self.speak("Call ended.")
            self.stop_audio_communication()
            
        self.state = PeboState.IDLE
        
    def handle_end_communication_command(self):
        """Handle 'end communication' command"""
        if self.state == PeboState.CONNECTED:
            self.send_control_signal("END_CALL")
            self.handle_end_call()
            
    def process_voice_command(self, command):
        """Process recognized voice commands"""
        if not command:
            return
            
        if "send message" in command:
            self.handle_send_message_command()
            
        elif "answer" in command:
            self.handle_answer_command()
            
        elif "end communication" in command or "end call" in command:
            self.handle_end_communication_command()
            
    def run(self):
        """Main loop for the controller"""
        self.speak(f"Pebo {self.device_id} controller started.")
        self.start_ring_listener()
        
        while self.running:
            try:
                command = self.listen_for_command(timeout=2)
                if command:
                    self.process_voice_command(command)
                    
            except KeyboardInterrupt:
                print(f"\n[{self.device_id}] Shutting down...")
                self.running = False
                break
            except Exception as e:
                print(f"[{self.device_id}] Error in main loop: {e}")
                
        # Cleanup
        self.stop_audio_communication()
        self.tts.stop()


def main():
    """Main function to start the appropriate Pebo controller"""
    if len(sys.argv) != 3:
        print("Usage: python pebo_controller.py <device_id> <partner_ip>")
        print("Example: python pebo_controller.py pebo1 192.168.124.182")
        sys.exit(1)
        
    device_id = sys.argv[1]
    partner_ip = sys.argv[2]
    
    if device_id not in ["pebo1", "pebo2"]:
        print("Device ID must be 'pebo1' or 'pebo2'")
        sys.exit(1)
        
    controller = PeboController(device_id, partner_ip)
    controller.run()


if __name__ == "__main__":
    main()
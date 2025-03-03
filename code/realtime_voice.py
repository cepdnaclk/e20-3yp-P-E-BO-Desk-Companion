import paho.mqtt.client as mqtt
import pyaudio
import threading
import time
import json
import argparse
import socket
import os
import numpy as np
from collections import deque

# Audio settings for 5-second chunks
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100  # CD quality sample rate
RECORD_SECONDS = 5  # Record in 5-second chunks
FRAMES_PER_CHUNK = int(RATE / CHUNK * RECORD_SECONDS)
SILENCE_THRESHOLD = 50  # Lowered threshold for silence detection (was 300)

# MQTT settings
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
QOS_LEVEL = 1

class LaptopVoiceCall:
    def __init__(self, user_id):
        self.user_id = user_id
        self.other_user = None
        self.call_active = False
        self.audio = pyaudio.PyAudio()
        self.stream_thread = None
        self.audio_buffer = deque(maxlen=10)  # Playback buffer for 5-second chunks
        self.playing = False
        self.silence_detection_enabled = True  # New flag to control silence detection
        
        # Initialize MQTT client
        client_id = f"laptop_{user_id}_{int(time.time())}"
        self.client = mqtt.Client(client_id=client_id, clean_session=True)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        print(f"Initializing voice call system as {client_id}...")
        
        # Connect to MQTT broker
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            print(f"Laptop {self.user_id} connected to MQTT broker")
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected to MQTT broker successfully")
            self.client.subscribe(f"laptop/control/{self.user_id}", qos=QOS_LEVEL)
            self.client.subscribe(f"laptop/voice/{self.user_id}", qos=QOS_LEVEL)
        else:
            print(f"Failed to connect to MQTT broker with code {rc}")
    
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        
        if topic.startswith("laptop/control/"):
            self.handle_control(msg.payload.decode())
        elif topic.startswith("laptop/voice/"):
            self.handle_voice(msg.payload)
    
    def handle_control(self, payload):
        try:
            data = json.loads(payload)
            action = data.get("action")
            caller = data.get("caller")
            
            if action == "call_request" and not self.call_active:
                print(f"\n\nIncoming call from {caller}. Accept? (y/n)")
                self.other_user = caller
                
            elif action == "call_accept" and caller == self.other_user:
                print(f"Call accepted by {caller}")
                self.call_active = True
                self.stream_thread = threading.Thread(target=self.record_and_send_chunks)
                self.stream_thread.daemon = True
                self.stream_thread.start()
                threading.Thread(target=self.continuous_audio_playback, daemon=True).start()
                
            elif action == "call_end":
                if self.call_active or self.other_user == caller:
                    print(f"Call ended by {caller}")
                    self.call_active = False
                    self.other_user = None
        except Exception as e:
            print(f"Error handling control message: {e}")
    
    def handle_voice(self, payload):
        if self.call_active:
            self.audio_buffer.append(payload)
    
    def continuous_audio_playback(self):
        print("Audio playback thread started")
        self.playing = True
        
        output_stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            frames_per_buffer=CHUNK
        )
        
        try:
            while self.call_active:
                if len(self.audio_buffer) > 0:
                    audio_data = self.audio_buffer.popleft()
                    output_stream.write(audio_data)
                else:
                    time.sleep(0.1)  # Longer sleep since we're dealing with larger chunks
                    
        except Exception as e:
            print(f"Audio playback thread error: {e}")
        finally:
            output_stream.stop_stream()
            output_stream.close()
            self.playing = False
            print("Audio playback thread stopped")
    
    def is_silent(self, audio_data, threshold=None):
        if not self.silence_detection_enabled:
            return False  # Always return not silent when detection is disabled
            
        if threshold is None:
            threshold = SILENCE_THRESHOLD
        
        try:
            data = np.frombuffer(audio_data, dtype=np.int16)
            amplitude = np.abs(data).mean()
            is_silent = amplitude < threshold
            if is_silent:
                print(f"Detected silence (amplitude: {amplitude}, threshold: {threshold})")
            return is_silent
        except Exception as e:
            print(f"Error in silence detection: {e}")
            return False
    
    def initiate_call(self, recipient):
        if self.call_active:
            print("Already in a call!")
            return False
            
        self.other_user = recipient
        
        control_data = {
            "action": "call_request",
            "caller": self.user_id,
            "timestamp": int(time.time())
        }
        
        self.client.publish(f"laptop/control/{recipient}", json.dumps(control_data), qos=QOS_LEVEL)
        print(f"Calling {recipient}...")
        return True
    
    def accept_call(self):
        if not self.other_user:
            print("No incoming call to accept!")
            return False
            
        control_data = {
            "action": "call_accept",
            "caller": self.user_id,
            "timestamp": int(time.time())
        }
        
        self.client.publish(f"laptop/control/{self.other_user}", json.dumps(control_data), qos=QOS_LEVEL)
        self.call_active = True
        self.stream_thread = threading.Thread(target=self.record_and_send_chunks)
        self.stream_thread.daemon = True
        self.stream_thread.start()
        threading.Thread(target=self.continuous_audio_playback, daemon=True).start()
        
        print(f"Call with {self.other_user} started!")
        return True
    
    def end_call(self):
        if not self.call_active and not self.other_user:
            print("No active call to end!")
            return False
            
        control_data = {
            "action": "call_end",
            "caller": self.user_id,
            "timestamp": int(time.time())
        }
        
        if self.other_user:
            self.client.publish(f"laptop/control/{self.other_user}", json.dumps(control_data), qos=QOS_LEVEL)
        
        self.call_active = False
        if self.other_user:
            print(f"Call with {self.other_user} ended!")
        self.other_user = None
        return True
    
    def record_and_send_chunks(self):
        print("\nVoice recording started. Recording in 5-second chunks! (Call in progress)")
        print("------------------------------------------------------")
        
        stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        while self.call_active:
            try:
                print("Recording 5-second chunk...")
                frames = []
                for i in range(0, FRAMES_PER_CHUNK):
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    frames.append(data)
                
                # Combine all frames into one audio chunk
                audio_chunk = b''.join(frames)
                
                # Check if the chunk is not silent or if silence detection is disabled
                if not self.is_silent(audio_chunk):
                    print(f"Sending 5-second audio chunk ({len(audio_chunk)/1024:.1f} KB)")
                    result = self.client.publish(f"laptop/voice/{self.other_user}", audio_chunk, qos=QOS_LEVEL)
                    if not result.is_published():
                        result.wait_for_publish(timeout=1.0)
                else:
                    print("Chunk was mostly silent, not sending")
                    
            except Exception as e:
                print(f"Error in recording: {e}")
                time.sleep(0.5)
        
        stream.stop_stream()
        stream.close()
        print("Voice recording ended.")
    
    def interactive_console(self):
        print(f"=== Laptop Voice Call System ({self.user_id}) ===")
        print("Commands:")
        print("  call <user_id>   - Start a call with another laptop")
        print("  accept           - Accept incoming call")
        print("  end              - End current call")
        print("  status           - Show current status")
        print("  silence <on/off> - Enable/disable silence detection")
        print("  threshold <value> - Set silence detection threshold (default: 50)")
        print("  exit             - Exit application")
        
        while True:
            try:
                command = input("\nEnter command: ").strip().lower()
                
                if command.startswith("call "):
                    recipient = command.split(" ")[1]
                    self.initiate_call(recipient)
                elif command == "accept":
                    self.accept_call()
                elif command == "end":
                    self.end_call()
                elif command == "status":
                    if self.call_active:
                        print(f"In call with {self.other_user}")
                    elif self.other_user:
                        print(f"Call pending with {self.other_user}")
                    else:
                        print("Not in a call")
                    print(f"Silence detection: {'Enabled' if self.silence_detection_enabled else 'Disabled'}")
                    print(f"Silence threshold: {SILENCE_THRESHOLD}")
                elif command.startswith("silence "):
                    option = command.split(" ")[1]
                    if option == "on":
                        self.silence_detection_enabled = True
                        print("Silence detection enabled")
                    elif option == "off":
                        self.silence_detection_enabled = False
                        print("Silence detection disabled")
                    else:
                        print("Invalid option. Use 'on' or 'off'")
                elif command.startswith("threshold "):
                    try:
                        value = int(command.split(" ")[1])
                        global SILENCE_THRESHOLD
                        SILENCE_THRESHOLD = value
                        print(f"Silence threshold set to {value}")
                    except:
                        print("Invalid value. Please enter a number.")
                elif command == "exit":
                    if self.call_active:
                        self.end_call()
                    print("Disconnecting from MQTT broker...")
                    self.client.loop_stop()
                    self.client.disconnect()
                    break
                else:
                    print("Unknown command")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
        
        print("Exiting Laptop Voice Call System")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Laptop Voice Call System')
    parser.add_argument('user_id', type=str, help='Unique user ID (e.g., alice, bob)')
    args = parser.parse_args()
    
    laptop_call = LaptopVoiceCall(args.user_id)
    laptop_call.interactive_console()
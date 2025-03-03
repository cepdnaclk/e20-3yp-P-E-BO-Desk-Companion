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

# Enhanced audio settings for real-time communication
CHUNK = 512  # Smaller chunk size for lower latency
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100  # CD quality sample rate
SILENCE_THRESHOLD = 300  # Threshold for silence detection

# MQTT settings
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
QOS_LEVEL = 1

class LaptopVoiceCall:
    def _init_(self, user_id):
        self.user_id = user_id
        self.other_user = None
        self.call_active = False
        self.audio = pyaudio.PyAudio()
        self.stream_thread = None
        self.audio_buffer = deque(maxlen=20)  # Playback buffer
        self.playing = False
        
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
                self.stream_thread = threading.Thread(target=self.stream_voice)
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
                    time.sleep(0.01)
                    
        except Exception as e:
            print(f"Audio playback thread error: {e}")
        finally:
            output_stream.stop_stream()
            output_stream.close()
            self.playing = False
            print("Audio playback thread stopped")
    
    def is_silent(self, audio_data, threshold=None):
        if threshold is None:
            threshold = SILENCE_THRESHOLD
        
        try:
            data = np.frombuffer(audio_data, dtype=np.int16)
            amplitude = np.abs(data).mean()
            return amplitude < threshold
        except:
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
        self.stream_thread = threading.Thread(target=self.stream_voice)
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
    
    def stream_voice(self):
        print("\nVoice streaming started. Speak now! (Call in progress)")
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
                audio_data = stream.read(CHUNK, exception_on_overflow=False)
                if not self.is_silent(audio_data):
                    result = self.client.publish(f"laptop/voice/{self.other_user}", audio_data, qos=QOS_LEVEL)
                    if not result.is_published():
                        result.wait_for_publish(timeout=0.1)
            except Exception as e:
                print(f"Error in voice streaming: {e}")
                time.sleep(0.01)
        
        stream.stop_stream()
        stream.close()
        print("Voice streaming ended.")
    
    def interactive_console(self):
        print(f"=== Laptop Voice Call System ({self.user_id}) ===")
        print("Commands:")
        print("  call <user_id>   - Start a call with another laptop")
        print("  accept           - Accept incoming call")
        print("  end              - End current call")
        print("  status           - Show current status")
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

if __name__ == "_main_":
    parser = argparse.ArgumentParser(description='Laptop Voice Call System')
    parser.add_argument('user_id', type=str, help='Unique user ID (e.g., alice, bob)')
    args = parser.parse_args()
    
    laptop_call = LaptopVoiceCall(args.user_id)
    laptop_call.interactive_console()
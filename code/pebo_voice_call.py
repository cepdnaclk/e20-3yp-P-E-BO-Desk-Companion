# pebo_voice_call.py
import paho.mqtt.client as mqtt
import base64
import json
import pyaudio
import wave
import threading
import time
import os
import argparse

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 1  # Short chunks for real-time communication

# MQTT settings
MQTT_BROKER = "broker.emqx.io"  # Public MQTT broker
MQTT_PORT = 1883

class PeboVoiceCall:
    def __init__(self, device_id):
        self.device_id = device_id
        self.other_device = None
        self.call_active = False
        self.audio = pyaudio.PyAudio()
        
        # Initialize MQTT client
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        # Connect to MQTT broker
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            print(f"PEBO {self.device_id} connected to MQTT broker")
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
    
    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected with result code {rc}")
        # Subscribe to control channel and voice channel
        self.client.subscribe(f"pebo/control/{self.device_id}")
        self.client.subscribe(f"pebo/voice/{self.device_id}")
    
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        
        if topic == f"pebo/control/{self.device_id}":
            self.handle_control(msg.payload.decode())
        elif topic == f"pebo/voice/{self.device_id}":
            self.handle_voice(msg.payload)
    
    def handle_control(self, payload):
        try:
            data = json.loads(payload)
            action = data.get("action")
            caller = data.get("caller")
            
            if action == "call_request" and not self.call_active:
                print(f"\nIncoming call from {caller}. Accept? (y/n)")
                self.other_device = caller
                
            elif action == "call_accept" and caller == self.other_device:
                print(f"Call accepted by {caller}")
                self.call_active = True
                # Start voice streaming
                threading.Thread(target=self.stream_voice).start()
                
            elif action == "call_end":
                if self.call_active:
                    print(f"Call ended by {caller}")
                    self.call_active = False
                    self.other_device = None
        except Exception as e:
            print(f"Error handling control message: {e}")
    
    def handle_voice(self, payload):
        if not self.call_active:
            return
            
        try:
            # Save audio data to temp file
            temp_file = f"temp_audio_{self.device_id}.wav"
            
            with open(temp_file, "wb") as f:
                f.write(payload)
            
            # Play the audio
            self.play_audio(temp_file)
        except Exception as e:
            print(f"Error handling voice data: {e}")
    
    def initiate_call(self, recipient):
        if self.call_active:
            print("Already in a call!")
            return False
            
        self.other_device = recipient
        
        # Send call request
        control_data = {
            "action": "call_request",
            "caller": self.device_id,
            "timestamp": int(time.time())
        }
        
        self.client.publish(f"pebo/control/{recipient}", json.dumps(control_data))
        print(f"Calling {recipient}...")
        return True
    
    def accept_call(self):
        if not self.other_device:
            print("No incoming call to accept!")
            return False
            
        # Send acceptance
        control_data = {
            "action": "call_accept",
            "caller": self.device_id,
            "timestamp": int(time.time())
        }
        
        self.client.publish(f"pebo/control/{self.other_device}", json.dumps(control_data))
        self.call_active = True
        
        # Start voice streaming
        threading.Thread(target=self.stream_voice).start()
        print(f"Call with {self.other_device} started!")
        return True
    
    def end_call(self):
        if not self.call_active:
            print("No active call to end!")
            return False
            
        # Send end call signal
        control_data = {
            "action": "call_end",
            "caller": self.device_id,
            "timestamp": int(time.time())
        }
        
        self.client.publish(f"pebo/control/{self.other_device}", json.dumps(control_data))
        self.call_active = False
        print(f"Call with {self.other_device} ended!")
        self.other_device = None
        return True
    
    def record_audio(self, duration=1):
        stream = self.audio.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK)
        
        frames = []
        
        for i in range(0, int(RATE / CHUNK * duration)):
            data = stream.read(CHUNK)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        
        # Save to temp file
        temp_file = f"temp_recording_{self.device_id}.wav"
        wf = wave.open(temp_file, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        return temp_file
    
    def play_audio(self, filename):
        try:
            wf = wave.open(filename, 'rb')
            stream = self.audio.open(format=self.audio.get_format_from_width(wf.getsampwidth()),
                                channels=wf.getnchannels(),
                                rate=wf.getframerate(),
                                output=True)
            
            data = wf.readframes(CHUNK)
            while data and self.call_active:
                stream.write(data)
                data = wf.readframes(CHUNK)
            
            stream.stop_stream()
            stream.close()
        except Exception as e:
            print(f"Error playing audio: {e}")
    
    def stream_voice(self):
        print("Voice streaming started. Speak now!")
        
        while self.call_active:
            try:
                # Record a chunk of audio
                audio_file = self.record_audio(RECORD_SECONDS)
                
                # Read the recorded data
                with open(audio_file, "rb") as f:
                    audio_data = f.read()
                
                # Send to the other device
                self.client.publish(f"pebo/voice/{self.other_device}", audio_data)
                
                # Slight delay to prevent overwhelming the broker
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error in voice streaming: {e}")
                break
        
        print("Voice streaming ended.")
    
    def interactive_console(self):
        print(f"=== PEBO Voice Call System ({self.device_id}) ===")
        print("Commands:")
        print("  call <pebo_id> - Start a call with another PEBO")
        print("  accept         - Accept incoming call")
        print("  end            - End current call")
        print("  exit           - Exit application")
        
        while True:
            try:
                command = input("\nEnter command: ").strip()
                
                if command.startswith("call "):
                    recipient = command.split(" ")[1]
                    self.initiate_call(recipient)
                    
                elif command == "accept":
                    self.accept_call()
                    
                elif command == "end":
                    self.end_call()
                    
                elif command == "exit":
                    if self.call_active:
                        self.end_call()
                    self.client.loop_stop()
                    self.client.disconnect()
                    break
                    
                else:
                    print("Unknown command")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
        
        print("Exiting PEBO Voice Call System")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PEBO Voice Call System')
    parser.add_argument('device_id', type=str, help='Unique device ID (e.g., pebo1)')
    
    args = parser.parse_args()
    
    pebo = PeboVoiceCall(args.device_id)
    pebo.interactive_console()
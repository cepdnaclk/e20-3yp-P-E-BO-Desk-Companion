import paho.mqtt.client as mqtt
import pyaudio
import wave
import threading
import time
import json
import argparse
import socket
import os

# Audio settings - optimized for speech
CHUNK = 2048       # Larger chunk size for better performance
FORMAT = pyaudio.paInt16
CHANNELS = 1       # Mono for voice clarity and smaller data size
RATE = 22050       # Higher sample rate for better voice quality
RECORD_SECONDS = 0.5  # Shorter chunks for more real-time feel

# MQTT settings
MQTT_BROKER = "broker.emqx.io"  # Public MQTT broker
MQTT_PORT = 1883
QOS_LEVEL = 1      # QoS 1 ensures message delivery at least once

class LaptopVoiceCall:
    def __init__(self, user_id):
        self.user_id = user_id
        self.other_user = None
        self.call_active = False
        self.audio = pyaudio.PyAudio()
        self.stream_thread = None
        self.temp_dir = "temp_audio"
        
        # Create temp directory if it doesn't exist
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        
        # Get hostname for display
        self.hostname = socket.gethostname()
        
        # Initialize MQTT client with clean session
        self.client = mqtt.Client(client_id=f"laptop_{user_id}_{int(time.time())}", clean_session=True)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        # Connect to MQTT broker
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            print(f"Laptop {self.user_id} ({self.hostname}) connected to MQTT broker")
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected to MQTT broker successfully")
            # Subscribe to control channel and voice channel
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
                # Start voice streaming in a separate thread
                self.stream_thread = threading.Thread(target=self.stream_voice)
                self.stream_thread.daemon = True
                self.stream_thread.start()
                
            elif action == "call_end":
                if self.call_active or self.other_user == caller:
                    print(f"Call ended by {caller}")
                    self.call_active = False
                    self.other_user = None
                    # Voice streaming thread will terminate due to self.call_active being False
        except Exception as e:
            print(f"Error handling control message: {e}")
    
    def handle_voice(self, payload):
        if not self.call_active:
            return
            
        try:
            # Save audio data to temp file
            temp_file = os.path.join(self.temp_dir, f"temp_audio_{int(time.time()*1000)}.wav")
            
            with open(temp_file, "wb") as f:
                f.write(payload)
            
            # Play the audio
            threading.Thread(target=self.play_audio, args=(temp_file,)).start()
            
            # Cleanup old files (keep only last 10 seconds of audio files)
            self.cleanup_temp_files()
            
        except Exception as e:
            print(f"Error handling voice data: {e}")
    
    def cleanup_temp_files(self):
        try:
            now = time.time()
            for f in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, f)
                if os.path.isfile(file_path) and now - os.path.getmtime(file_path) > 10:
                    os.unlink(file_path)
        except Exception as e:
            pass  # Silent cleanup failure
    
    def initiate_call(self, recipient):
        if self.call_active:
            print("Already in a call!")
            return False
            
        self.other_user = recipient
        
        # Send call request
        control_data = {
            "action": "call_request",
            "caller": self.user_id,
            "hostname": self.hostname,
            "timestamp": int(time.time())
        }
        
        self.client.publish(f"laptop/control/{recipient}", json.dumps(control_data), qos=QOS_LEVEL)
        print(f"Calling {recipient}...")
        return True
    
    def accept_call(self):
        if not self.other_user:
            print("No incoming call to accept!")
            return False
            
        # Send acceptance
        control_data = {
            "action": "call_accept",
            "caller": self.user_id,
            "hostname": self.hostname,
            "timestamp": int(time.time())
        }
        
        self.client.publish(f"laptop/control/{self.other_user}", json.dumps(control_data), qos=QOS_LEVEL)
        self.call_active = True
        
        # Start voice streaming
        self.stream_thread = threading.Thread(target=self.stream_voice)
        self.stream_thread.daemon = True
        self.stream_thread.start()
        
        print(f"Call with {self.other_user} started!")
        return True
    
    def end_call(self):
        if not self.call_active and not self.other_user:
            print("No active call to end!")
            return False
            
        # Send end call signal
        control_data = {
            "action": "call_end",
            "caller": self.user_id,
            "hostname": self.hostname,
            "timestamp": int(time.time())
        }
        
        if self.other_user:
            self.client.publish(f"laptop/control/{self.other_user}", json.dumps(control_data), qos=QOS_LEVEL)
        
        self.call_active = False
        if self.other_user:
            print(f"Call with {self.other_user} ended!")
        self.other_user = None
        return True
    
    def record_audio(self, duration=0.5):
        try:
            stream = self.audio.open(format=FORMAT,
                                channels=CHANNELS,
                                rate=RATE,
                                input=True,
                                frames_per_buffer=CHUNK)
            
            frames = []
            
            for i in range(0, int(RATE / CHUNK * duration)):
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            
            # Save to temp file
            temp_file = os.path.join(self.temp_dir, f"temp_recording_{int(time.time()*1000)}.wav")
            wf = wave.open(temp_file, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            return temp_file
        except Exception as e:
            print(f"Error recording audio: {e}")
            return None
    
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
            
            # Try to remove the file after playing
            try:
                os.unlink(filename)
            except:
                pass
                
        except Exception as e:
            print(f"Error playing audio: {e}")
    
    def stream_voice(self):
        print("Voice streaming started. Speak now! (Call in progress)")
        print("------------------------------------------------------")
        
        while self.call_active:
            try:
                # Record a chunk of audio
                audio_file = self.record_audio(RECORD_SECONDS)
                
                if not audio_file or not self.call_active:
                    continue
                
                # Read the recorded data
                with open(audio_file, "rb") as f:
                    audio_data = f.read()
                
                # Send to the other device with QoS 1 for reliability
                self.client.publish(f"laptop/voice/{self.other_user}", audio_data, qos=QOS_LEVEL)
                
                # Clean up the temp recording file
                try:
                    os.unlink(audio_file)
                except:
                    pass
                
                # Small delay to prevent overwhelming the CPU
                time.sleep(0.05)
                
            except Exception as e:
                print(f"Error in voice streaming: {e}")
                time.sleep(1)  # Wait a bit before retrying
        
        print("Voice streaming ended.")
    
    def interactive_console(self):
        print(f"=== Laptop Voice Call System ({self.user_id} on {self.hostname}) ===")
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
                    
                elif command == "y" and self.other_user and not self.call_active:
                    # Shortcut for accepting calls
                    self.accept_call()
                    
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
                    
                elif command == "":
                    # Ignore empty commands
                    pass
                    
                else:
                    print("Unknown command")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
        
        print("Exiting Laptop Voice Call System")
        # Clean up temp directory
        for f in os.listdir(self.temp_dir):
            try:
                os.unlink(os.path.join(self.temp_dir, f))
            except:
                pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Laptop Voice Call System')
    parser.add_argument('user_id', type=str, help='Unique user ID (e.g., alice, bob)')
    
    args = parser.parse_args()
    
    laptop_call = LaptopVoiceCall(args.user_id)
    laptop_call.interactive_console()
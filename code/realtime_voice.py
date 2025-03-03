import paho.mqtt.client as mqtt
import pyaudio
import wave
import threading
import time
import json
import argparse
import socket
import os
import numpy as np
from collections import deque

# Enhanced audio settings for clarity
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100  # CD quality sample rate for better clarity
RECORD_SECONDS = 1.0  # Full 1-second chunks
BUFFER_SECONDS = 0.2  # Buffer to smooth playback

# MQTT settings
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
QOS_LEVEL = 1
MAX_PAYLOAD = 65536  # Maximum MQTT payload size (64KB)

class LaptopVoiceCall:
    def __init__(self, user_id):
        self.user_id = user_id
        self.other_user = None
        self.call_active = False
        self.audio = pyaudio.PyAudio()
        self.stream_thread = None
        self.temp_dir = "temp_audio"
        self.audio_buffer = deque(maxlen=20)  # Playback buffer to smooth audio
        self.playing = False
        self.silence_threshold = 300  # Threshold for silence detection
        
        # Create temp directory if it doesn't exist
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        
        # Get hostname for display
        self.hostname = socket.gethostname()
        
        # Initialize MQTT client with clean session
        client_id = f"laptop_{user_id}_{int(time.time())}"
        self.client = mqtt.Client(client_id=client_id, clean_session=True)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        print(f"Initializing voice call system as {client_id}...")
        
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
                
                # Start audio playback thread
                threading.Thread(target=self.continuous_audio_playback, daemon=True).start()
                
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
            # Add the audio data to the buffer for playback
            self.audio_buffer.append(payload)
        except Exception as e:
            print(f"Error handling voice data: {e}")
    
    def continuous_audio_playback(self):
        """Continuously play audio from the buffer for smoother output"""
        print("Audio playback thread started")
        self.playing = True
        
        # Create output stream once
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
                    # Get the next audio data from the buffer
                    audio_data = self.audio_buffer.popleft()
                    
                    # Convert to wave format for easier processing
                    temp_file = os.path.join(self.temp_dir, f"temp_play_{int(time.time()*1000)}.wav")
                    with open(temp_file, "wb") as f:
                        f.write(audio_data)
                    
                    # Read and play
                    try:
                        wf = wave.open(temp_file, 'rb')
                        frames = wf.readframes(wf.getnframes())
                        output_stream.write(frames)
                        wf.close()
                        
                        # Clean up temp file
                        try:
                            os.unlink(temp_file)
                        except:
                            pass
                    except Exception as e:
                        print(f"Playback error: {e}")
                        
                else:
                    # No audio data, sleep a bit
                    time.sleep(0.01)
                    
        except Exception as e:
            print(f"Audio playback thread error: {e}")
        finally:
            try:
                output_stream.stop_stream()
                output_stream.close()
            except:
                pass
            
            self.playing = False
            print("Audio playback thread stopped")
    
    def is_silent(self, audio_data, format=FORMAT, threshold=None):
        """Check if audio data is silent"""
        if threshold is None:
            threshold = self.silence_threshold
            
        try:
            # Convert audio data to numpy array
            data = np.frombuffer(audio_data, dtype=np.int16)
            # Calculate amplitude
            amplitude = np.abs(data).mean()
            return amplitude < threshold
        except:
            return False  # In case of error, assume not silent
    
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
        
        # Start audio playback thread
        threading.Thread(target=self.continuous_audio_playback, daemon=True).start()
        
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
    
    def record_audio(self, duration=RECORD_SECONDS):
        try:
            # Create a new input stream for each recording
            stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            
            print("Recording...", end="", flush=True)
            frames = []
            
            # Calculate number of chunks to read based on duration
            num_chunks = int(RATE / CHUNK * duration)
            
            # Ensure we always read at least 1 chunk
            num_chunks = max(1, num_chunks)
            
            for i in range(num_chunks):
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
            
            print(" Done")
            
            stream.stop_stream()
            stream.close()
            
            # Check if audio is silent
            all_data = b''.join(frames)
            if self.is_silent(all_data):
                print("Silent frame detected, skipping")
                return None
            
            # Save to temp wave file
            temp_file = os.path.join(self.temp_dir, f"temp_recording_{int(time.time()*1000)}.wav")
            wf = wave.open(temp_file, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(all_data)
            wf.close()
            
            return temp_file
        except Exception as e:
            print(f"Error recording audio: {e}")
            return None
    
    def stream_voice(self):
        print("\nVoice streaming started. Speak now! (Call in progress)")
        print("------------------------------------------------------")
        
        # Wait for buffer time before starting to ensure smooth start
        time.sleep(BUFFER_SECONDS)
        
        while self.call_active:
            try:
                # Record a chunk of audio (full 1 second)
                audio_file = self.record_audio(RECORD_SECONDS)
                
                if not audio_file or not self.call_active:
                    time.sleep(0.1)  # Small delay if no audio or call ended
                    continue
                
                # Read the recorded data
                with open(audio_file, "rb") as f:
                    audio_data = f.read()
                
                # Check file size before sending
                if len(audio_data) > MAX_PAYLOAD:
                    print(f"Warning: Audio payload too large ({len(audio_data)} bytes), skipping")
                    continue
                
                # Send to the other device with QoS 1 for reliability
                result = self.client.publish(f"laptop/voice/{self.other_user}", audio_data, qos=QOS_LEVEL)
                
                # Check if publish was successful
                if not result.is_published():
                    result.wait_for_publish(timeout=2.0)
                
                # Clean up the temp recording file
                try:
                    os.unlink(audio_file)
                except:
                    pass
                
            except Exception as e:
                print(f"Error in voice streaming: {e}")
                time.sleep(0.5)  # Wait before retrying
        
        print("Voice streaming ended.")
    
    def test_microphone(self):
        """Test microphone and speakers"""
        print("\nTesting microphone... speak for 3 seconds")
        audio_file = self.record_audio(3.0)
        
        if audio_file:
            print("Playing back recorded audio...")
            # Create temporary output stream
            stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                output=True,
                frames_per_buffer=CHUNK
            )
            
            wf = wave.open(audio_file, 'rb')
            data = wf.readframes(CHUNK)
            
            while data:
                stream.write(data)
                data = wf.readframes(CHUNK)
                
            stream.stop_stream()
            stream.close()
            wf.close()
            
            print("Audio test complete. Did you hear your voice?")
        else:
            print("Microphone test failed! Check your microphone settings.")
    
    def interactive_console(self):
        print(f"=== Laptop Voice Call System ({self.user_id} on {self.hostname}) ===")
        print("Commands:")
        print("  call <user_id>   - Start a call with another laptop")
        print("  accept           - Accept incoming call")
        print("  end              - End current call")
        print("  status           - Show current status")
        print("  test             - Test microphone and speakers")
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
                
                elif command == "test":
                    self.test_microphone()
                    
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
    parser.add_argument('--broker', type=str, default=MQTT_BROKER, help='MQTT broker address')
    parser.add_argument('--port', type=int, default=MQTT_PORT, help='MQTT broker port')
    
    args = parser.parse_args()
    
    # Update global settings if provided
    MQTT_BROKER = args.broker
    MQTT_PORT = args.port
    
    try:
        # Check if numpy is installed
        import numpy
    except ImportError:
        print("NumPy is required. Installing...")
        os.system('pip install numpy')
        print("NumPy installed. Starting application...")
    
    # Start the voice call system
    laptop_call = LaptopVoiceCall(args.user_id)
    
    # Offer to test the microphone first
    test_mic = input("Would you like to test your microphone before starting? (y/n): ").strip().lower()
    if test_mic == 'y':
        laptop_call.test_microphone()
    
    laptop_call.interactive_console()
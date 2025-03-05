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

# Enhanced audio settings for better quality
CHUNK = 2048
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
SILENCE_THRESHOLD = 300
RECORDING_SECONDS = 6  # Record in 6-second segments

# MQTT settings
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
QOS_LEVEL = 1  # Using QoS 1 for better reliability

# Network performance monitoring
class NetworkStats:
    def __init__(self):
        self.latency_samples = deque(maxlen=50)
        self.packet_loss = 0
        self.last_packet_time = 0
    
    def add_latency_sample(self, latency):
        self.latency_samples.append(latency)
    
    def get_average_latency(self):
        if not self.latency_samples:
            return 0
        return sum(self.latency_samples) / len(self.latency_samples)

class LaptopVoiceCall:
    def __init__(self, user_id):
        self.user_id = user_id
        self.other_user = None
        self.call_active = False
        self.audio = pyaudio.PyAudio()
        self.record_thread = None
        
        self.recording = False
        self.network_stats = NetworkStats()
        
        # Initialize MQTT client
        client_id = f"laptop_{user_id}_{int(time.time())}"
        self.client = mqtt.Client(client_id=client_id, clean_session=True)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        print(f"Initializing simplified voice call system as {client_id}...")
        
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
            print(f"Subscribed to topics: laptop/control/{self.user_id}, laptop/voice/{self.user_id}")
        else:
            print(f"Failed to connect to MQTT broker with code {rc}")
    
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        print(f"Received message on topic: {msg.topic}, payload size: {len(msg.payload)} bytes")
        
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
                # Start network monitoring
                threading.Thread(target=self.network_ping, daemon=True).start()
                # Start audio recording
                self.start_recording()
                
            elif action == "call_end":
                if self.call_active or self.other_user == caller:
                    print(f"Call ended by {caller}")
                    self.call_active = False
                    self.other_user = None
            
            elif action == "ping":
                # Respond to ping requests
                response_data = {
                    "action": "pong",
                    "id": data.get("id"),
                    "timestamp": int(time.time() * 1000)
                }
                self.client.publish(f"laptop/control/{caller}", json.dumps(response_data), qos=QOS_LEVEL)
            
            elif action == "pong":
                # Calculate latency
                now = int(time.time() * 1000)
                sent_time = int(data.get("timestamp", 0))
                latency = now - sent_time
                self.network_stats.add_latency_sample(latency)
                
        except Exception as e:
            print(f"Error handling control message: {e}")
    
    def network_ping(self):
        """Send periodic pings to measure network quality"""
        ping_id = 0
        while self.call_active:
            try:
                ping_id += 1
                ping_data = {
                    "action": "ping",
                    "caller": self.user_id,
                    "id": ping_id,
                    "timestamp": int(time.time() * 1000)
                }
                self.client.publish(f"laptop/control/{self.other_user}", 
                                   json.dumps(ping_data), qos=QOS_LEVEL)
                time.sleep(2)
            except Exception as e:
                print(f"Ping error: {e}")
    
    def handle_voice(self, payload):
        if self.call_active:
            print(f"Received audio packet: {len(payload)} bytes")
            # Play the audio immediately
            threading.Thread(target=self.play_received_audio, args=(payload,), daemon=True).start()
    
    def start_recording(self):
        """Start audio recording thread"""
        if not self.recording:
            self.record_thread = threading.Thread(target=self.record_and_send)
            self.record_thread.daemon = True
            self.record_thread.start()
    
    def record_and_send(self):
        """Record audio for a fixed duration and send as a complete packet"""
        print("\nRecording started. Speak now...")
        self.recording = True
        
        stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        try:
            while self.call_active:
                print("Recording new audio segment...")
                audio_buffer = []
                
                # Record for exactly RECORDING_SECONDS
                for i in range(0, int(RATE / CHUNK * RECORDING_SECONDS)):
                    if not self.call_active:
                        break
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    audio_buffer.append(data)
                
                # Join all chunks into one message and send
                if audio_buffer and self.call_active:
                    complete_audio = b''.join(audio_buffer)
                    print(f"Sending {len(complete_audio)} bytes...")
                    
                    # Send the complete audio segment
                    result = self.client.publish(
                        f"laptop/voice/{self.other_user}", 
                        complete_audio, 
                        qos=QOS_LEVEL
                    )
                    print(f"Message sent, result: {result.rc}")
                    
                    # Wait briefly to ensure message is sent
                    time.sleep(0.2)
                
        except Exception as e:
            print(f"Error in audio recording: {e}")
        finally:
            stream.stop_stream()
            stream.close()
            self.recording = False
            print("Recording stopped.")
    
    def play_received_audio(self, audio_data):
        """Play a complete received audio segment"""
        print(f"Playing received audio ({len(audio_data)} bytes)")
        
        try:
            # Get output device info
            try:
                info = self.audio.get_default_output_device_info()
                print(f"Using audio output device: {info['name']}")
            except:
                print("Couldn't get default output device info")
            
            stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                output=True,
                frames_per_buffer=CHUNK
            )
            
            stream.write(audio_data)
            stream.stop_stream()
            stream.close()
            print("Finished playing audio segment")
            
        except Exception as e:
            print(f"Error playing audio: {e}")
    
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
        
        # Start network monitoring
        threading.Thread(target=self.network_ping, daemon=True).start()
        
        # Start audio recording
        self.start_recording()
        
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
        
        # Print network stats
        avg_latency = self.network_stats.get_average_latency()
        print(f"Call stats - Average latency: {avg_latency:.1f}ms, " +
              f"Packet loss events: {self.network_stats.packet_loss}")
        
        if self.other_user:
            print(f"Call with {self.other_user} ended!")
        self.other_user = None
        return True
    
    def list_audio_devices(self):
        """List all available audio devices"""
        print("\nAvailable Audio Devices:")
        for i in range(self.audio.get_device_count()):
            try:
                device_info = self.audio.get_device_info_by_index(i)
                print(f"Device {i}: {device_info['name']}")
                print(f"  Max Input Channels: {device_info['maxInputChannels']}")
                print(f"  Max Output Channels: {device_info['maxOutputChannels']}")
                print(f"  Default Sample Rate: {device_info['defaultSampleRate']}")
            except:
                print(f"Could not get info for device {i}")
    
    def interactive_console(self):
        print(f"=== Laptop Voice Call System ({self.user_id}) ===")
        print("Commands:")
        print("  call <user_id>   - Start a call with another laptop")
        print("  accept           - Accept incoming call")
        print("  end              - End current call")
        print("  status           - Show current status")
        print("  devices          - List audio devices")
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
                        avg_latency = self.network_stats.get_average_latency()
                        print(f"In call with {self.other_user}")
                        print(f"Network stats - Latency: {avg_latency:.1f}ms, " +
                              f"Packet loss events: {self.network_stats.packet_loss}")
                    elif self.other_user:
                        print(f"Call pending with {self.other_user}")
                    else:
                        print("Not in a call")
                elif command == "devices":
                    self.list_audio_devices()
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
    parser = argparse.ArgumentParser(description='Laptop Voice Call System with Record and Send')
    parser.add_argument('user_id', type=str, help='Unique user ID (e.g., alice, bob)')
    parser.add_argument('--broker', type=str, default=MQTT_BROKER, 
                        help=f'MQTT broker address (default: {MQTT_BROKER})')
    parser.add_argument('--port', type=int, default=MQTT_PORT, 
                        help=f'MQTT broker port (default: {MQTT_PORT})')
    parser.add_argument('--rate', type=int, default=RATE, 
                        help=f'Audio sample rate (default: {RATE})')
    parser.add_argument('--chunk', type=int, default=CHUNK, 
                        help=f'Audio chunk size (default: {CHUNK})')
    parser.add_argument('--record-time', type=int, default=RECORDING_SECONDS, 
                        help=f'Recording time per segment in seconds (default: {RECORDING_SECONDS})')
    args = parser.parse_args()
    
    # Update global settings based on command line arguments
    MQTT_BROKER = args.broker
    MQTT_PORT = args.port
    RATE = args.rate
    CHUNK = args.chunk
    RECORDING_SECONDS = args.record_time
    
    # Initialize the application
    laptop_call = LaptopVoiceCall(args.user_id)
    
    # Start the interactive console
    laptop_call.interactive_console()
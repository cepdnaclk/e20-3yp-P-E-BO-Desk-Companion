# integrated_pebo_communication.py - Add this to your existing main control code

import socket
import pyaudio
import threading
import time
import queue
import json
import asyncio
from firebase_admin import db

class PeboVoiceCommunication:
    def __init__(self, config_path="/home/pi/pebo_config.json"):
        # Audio settings
        self.CHUNK = 2048
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 48000
        
        # Communication state
        self.call_active = False
        self.incoming_call = False
        self.audio_streaming = False
        self.communication_ready = False
        
        # Configuration
        self.config_path = config_path
        self.current_device_config = None
        self.target_device = None
        
        # Audio components
        self.audio_queue = queue.Queue(maxsize=10)
        self.audio = pyaudio.PyAudio()
        self.running = True
        
        # Network sockets
        self.control_socket = None
        self.audio_socket = None
        self.caller_conn = None
        
        # Background threads
        self.call_listener_thread = None
        self.audio_threads = []
        
        # Initialize the communication system
        self.initialize_communication()
    
    def initialize_communication(self):
        """Initialize the communication system in background"""
        try:
            # Load device configuration
            with open(self.config_path, 'r') as config_file:
                self.current_device_config = json.load(config_file)
            
            # Start background call listener
            self.call_listener_thread = threading.Thread(target=self.listen_for_calls, daemon=True)
            self.call_listener_thread.start()
            
            self.communication_ready = True
            print("✅ Pebo voice communication system ready")
            
        except Exception as e:
            print(f"❌ Communication system initialization failed: {e}")
            self.communication_ready = False
    
    async def handle_send_message_command(self, speak_text, listen, recognizer, mic, normal):
        """Handle the 'send message' command - integrate this into your existing code"""
        if not self.communication_ready:
            await speak_text("Communication system is not ready.")
            return
        
        try:
            # Get current device info
            current_ssid = self.current_device_config.get('ssid')
            current_device_id = self.current_device_config.get('deviceId')
            user_id = self.current_device_config.get('userId')
            
            if not all([current_ssid, current_device_id, user_id]):
                await speak_text("Device configuration incomplete.")
                return
            
            # Get current IP address
            current_ip = self.get_ip_address()
            if not current_ip:
                await speak_text("Cannot initiate communication: Not connected to Wi-Fi.")
                return
            
            # Query Firebase for devices on the same SSID
            users_ref = db.reference('users')
            users = users_ref.get()
            if not users:
                await speak_text("No other devices found.")
                return
            
            same_wifi_devices = []
            for uid, user_data in users.items():
                if 'peboDevices' in user_data:
                    for device_id, device_data in user_data['peboDevices'].items():
                        if (device_data.get('ssid') == current_ssid and 
                            device_data.get('ipAddress') != 'Disconnected' and 
                            device_id != current_device_id):
                            same_wifi_devices.append({
                                'user_id': uid,
                                'device_id': device_id,
                                'ip_address': device_data.get('ipAddress'),
                                'location': device_data.get('location', 'Unknown')
                            })
            
            if not same_wifi_devices:
                await speak_text(f"No other devices found on Wi-Fi {current_ssid}.")
                return
            
            # Select device to call
            if len(same_wifi_devices) == 1:
                self.target_device = same_wifi_devices[0]
                await speak_text(f"Calling device in {self.target_device['location']}.")
            else:
                # Ask user to select device
                locations = [device['location'] for device in same_wifi_devices]
                locations_str = ", ".join(locations[:-1]) + (f", or {locations[-1]}" if len(locations) > 1 else locations[0])
                await speak_text(f"Which device would you like to call in {locations_str}?")
                await asyncio.to_thread(normal)
                
                # Get user input for device location
                location_input = await asyncio.get_event_loop().run_in_executor(None, lambda: listen(recognizer, mic))
                if not location_input:
                    await speak_text("Sorry, I didn't catch that.")
                    return
                
                # Find the device matching the user's input
                selected_device = None
                for device in same_wifi_devices:
                    if location_input.lower() in device['location'].lower():
                        selected_device = device
                        break
                
                if selected_device:
                    self.target_device = selected_device
                    await speak_text(f"Calling device in {selected_device['location']}.")
                else:
                    await speak_text("Sorry, I couldn't find a device in that location.")
                    return
            
            # Initiate the call
            await self.initiate_call(speak_text)
            
        except Exception as e:
            print(f"Error in send message: {e}")
            await speak_text("Sorry, there was an error connecting to other devices.")
    
    async def handle_answer_command(self, speak_text):
        """Handle the 'answer' command"""
        if self.incoming_call:
            await self.answer_call(speak_text)
        else:
            await speak_text("No incoming call.")
    
    async def handle_end_communication_command(self, speak_text):
        """Handle the 'end communication' command"""
        if self.call_active:
            await self.end_call(speak_text)
        else:
            await speak_text("No active call to end.")
    
    async def initiate_call(self, speak_text):
        """Initiate a call to the target device"""
        if not self.target_device:
            await speak_text("No target device selected.")
            return
        
        try:
            # Connect to target device's control port
            self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_ip = self.target_device['ip_address']
            control_port = 8889  # Control port
            
            self.control_socket.connect((target_ip, control_port))
            
            # Send call signal
            call_signal = {
                "action": "incoming_call",
                "caller": self.current_device_config.get('location', 'Unknown Device'),
                "caller_ip": self.get_ip_address(),
                "timestamp": time.time()
            }
            
            self.control_socket.send(json.dumps(call_signal).encode())
            await speak_text("Calling... waiting for answer.")
            
            # Wait for response
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.control_socket.recv(1024)
            )
            response_data = json.loads(response.decode())
            
            if response_data["action"] == "call_accepted":
                self.call_active = True
                await speak_text("Call connected! You can now talk.")
                self.start_audio_streaming(target_ip)
                
            elif response_data["action"] == "call_rejected":
                await speak_text("Call was rejected.")
                self.control_socket.close()
                
        except Exception as e:
            print(f"Call initiation error: {e}")
            await speak_text("Failed to connect to the other device.")
    
    async def answer_call(self, speak_text):
        """Answer an incoming call"""
        if not self.incoming_call or not self.caller_conn:
            return
        
        try:
            # Send acceptance response
            response = {
                "action": "call_accepted",
                "timestamp": time.time()
            }
            self.caller_conn.send(json.dumps(response).encode())
            
            self.incoming_call = False
            self.call_active = True
            await speak_text("Call connected! You can now talk.")
            
            # Start audio streaming
            caller_ip = self.caller_info.get('caller_ip')
            if caller_ip:
                self.start_audio_streaming(caller_ip)
            
        except Exception as e:
            print(f"Answer call error: {e}")
            await speak_text("Failed to answer call.")
    
    async def end_call(self, speak_text):
        """End the active call"""
        try:
            if self.control_socket:
                end_signal = {
                    "action": "end_call",
                    "timestamp": time.time()
                }
                self.control_socket.send(json.dumps(end_signal).encode())
                self.control_socket.close()
                self.control_socket = None
            
            self.call_active = False
            self.audio_streaming = False
            await speak_text("Call ended.")
            
            # Stop audio streaming
            self.stop_audio_streaming()
            
        except Exception as e:
            print(f"End call error: {e}")
    
    def listen_for_calls(self):
        """Background thread to listen for incoming calls"""
        try:
            control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            control_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            control_sock.bind(('0.0.0.0', 8889))  # Control port
            control_sock.listen(1)
            print("🔔 Listening for incoming calls...")
            
            while self.running:
                try:
                    conn, addr = control_sock.accept()
                    self.caller_conn = conn
                    
                    # Handle incoming call
                    data = conn.recv(1024)
                    if data:
                        message = json.loads(data.decode())
                        if message["action"] == "incoming_call":
                            self.incoming_call = True
                            self.caller_info = message
                            caller_name = message.get("caller", "Unknown")
                            
                            # This will be handled by your main speech loop
                            print(f"📞 INCOMING CALL from {caller_name}")
                            print("Say 'answer' to accept the call")
                            
                        elif message["action"] == "end_call":
                            self.call_active = False
                            self.audio_streaming = False
                            self.stop_audio_streaming()
                            print("📞 Call ended by caller")
                            
                except Exception as e:
                    print(f"Call listener error: {e}")
                    
        except Exception as e:
            print(f"Call listener setup error: {e}")
    
    def start_audio_streaming(self, target_ip):
        """Start audio streaming threads"""
        if self.audio_streaming:
            return
        
        self.audio_streaming = True
        self.target_ip = target_ip
        
        # Setup audio streams
        self.setup_audio_streams()
        
        # Start audio threads
        send_thread = threading.Thread(target=self.send_audio, daemon=True)
        receive_thread = threading.Thread(target=self.receive_audio, daemon=True)
        play_thread = threading.Thread(target=self.play_audio, daemon=True)
        
        self.audio_threads = [send_thread, receive_thread, play_thread]
        
        for thread in self.audio_threads:
            thread.start()
    
    def stop_audio_streaming(self):
        """Stop audio streaming"""
        self.audio_streaming = False
        
        try:
            if hasattr(self, 'mic_stream') and self.mic_stream:
                self.mic_stream.stop_stream()
                self.mic_stream.close()
            if hasattr(self, 'speaker_stream') and self.speaker_stream:
                self.speaker_stream.stop_stream()
                self.speaker_stream.close()
            if self.audio_socket:
                self.audio_socket.close()
                self.audio_socket = None
        except Exception as e:
            print(f"Audio cleanup error: {e}")
    
    def setup_audio_streams(self):
        """Setup audio input/output streams"""
        try:
            self.mic_stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )
            
            self.speaker_stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                output=True,
                frames_per_buffer=self.CHUNK
            )
        except Exception as e:
            print(f"Audio setup error: {e}")
    
    def send_audio(self):
        """Send audio to target device"""
        try:
            self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.audio_socket.connect((self.target_ip, 8888))  # Audio port
            
            while self.audio_streaming and self.call_active:
                try:
                    data = self.mic_stream.read(self.CHUNK, exception_on_overflow=False)
                    self.audio_socket.send(data)
                except Exception as e:
                    print(f"Send audio error: {e}")
                    break
                    
        except Exception as e:
            print(f"Audio send connection error: {e}")
    
    def receive_audio(self):
        """Receive audio from target device"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('0.0.0.0', 8888))  # Audio port
            sock.listen(1)
            
            conn, addr = sock.accept()
            
            while self.audio_streaming and self.call_active:
                try:
                    data = conn.recv(self.CHUNK * 2)
                    if not data:
                        break
                    if not self.audio_queue.full():
                        self.audio_queue.put(data)
                except Exception as e:
                    print(f"Receive audio error: {e}")
                    break
                    
        except Exception as e:
            print(f"Audio receive error: {e}")
    
    def play_audio(self):
        """Play received audio"""
        while self.audio_streaming and self.call_active:
            try:
                data = self.audio_queue.get(timeout=0.1)
                self.speaker_stream.write(data)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Audio playback error: {e}")
                continue
    
    def get_ip_address(self):
        """Get current IP address"""
        try:
            import subprocess
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
            return result.stdout.strip().split()[0]
        except:
            return None
    
    def cleanup(self):
        """Cleanup resources"""
        self.running = False
        self.call_active = False
        self.audio_streaming = False
        self.stop_audio_streaming()
        if self.audio:
            self.audio.terminate()

# Global instance
pebo_communication = PeboVoiceCommunication()

# Integration functions for your existing code
async def handle_send_message(speak_text, listen, recognizer, mic, normal):
    """Add this to your existing 'send message' command handler"""
    await pebo_communication.handle_send_message_command(speak_text, listen, recognizer, mic, normal)

async def handle_answer_call(speak_text):
    """Add this to handle 'answer' command"""
    await pebo_communication.handle_answer_command(speak_text)

async def handle_end_communication(speak_text):
    """Add this to handle 'end communication' command"""
    await pebo_communication.handle_end_communication_command(speak_text)

# Add these command handlers to your existing speech recognition loop
def integrate_voice_commands(user_input, speak_text, listen, recognizer, mic, normal):
    """
    Add this to your existing command processing logic
    
    Replace your existing "send message" handler with:
    """
    if user_input == "send message":
        asyncio.create_task(handle_send_message(speak_text, listen, recognizer, mic, normal))
        return True
    
    elif user_input == "answer" or user_input == "accept":
        asyncio.create_task(handle_answer_call(speak_text))
        return True
    
    elif user_input == "end communication" or user_input == "hang up":
        asyncio.create_task(handle_end_communication(speak_text))
        return True
    
    return False  # Command not handled, continue with other commands
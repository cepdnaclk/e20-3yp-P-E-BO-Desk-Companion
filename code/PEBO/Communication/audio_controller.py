import threading
import time
import socket
import pyaudio
import queue
from enum import Enum

class NodeType(Enum):
    LAPTOP = "laptop"
    PI = "pi"

class AudioCommunicationController:
    def __init__(self, node_type=NodeType.LAPTOP, 
                 laptop_ip="192.168.124.94", 
                 pi_ip="192.168.124.182",
                 laptop_port=8889,
                 pi_port=8888):
        self.node_type = node_type
        self.laptop_ip = laptop_ip
        self.pi_ip = pi_ip
        self.laptop_port = laptop_port
        self.pi_port = pi_port
        
        # Audio settings
        self.CHUNK = 2048
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 48000
        
        # Control flags
        self.running = False
        self.connected = False
        self.mic_enabled = True
        self.speaker_enabled = True
        
        # Audio components
        self.audio = None
        self.mic_stream = None
        self.speaker_stream = None
        self.audio_queue = queue.Queue(maxsize=10)
        
        # Network components
        self.send_socket = None
        self.receive_socket = None
        self.connection = None
        
        # Threads
        self.send_thread = None
        self.receive_thread = None
        self.play_thread = None
        
        # Stats
        self.stats = {
            'bytes_sent': 0,
            'bytes_received': 0,
            'packets_sent': 0,
            'packets_received': 0,
            'connection_errors': 0,
            'audio_errors': 0
        }
        
    def setup_audio(self):
        try:
            self.audio = pyaudio.PyAudio()
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
            print("✓ Audio streams initialized")
            return True
        except Exception as e:
            print(f"✗ Audio setup failed: {e}")
            self.stats['audio_errors'] += 1
            return False
    
    def get_network_config(self):
        return {
            'listen_port': self.laptop_port if self.node_type == NodeType.LAPTOP else self.pi_port,
            'target_host': self.pi_ip if self.node_type == NodeType.LAPTOP else self.laptop_ip,
            'target_port': self.pi_port if self.node_type == NodeType.LAPTOP else self.laptop_port
        }

    def send_audio(self):
        config = self.get_network_config()
        try:
            self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            time.sleep(2)
            self.send_socket.connect((config['target_host'], config['target_port']))
            print(f"✓ Connected to {config['target_host']}:{config['target_port']} for sending")

            while self.running:
                if not self.mic_enabled:
                    time.sleep(0.1)
                    continue
                try:
                    data = self.mic_stream.read(self.CHUNK, exception_on_overflow=False)
                    self.send_socket.send(data)
                    self.stats['bytes_sent'] += len(data)
                    self.stats['packets_sent'] += 1
                except Exception as e:
                    print(f"Send error: {e}")
                    break
        except Exception as e:
            print(f"Send socket error: {e}")
        finally:
            if self.send_socket:
                self.send_socket.close()

    def receive_audio(self):
        config = self.get_network_config()
        try:
            self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.receive_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.receive_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            self.receive_socket.bind(('0.0.0.0', config['listen_port']))
            self.receive_socket.listen(1)
            print(f"Listening on port {config['listen_port']}...")

            self.connection, addr = self.receive_socket.accept()
            print(f"✓ Connection accepted from {addr}")
            self.connected = True

            while self.running:
                try:
                    data = self.connection.recv(self.CHUNK * 2)
                    if not data:
                        break
                    self.stats['bytes_received'] += len(data)
                    self.stats['packets_received'] += 1
                    if self.speaker_enabled and not self.audio_queue.full():
                        self.audio_queue.put(data)
                except Exception as e:
                    print(f"Receive error: {e}")
                    break
        except Exception as e:
            print(f"Receive socket error: {e}")
        finally:
            self.connected = False
            if self.connection:
                self.connection.close()
            if self.receive_socket:
                self.receive_socket.close()

    def play_audio(self):
        while self.running:
            if not self.speaker_enabled:
                time.sleep(0.1)
                continue
            try:
                data = self.audio_queue.get(timeout=0.1)
                self.speaker_stream.write(data)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Playback error: {e}")
                self.stats['audio_errors'] += 1

    def start_communication(self):
        if self.running:
            print("Communication already running.")
            return False
        print(f"🔊 Starting communication as {self.node_type.value}")
        if not self.setup_audio():
            return False
        self.running = True
        self.send_thread = threading.Thread(target=self.send_audio)
        self.receive_thread = threading.Thread(target=self.receive_audio)
        self.play_thread = threading.Thread(target=self.play_audio)
        self.send_thread.daemon = True
        self.receive_thread.daemon = True
        self.play_thread.daemon = True
        self.send_thread.start()
        self.receive_thread.start()
        self.play_thread.start()
        return True

    def stop_communication(self):
        self.running = False
        print("🛑 Stopping communication...")
        if self.mic_stream:
            self.mic_stream.stop_stream()
            self.mic_stream.close()
        if self.speaker_stream:
            self.speaker_stream.stop_stream()
            self.speaker_stream.close()
        if self.audio:
            self.audio.terminate()
        if self.send_socket:
            try: self.send_socket.close()
            except: pass
        if self.connection:
            try: self.connection.close()
            except: pass
        if self.receive_socket:
            try: self.receive_socket.close()
            except: pass

    def toggle_microphone(self):
        self.mic_enabled = not self.mic_enabled
        print(f"Microphone: {'ON' if self.mic_enabled else 'OFF'}")
        return self.mic_enabled

    def toggle_speaker(self):
        self.speaker_enabled = not self.speaker_enabled
        print(f"Speaker: {'ON' if self.speaker_enabled else 'OFF'}")
        return self.speaker_enabled

    def print_status(self):
        print("\n📡 Communication Status:")
        print(f"  Node:        {self.node_type.value}")
        print(f"  Running:     {'✓' if self.running else '✗'}")
        print(f"  Connected:   {'✓' if self.connected else '✗'}")
        print(f"  Microphone:  {'ON' if self.mic_enabled else 'OFF'}")
        print(f"  Speaker:     {'ON' if self.speaker_enabled else 'OFF'}")
        print(f"  Bytes Sent:  {self.stats['bytes_sent']}")
        print(f"  Bytes Received: {self.stats['bytes_received']}")
        print(f"  Packets Sent: {self.stats['packets_sent']}")
        print(f"  Packets Received: {self.stats['packets_received']}")
        print(f"  Errors:      {self.stats['connection_errors']} net / {self.stats['audio_errors']} audio\n")

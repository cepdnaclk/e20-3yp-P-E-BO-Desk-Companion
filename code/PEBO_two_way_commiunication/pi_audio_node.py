# pi_audio_node.py - Run on Raspberry Pi
import socket
import pyaudio
import threading
import time

class AudioNode:
    def __init__(self, listen_port=8888, target_host='192.168.38.182', target_port=8889):
        # Audio settings
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        
        # Network settings
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port
        
        # Initialize audio
        self.audio = pyaudio.PyAudio()
        self.running = True
        
        # Setup audio streams
        self.setup_audio()
        
    def setup_audio(self):
        # Microphone stream (input)
        self.mic_stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        
        # Speaker stream (output)
        self.speaker_stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            output=True,
            frames_per_buffer=self.CHUNK
        )
    
    def send_audio(self):
        """Send microphone audio to laptop"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            time.sleep(2)  # Wait for receiver to start
            sock.connect((self.target_host, self.target_port))
            print(f"Connected to laptop at {self.target_host}:{self.target_port}")
            
            while self.running:
                try:
                    data = self.mic_stream.read(self.CHUNK, exception_on_overflow=False)
                    sock.send(data)
                except Exception as e:
                    print(f"Send error: {e}")
                    break
                    
        except Exception as e:
            print(f"Connection error: {e}")
        finally:
            try:
                sock.close()
            except:
                pass
    
    def receive_audio(self):
        """Receive laptop audio and play through speaker"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('0.0.0.0', self.listen_port))
            sock.listen(1)
            print(f"Listening for laptop connection on port {self.listen_port}")
            
            conn, addr = sock.accept()
            print(f"Laptop connected from {addr}")
            
            while self.running:
                try:
                    data = conn.recv(self.CHUNK)
                    if not data:
                        break
                    self.speaker_stream.write(data)
                except Exception as e:
                    print(f"Receive error: {e}")
                    break
                    
        except Exception as e:
            print(f"Listen error: {e}")
        finally:
            try:
                conn.close()
                sock.close()
            except:
                pass
    
    def start(self):
        """Start both sending and receiving threads"""
        print("Starting Pi audio node...")
        print("Set your Bluetooth mic as default input:")
        print("pactl set-default-source bluez_input.E1_0D_7B_25_E6_04.0")
        
        # Start threads
        send_thread = threading.Thread(target=self.send_audio)
        receive_thread = threading.Thread(target=self.receive_audio)
        
        send_thread.daemon = True
        receive_thread.daemon = True
        
        receive_thread.start()
        send_thread.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
            self.running = False
            
        # Cleanup
        self.mic_stream.stop_stream()
        self.speaker_stream.stop_stream()
        self.mic_stream.close()
        self.speaker_stream.close()
        self.audio.terminate()

if __name__ == "__main__":
    # Replace with your laptop's IP address
    LAPTOP_IP = "192.168.38.182"  # Change this!
    
    node = AudioNode(
        listen_port=8888,      # Pi listens on this port
        target_host=LAPTOP_IP, # Laptop IP
        target_port=8889       # Laptop listens on this port
    )
    node.start()
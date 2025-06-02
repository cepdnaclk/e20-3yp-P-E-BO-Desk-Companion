import socket
import pyaudio
import threading
import time
import queue

class AudioNode:
    def __init__(self, listen_port=8888, target_host='172.20.10.11', target_port=8888):
        # Audio settings for Raspberry Pi Bluetooth speaker (48kHz)
        self.CHUNK = 2048
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        
        # Network settings
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port
        
        # Audio buffer queue for smoother playback
        self.audio_queue = queue.Queue(maxsize=10)
        
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
            frames_per_buffer=self.CHUNK,
            input_device_index=None  # Use default input
        )
        
        # Speaker stream (output)
        self.speaker_stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            output=True,
            frames_per_buffer=self.CHUNK,
            output_device_index=None,  # Use default output (Bluetooth speaker)
            stream_callback=None
        )
    
    def send_audio(self):
        """Send microphone audio to target Pi"""
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
                sock.connect((self.target_host, self.target_port))
                print(f"Connected to Pi at {self.target_host}:{self.target_port}")
                
                while self.running:
                    try:
                        data = self.mic_stream.read(self.CHUNK, exception_on_overflow=False)
                        sock.send(data)
                    except Exception as e:
                        print(f"Send error: {e}")
                        break
                        
            except Exception as e:
                print(f"Connection error: {e}")
                time.sleep(2)  # Retry after delay
            finally:
                try:
                    sock.close()
                except:
                    pass
    
    def receive_audio(self):
        """Receive audio from target Pi and queue for playback"""
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
                sock.bind(('0.0.0.0', self.listen_port))
                sock.listen(1)
                print(f"Listening for Pi connection on port {self.listen_port}")
                
                conn, addr = sock.accept()
                print(f"Pi connected from {addr}")
                
                while self.running:
                    try:
                        data = conn.recv(self.CHUNK * 2)  # *2 for int16 format
                        if not data:
                            break
                        if not self.audio_queue.full():
                            self.audio_queue.put(data)
                    except Exception as e:
                        print(f"Receive error: {e}")
                        break
                        
            except Exception as e:
                print(f"Listen error: {e}")
                time.sleep(2)  # Retry after delay
            finally:
                try:
                    conn.close()
                    sock.close()
                except:
                    pass
    
    def play_audio(self):
        """Play audio from queue"""
        while self.running:
            try:
                data = self.audio_queue.get(timeout=0.1)
                self.speaker_stream.write(data)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Playback error: {e}")
                continue
    
    def start(self):
        """Start sending, receiving, and playback threads"""
        print("Starting Pi audio node...")
        print("Using 48kHz for Bluetooth speakers")
        
        send_thread = threading.Thread(target=self.send_audio)
        receive_thread = threading.Thread(target=self.receive_audio)
        play_thread = threading.Thread(target=self.play_audio)
        
        send_thread.daemon = True
        receive_thread.daemon = True
        play_thread.daemon = True
        
        receive_thread.start()
        play_thread.start()
        send_thread.start()
        
        try:
            while self.running:
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
    node = AudioNode(
        listen_port=8888,      # Pi 1 listens on this port
        target_host='172.20.10.11', # Pi 2 IP
        target_port=8888       # Pi 2 listens on this port
    )
    node.start()

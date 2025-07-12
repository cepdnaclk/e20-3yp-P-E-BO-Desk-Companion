import socket
import pyaudio
import threading
import time
import queue
import argparse

class AudioNode:
    def __init__(self, listen_port, target_host, target_port):
        # Audio settings for Raspberry Pi (48kHz for Bluetooth compatibility)
        self.CHUNK = 2048
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 48000
        
        # Network settings
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port
        
        # Audio buffer queue for smoother playback
        self.audio_queue = queue.Queue(maxsize=20)  # Increased for stability
        
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
            output_device_index=None  # Use default output
        )
    
    def send_audio(self):
        """Send microphone audio to target"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            time.sleep(5)  # Wait for receiver to start
            sock.connect((self.target_host, self.target_port))
            print(f"Connected to {self.target_host}:{self.target_port}")
            
            while self.running:
                try:
                    data = self.mic_stream.read(self.CHUNK, exception_on_overflow=False)
                    print(f"Sending {len(data)} bytes")  # Debug
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
        """Receive audio and add to playback queue"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            sock.bind(('0.0.0.0', self.listen_port))
            sock.listen(1)
            print(f"Listening for connection on port {self.listen_port}")
            
            conn, addr = sock.accept()
            print(f"Connected from {addr}")
            
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
                print(f"Playing {len(data)} bytes")  # Debug
                self.speaker_stream.write(data)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Playback error: {e}")
                continue
    
    def start(self):
        """Start sending, receiving, and playback threads"""
        print("Starting Pi audio node...")
        print(f"Using 48kHz, listening on {self.listen_port}, sending to {self.target_host}:{self.target_port}")
        
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
    parser = argparse.ArgumentParser(description="Raspberry Pi audio node for two-way communication")
    parser.add_argument("--listen-port", type=int, required=True, help="Port to listen on")
    parser.add_argument("--target-host", type=str, required=True, help="Target IP to send audio to")
    parser.add_argument("--target-port", type=int, required=True, help="Target port to send audio to")
    args = parser.parse_args()
    
    node = AudioNode(
        listen_port=args.listen_port,
        target_host=args.target_host,
        target_port=args.target_port
    )
    node.start()

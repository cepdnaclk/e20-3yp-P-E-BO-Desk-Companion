# laptop_audio_node.py - FIXED VERSION for Laptop with Amplified Playback
import socket
import pyaudio
import threading
import time
import queue
import numpy as np  # For amplification

class AudioNode:
    def __init__(self, listen_port=8889, target_host='172.20.10.11', target_port=8888):
        # FIXED: Audio settings to match Pi (48kHz)
        self.CHUNK = 2048
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 48000
        
        # Network settings
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port
        
        # Audio buffer queue
        self.audio_queue = queue.Queue(maxsize=10)
        
        # PyAudio instance
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
        """Send microphone audio to Pi"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            time.sleep(2)
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
        finally:
            try:
                sock.close()
            except:
                pass

    def receive_audio(self):
        """Receive Pi audio and queue for playback"""
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
                    data = conn.recv(self.CHUNK * 2)
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
        """Play received audio with amplification"""
        amplification_factor = 2.0  # Adjust volume level here
        while self.running:
            try:
                data = self.audio_queue.get(timeout=0.1)

                # Amplify the audio
                audio_data = np.frombuffer(data, dtype=np.int16)
                amplified = np.clip(audio_data * amplification_factor, -32768, 32767).astype(np.int16)
                self.speaker_stream.write(amplified.tobytes())

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Playback error: {e}")
                continue

    def start(self):
        """Start audio node"""
        print("Starting laptop audio node...")
        print("Using 48kHz to match Pi Bluetooth speakers")

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
    # Replace with your Pi's IP address
    PI_IP = "192.168.248.203"  # Change this!

    node = AudioNode(
        listen_port=8889,
        target_host=PI_IP,
        target_port=8888
    )
    node.start()

# pi_audio_node.py - Audio sender for Pebo1
import socket
import pyaudio
import threading
import time
import queue
import sys

class AudioNode:
    def __init__(self, listen_port=8888, target_host='192.168.124.182', target_port=8889):
        self.CHUNK = 2048
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 48000
        
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port
        
        self.audio_queue = queue.Queue(maxsize=10)
        self.audio = pyaudio.PyAudio()
        self.running = True
        
        self.setup_audio()
        
    def setup_audio(self):
        """Setup audio streams"""
        try:
            self.mic_stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
                input_device_index=None
            )
            
            self.speaker_stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                output=True,
                frames_per_buffer=self.CHUNK,
                output_device_index=None
            )
            print("[AudioNode] Audio streams initialized")
        except Exception as e:
            print(f"[AudioNode] Audio setup error: {e}")
            sys.exit(1)
    
    def send_audio(self):
        """Send microphone audio to target"""
        retry_count = 0
        max_retries = 5
        
        while self.running and retry_count < max_retries:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
                sock.settimeout(10)
                
                print(f"[AudioNode] Attempting to connect to {self.target_host}:{self.target_port}")
                sock.connect((self.target_host, self.target_port))
                print(f"[AudioNode] Connected to target")
                
                retry_count = 0  # Reset retry count on successful connection
                
                while self.running:
                    try:
                        data = self.mic_stream.read(self.CHUNK, exception_on_overflow=False)
                        sock.send(data)
                    except Exception as e:
                        print(f"[AudioNode] Send error: {e}")
                        break
                        
            except Exception as e:
                print(f"[AudioNode] Connection error: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    print(f"[AudioNode] Retrying connection in 2 seconds... ({retry_count}/{max_retries})")
                    time.sleep(2)
                else:
                    print(f"[AudioNode] Max retries reached. Giving up.")
                    
            finally:
                try:
                    sock.close()
                except:
                    pass
    
    def receive_audio(self):
        """Receive audio from target"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            sock.bind(('0.0.0.0', self.listen_port))
            sock.listen(1)
            sock.settimeout(1)
            
            print(f"[AudioNode] Listening for connection on port {self.listen_port}")
            
            while self.running:
                try:
                    conn, addr = sock.accept()
                    print(f"[AudioNode] Target connected from {addr}")
                    
                    while self.running:
                        try:
                            data = conn.recv(self.CHUNK * 2)
                            if not data:
                                break
                                
                            if not self.audio_queue.full():
                                self.audio_queue.put(data)
                                
                        except Exception as e:
                            print(f"[AudioNode] Receive error: {e}")
                            break
                            
                    conn.close()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"[AudioNode] Listen error: {e}")
                        
        except Exception as e:
            print(f"[AudioNode] Setup error: {e}")
        finally:
            try:
                sock.close()
            except:
                pass
    
    def play_audio(self):
        """Play received audio"""
        while self.running:
            try:
                data = self.audio_queue.get(timeout=0.1)
                self.speaker_stream.write(data)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[AudioNode] Playback error: {e}")
                continue
    
    def start(self):
        """Start all audio threads"""
        print("[AudioNode] Starting Pi audio node...")
        
        # Start threads
        send_thread = threading.Thread(target=self.send_audio)
        receive_thread = threading.Thread(target=self.receive_audio)
        play_thread = threading.Thread(target=self.play_audio)
        
        send_thread.daemon = True
        receive_thread.daemon = True
        play_thread.daemon = True
        
        receive_thread.start()
        play_thread.start()
        
        # Wait a bit before starting to send
        time.sleep(2)
        send_thread.start()
        
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[AudioNode] Stopping...")
            self.running = False
            
        # Cleanup
        self.cleanup()
        
    def cleanup(self):
        """Cleanup audio resources"""
        try:
            self.mic_stream.stop_stream()
            self.speaker_stream.stop_stream()
            self.mic_stream.close()
            self.speaker_stream.close()
            self.audio.terminate()
            print("[AudioNode] Audio resources cleaned up")
        except Exception as e:
            print(f"[AudioNode] Cleanup error: {e}")


if __name__ == "__main__":
    # Get configuration from command line or use defaults
    if len(sys.argv) >= 2:
        target_host = sys.argv[1]
    else:
        target_host = "192.168.124.182"  # Default to pebo2 IP
        
    node = AudioNode(
        listen_port=8888,
        target_host=target_host,
        target_port=8889
    )
    node.start()
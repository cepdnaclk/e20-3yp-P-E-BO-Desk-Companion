import socket
import pyaudio
import threading
import time
import queue
import RPi.GPIO as GPIO

class AudioNode:
    def __init__(self, listen_port=8888, target_host='192.168.248.94', target_port=8889, touch_pin=17):
        # Audio settings to match Pi's Bluetooth speaker (48kHz)
        self.CHUNK = 2048  # Increased buffer size for Bluetooth
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 48000  # Changed from 44100 to match Pi speakers
        
        # Network settings
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port
        self.touch_pin = touch_pin  # Store touch pin
        
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
            output_device_index=None,  # Use default output (your Bluetooth speaker)
            stream_callback=None
        )
    
    def send_audio(self):
        """Send microphone audio to laptop"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
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
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            sock.bind(('0.0.0.0', self.listen_port))
            sock.listen(1)
            print(f"Listening for laptop connection on port {self.listen_port}")
            
            conn, addr = sock.accept()
            print(f"Laptop connected from {addr}")
            
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
        """Separate thread for smooth audio playback"""
        while self.running:
            try:
                data = self.audio_queue.get(timeout=0.1)
                self.speaker_stream.write(data)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Playback error: {e}")
                continue
    
    def detect_double_tap(self):
        """
        Detects a double-tap on the touch sensor (two quick touches within 0.5 seconds).
        Returns True if double-tap is detected, False otherwise.
        """
        GPIO.setmode(GPIO.BCM)  # Set BCM numbering mode
        GPIO.setup(self.touch_pin, GPIO.IN)  # Set pin as input
        first_tap_time = None
        tap_count = 0
        max_interval = 0.5  # Maximum time between taps (seconds)
        min_tap_duration = 0.05  # Minimum duration for a valid tap
        max_tap_duration = 0.3  # Maximum duration for a valid tap
        last_state = GPIO.LOW
        
        while self.running:
            current_state = GPIO.input(self.touch_pin)
            
            if current_state == GPIO.HIGH and last_state == GPIO.LOW:
                # Start of a tap
                tap_start = time.time()
                last_state = GPIO.HIGH
                print("Tap started")
                
            elif current_state == GPIO.LOW and last_state == GPIO.HIGH:
                # End of a tap
                tap_duration = time.time() - tap_start
                last_state = GPIO.LOW
                
                if min_tap_duration <= tap_duration <= max_tap_duration:
                    # Valid tap
                    print("Valid tap detected")
                    current_time = time.time()
                    
                    if tap_count == 0:
                        # First tap
                        first_tap_time = current_time
                        tap_count = 1
                    elif tap_count == 1 and (current_time - first_tap_time) <= max_interval:
                        # Second tap within interval
                        print("Double-tap detected!")
                        return True
                    else:
                        # Reset if interval exceeded
                        first_tap_time = current_time
                        tap_count = 1
                
            time.sleep(0.01)  # Short delay for debouncing
            last_state = current_state
        
        return False
    
    def stop(self):
        """Stop all threads and clean up resources"""
        print("Stopping audio node...")
        self.running = False
        
        # Cleanup audio streams
        try:
            self.mic_stream.stop_stream()
            self.speaker_stream.stop_stream()
            self.mic_stream.close()
            self.speaker_stream.close()
            self.audio.terminate()
        except Exception as e:
            print(f"Error cleaning up audio streams: {e}")
    
    def start(self):
        """Start both sending and receiving threads with double-tap detection"""
        print("Starting Pi audio node...")
        print("Using 48kHz to match Pi Bluetooth speakers")
        
        # Start audio threads
        send_thread = threading.Thread(target=self.send_audio)
        receive_thread = threading.Thread(target=self.receive_audio)
        play_thread = threading.Thread(target=self.play_audio)
        
        send_thread.daemon = True
        receive_thread.daemon = True
        play_thread.daemon = True
        
        receive_thread.start()
        play_thread.start()
        send_thread.start()
        
        # Start double-tap detection
        try:
            if self.detect_double_tap():
                self.stop()
        except KeyboardInterrupt:
            self.stop()
        
        # Wait for threads to finish
        send_thread.join(timeout=1)
        receive_thread.join(timeout=1)
        play_thread.join(timeout=1)

def start_audio_node(listen_port=8888, target_host='192.168.248.94', target_port=8889, touch_pin=17):
    """
    Start the audio node for Pi communication.
    
    Args:
        listen_port (int): Port to listen for incoming audio
        target_host (str): IP address of the target device (e.g., laptop)
        target_port (int): Port the target device listens on
        touch_pin (int): GPIO pin number for the touch sensor
    """
    node = AudioNode(listen_port=listen_port, target_host=target_host, target_port=target_port, touch_pin=touch_pin)
    node.start()

if __name__ == "__main__":
    # Replace with your laptop's IP address
    LAPTOP_IP = "172.20.10.11"  # Change this!
    
    start_audio_node(
        listen_port=8888,      # Pi listens on this port
        target_host=LAPTOP_IP, # Laptop IP
        target_port=8889,      # Laptop listens on this port
        touch_pin=17
    )

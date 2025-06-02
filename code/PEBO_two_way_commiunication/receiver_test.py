import socket
import pyaudio
import threading
import queue
import logging
import time
import numpy as np
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/ipconfig/receiver_log.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Firebase configuration
def initialize_firebase():
    if not firebase_admin._apps:
        try:
            service_account_path = '/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/ipconfig/firebase_config.json'
            if not os.path.exists(service_account_path):
                logger.error(f"Service account key not found at {service_account_path}")
                raise FileNotFoundError(f"Service account key not found at {service_account_path}")
            
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://pebo-task-manager-767f3-default-rtdb.asia-southeast1.firebasedatabase.app'
            })
            logger.info("Firebase initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            raise

# Initialize Firebase
initialize_firebase()

class AudioNode:
    def __init__(self, listen_port=8889, target_host=None, target_port=8888, device_id='pebo_rpi_1', user_id='CURRENT_USER_ID'):
        self.CHUNK = 2048
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 48000
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port
        self.audio_queue = queue.Queue(maxsize=10)
        self.audio = pyaudio.PyAudio()
        self.running = False
        self.device_id = device_id
        self.user_id = user_id
        self.setup_audio()
        
    def setup_audio(self):
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
            output_device_index=None,
            stream_callback=None
        )
    
    def generate_ringing_tone(self, duration=2.0):
        """Generate a simple ringing tone"""
        t = np.linspace(0, duration, int(self.RATE * duration), False)
        tone = 0.5 * np.sin(2 * np.pi * 440 * t)  # 440 Hz tone
        tone = (tone * 32767).astype(np.int16)  # Convert to 16-bit
        return tone.tobytes()
    
    def play_ringing(self, caller_id):
        """Play ringing sound and display caller"""
        print(f"Incoming call from {caller_id}...")
        tone = self.generate_ringing_tone()
        for _ in range(3):  # Ring 3 times
            self.speaker_stream.write(tone)
            time.sleep(2.0)  # 2 seconds between rings
    
    def monitor_requests(self):
        """Monitor Firebase for incoming communication requests"""
        requests_ref = db.reference(f'users/{self.user_id}/communicationRequests')
        while True:
            requests = requests_ref.get()
            if requests:
                for request_id, request_data in requests.items():
                    if request_data.get('to_device_id') == self.device_id and request_data.get('status') == 'pending':
                        logger.info(f"Received call request from {request_data['from_device_id']}")
                        self.play_ringing(request_data['from_device_id'])
                        
                        # Wait for user acceptance
                        accept = input(f"Accept call from {request_data['from_device_id']}? (y/n): ").lower()
                        if accept == 'y':
                            requests_ref.child(request_id).update({'status': 'accepted'})
                            self.target_host = request_data.get('from_ip')
                            self.start_communication()
                        else:
                            requests_ref.child(request_id).update({'status': 'rejected'})
                            logger.info(f"Call from {request_data['from_device_id']} rejected")
            time.sleep(1)  # Check every second
    
    def send_audio(self):
        """Send microphone audio to the initiating Pi"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            time.sleep(2)
            sock.connect((self.target_host, self.target_port))
            logger.info(f"Connected to initiating Pi at {self.target_host}:{self.target_port}")
            
            while self.running:
                try:
                    data = self.mic_stream.read(self.CHUNK, exception_on_overflow=False)
                    sock.send(data)
                except Exception as e:
                    logger.error(f"Send error: {e}")
                    break
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            try:
                sock.close()
            except:
                pass
    
    def receive_audio(self):
        """Receive audio from the initiating Pi and play through speaker"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            sock.bind(('0.0.0.0', self.listen_port))
            sock.listen(1)
            logger.info(f"Listening for connection on port {self.listen_port}")
            
            conn, addr = sock.accept()
            logger.info(f"Initiating Pi connected from {addr}")
            self.target_host = addr[0]
            
            while self.running:
                try:
                    data = conn.recv(self.CHUNK * 2)
                    if not data:
                        break
                    if not self.audio_queue.full():
                        self.audio_queue.put(data)
                except Exception as e:
                    logger.error(f"Receive error: {e}")
                    break
        except Exception as e:
            logger.error(f"Listen error: {e}")
        finally:
            try:
                conn.close()
                sock.close()
            except:
                pass
    
    def play_audio(self):
        """Play received audio through speaker"""
        while self.running:
            try:
                data = self.audio_queue.get(timeout=0.1)
                self.speaker_stream.write(data)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Playback error: {e}")
                continue
    
    def start_communication(self):
        """Start audio communication threads"""
        self.running = True
        logger.info("Starting audio communication...")
        
        receive_thread = threading.Thread(target=self.receive_audio)
        play_thread = threading.Thread(target=self.play_audio)
        send_thread = threading.Thread(target=self.send_audio)
        
        receive_thread.daemon = True
        play_thread.daemon = True
        send_thread.daemon = True
        
        receive_thread.start()
        play_thread.start()
        send_thread.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping audio communication...")
            self.running = False
    
    def start(self):
        logger.info("Starting Pi audio receiver...")
        request_thread = threading.Thread(target=self.monitor_requests)
        request_thread.daemon = True
        request_thread.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping audio receiver...")
            self.running = False
        finally:
            self.mic_stream.stop_stream()
            self.speaker_stream.stop_stream()
            self.mic_stream.close()
            self.speaker_stream.close()
            self.audio.terminate()

if __name__ == "__main__":
    device_id = os.getenv('DEVICE_ID', 'pebo_rpi_1')
    user_id = os.getenv('USER_ID', 'CURRENT_USER_ID')
    node = AudioNode(listen_port=8889, target_host=None, target_port=8888, device_id=device_id, user_id=user_id)
    node.start()

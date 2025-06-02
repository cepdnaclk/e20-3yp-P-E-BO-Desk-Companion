import socket
import fcntl
import struct
import subprocess
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import logging
import os
import pyaudio
import threading
import queue

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/ipconfig/store_ip.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# AudioNode class from the provided pi_audio_node.py
class AudioNode:
    def __init__(self, listen_port=8888, target_host='192.168.1.1', target_port=8889):
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
    
    def send_audio(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            time.sleep(2)
            sock.connect((self.target_host, self.target_port))
            logger.info(f"Connected to target at {self.target_host}:{self.target_port}")
            
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
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            sock.bind(('0.0.0.0', self.listen_port))
            sock.listen(1)
            logger.info(f"Listening for connection on port {self.listen_port}")
            
            conn, addr = sock.accept()
            logger.info(f"Target connected from {addr}")
            
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
        while self.running:
            try:
                data = self.audio_queue.get(timeout=0.1)
                self.speaker_stream.write(data)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Playback error: {e}")
                continue
    
    def start(self):
        logger.info("Starting audio node...")
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
            logger.info("Stopping audio node...")
            self.running = False
        finally:
            self.mic_stream.stop_stream()
            self.speaker_stream.stop_stream()
            self.mic_stream.close()
            self.speaker_stream.close()
            self.audio.terminate()

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

# Get IP address of a network interface
def get_ip_address(ifname='wlan0'):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip = socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,
            struct.pack('256s', bytes(ifname[:15], 'utf-8'))
        )[20:24])
        return ip
    except Exception as e:
        logger.warning(f"Error getting IP address for {ifname}: {str(e)}")
        return None

# Get current Wi-Fi SSID
def get_wifi_ssid():
    try:
        result = subprocess.run(['iwgetid', '-r'], capture_output=True, text=True, timeout=5)
        ssid = result.stdout.strip()
        return ssid if ssid else None
    except subprocess.TimeoutExpired:
        logger.warning("Timeout while getting SSID")
        return None
    except Exception as e:
        logger.warning(f"Error getting SSID: {str(e)}")
        return None

# Store IP address and SSID in Firebase
def store_ip_to_firebase(user_id, device_id, ip_address, ssid):
    try:
        ref = db.reference(f'users/{user_id}/peboDevices/{device_id}')
        ref.update({
            'ipAddress': ip_address or 'Disconnected',
            'ssid': ssid or 'Unknown',
            'lastUpdated': int(time.time() * 1000)
        })
        logger.info(f"Stored IP {ip_address or 'Disconnected'} and SSID {ssid or 'Unknown'} for user {user_id}, device {device_id}")
    except Exception as e:
        logger.error(f"Error storing data to Firebase: {str(e)}")
ces' in user_data:
                for device_id, device_data in user_data['peboDevices'].items():
                    if device_data.get('ssid') == current_ssid and device_data.get('ipAddress') != 'Disconnected':
                        same_wifi_devices.append({
                            'user_id': uid,
                            'device_id': device_id,
                            'ip_address': device_data.get('ipAddress'),
                            'ssid': device_data.get('ssid')
                        })

        if not same_wifi_devices:
            logger.info(f"No devices found on SSID {current_ssid}")
            print(f"No other devices found on Wi-Fi {current_ssid}.")
            return

        print("Available PEBO devices on the same Wi-Fi:")
        for idx, device in enumerate(same_wifi_devices, 1):
            print(f"{idx}. Device: {device['device_id']} (User: {device['user_id']}, IP: {device['ip_address']})")

        choice = int(input("Enter the number of the device you want to talk to: ")) - 1
        if choice < 0 or choice >= len(same_wifi_devices):
            print("Invalid choice.")
            return

        selected_device = same_wifi_devices[choice]
        target_ip = selected_device['ip_address']
        logger.info(f"Selected device {selected_device['device_id']} with IP {target_ip} for communication")

        # Send communication request to Firebase
        request_id = f"req_{int(time.time() * 1000)}"
        requests_ref = db.reference(f'users/{selected_device["user_id"]}/communicationRequests/{request_id}')
        requests_ref.set({
            'from_device_id': device_id,
            'from_user_id': user_id,
            'to_device_id': selected_device['device_id'],
            'from_ip': current_ip,
            'status': 'pending',
            'timestamp': int(time.time() * 1000)
        })
        logger.info(f"Sent call request to {selected_device['device_id']}")

        # Wait for acceptance (simplified polling)
        while True:
            request = requests_ref.get()
            if request and request.get('status') == 'accepted':
                logger.info(f"Call request accepted by {selected_device['device_id']}")
                break
            elif request and request.get('status') == 'rejected':
                logger.info(f"Call request rejected by {selected_device['device_id']}")
                return
            time.sleep(1)

        # Start audio communication
        audio_node = AudioNode(listen_port=8888, target_host=target_ip, target_port=8889)
        audio_node.start()

    except Exception as e:
        logger.error(f"Error in interdevice communication: {str(e)}")
        print(f"Error occurred: {str(e)}")

# ... (keep rest of the code, update main to pass current_ip) ...

def main():
    # Initialize Firebase
    try:
        initialize_firebase()
    except Exception as e:
        logger.error("Exiting due to Firebase initialization failure")
        return

    user_id = os.getenv('USER_ID', 'CURRENT_USER_ID')
    device_id = os.getenv('DEVICE_ID', 'pebo_rpi_1')

    last_ip = None
    last_ssid = None

    while True:
        try:
            current_ip = get_ip_address()
            current_ssid = get_wifi_ssid()

            if current_ip and (current_ip != last_ip or current_ssid != last_ssid):
                logger.info(f"Wi-Fi change detected: IP={current_ip}, SSID={current_ssid}")
                store_ip_to_firebase(user_id, device_id, current_ip, current_ssid)
                last_ip = current_ip
                last_ssid = current_ssid
            elif not current_ip and (last_ip or last_ssid):
                logger.info("No Wi-Fi connection detected")
                store_ip_to_firebase(user_id, device_id, None, None)
                last_ip = None
                last_ssid = None

            user_input = input("Enter command (type 'call pebo' to initiate communication, 'exit' to quit): ").strip().lower()
            if user_input == 'call pebo':
                if current_ip and current_ssid:
                    initiate_interdevice_communication(user_id, current_ssid, current_ip)
                else:
                    print("Cannot initiate communication: Not connected to Wi-Fi.")
            elif user_input == 'exit':
                logger.info("Program terminated by user")
                break

            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Program terminated by user")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    main()

import socket
import fcntl
import struct
import subprocess
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/pi/store_ip.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Firebase configuration
def initialize_firebase():
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate('/path/to/your/serviceAccountKey.json')  # Update with your service account key path
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://pebo-task-manager-767f3-default-rtdb.asia-southeast1.firebasedatabase.app'
            })
            logger.info("Firebase initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise

# Get IP address of wlan0 interface
def get_ip_address(ifname='wlan0'):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip = socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', bytes(ifname[:15], 'utf-8'))
        )[20:24])
        return ip
    except Exception as e:
        logger.warning(f"Error getting IP address: {e}")
        return None

# Get current Wi-Fi SSID
def get_wifi_ssid():
    try:
        result = subprocess.run(['iwgetid', '-r'], capture_output=True, text=True, timeout=5)
        ssid = result.stdout.strip()
        return ssid if ssid else None
    except Exception as e:
        logger.warning(f"Error getting SSID: {e}")
        return None

# Store IP address in Firebase Realtime Database
def store_ip_to_firebase(user_id, device_id, ip_address, ssid):
    try:
        ref = db.reference(f'users/{user_id}/peboDevices/{device_id}')
        ref.update({
            'ipAddress': ip_address,
            'ssid': ssid or 'Unknown',
            'lastUpdated': int(time.time() * 1000)  # Timestamp in milliseconds
        })
        logger.info(f"Stored IP {ip_address} and SSID {ssid} for user {user_id}, device {device_id}")
    except Exception as e:
        logger.error(f"Error storing IP to Firebase: {e}")

def main():
    # Initialize Firebase
    try:
        initialize_firebase()
    except Exception as e:
        logger.error("Exiting due to Firebase initialization failure")
        return

    # User ID and device ID (replace with actual user ID or retrieve dynamically)
    user_id = "CURRENT_USER_ID"  # Replace with the actual user ID
    device_id = "pebo_rpi_1"    # Unique identifier for this Raspberry Pi

    # Track previous state to detect changes
    last_ip = None
    last_ssid = None

    while True:
        try:
            # Get current IP and SSID
            current_ip = get_ip_address()
            current_ssid = get_wifi_ssid()

            # Check if Wi-Fi is connected and if IP or SSID has changed
            if current_ip and (current_ip != last_ip or current_ssid != last_ssid):
                logger.info(f"Wi-Fi change detected: IP={current_ip}, SSID={current_ssid}")
                store_ip_to_firebase(user_id, device_id, current_ip, current_ssid)
                last_ip = current_ip
                last_ssid = current_ssid
            elif not current_ip:
                logger.info("No Wi-Fi connection detected")
                if last_ip or last_ssid:
                    # Clear IP in Firebase if disconnected
                    store_ip_to_firebase(user_id, device_id, None, None)
                    last_ip = None
                    last_ssid = None

            # Wait before checking again (30 seconds)
            time.sleep(30)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(60)  # Wait longer after an error to avoid spamming

if __name__ == "__main__":
    main()
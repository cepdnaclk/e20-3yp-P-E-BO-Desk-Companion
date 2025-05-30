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

# Firebase configuration
def initialize_firebase():
    """Initialize Firebase with the provided service account key."""
    if not firebase_admin._apps:
        try:
            # Use the provided service account key path
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
    """Retrieve the IP address of the specified network interface."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip = socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', bytes(ifname[:15], 'utf-8'))
        )[20:24])
        return ip
    except Exception as e:
        logger.warning(f"Error getting IP address for {ifname}: {str(e)}")
        return None

# Get current Wi-Fi SSID
def get_wifi_ssid():
    """Retrieve the current Wi-Fi SSID."""
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

# Store IP address and SSID in Firebase Realtime Database
def store_ip_to_firebase(user_id, device_id, ip_address, ssid):
    """Store IP address and SSID in Firebase for the given user and device."""
    try:
        ref = db.reference(f'users/{user_id}/peboDevices/{device_id}')
        ref.update({
            'ipAddress': ip_address or 'Disconnected',
            'ssid': ssid or 'Unknown',
            'lastUpdated': int(time.time() * 1000)  # Timestamp in milliseconds
        })
        logger.info(f"Stored IP {ip_address or 'Disconnected'} and SSID {ssid or 'Unknown'} for user {user_id}, device {device_id}")
    except Exception as e:
        logger.error(f"Error storing data to Firebase: {str(e)}")

def main():
    """Main function to monitor and upload IP address and SSID to Firebase."""
    # Initialize Firebase
    try:
        initialize_firebase()
    except Exception as e:
        logger.error("Exiting due to Firebase initialization failure")
        return

    # Get user ID and device ID from environment variables or use defaults
    user_id = os.getenv('USER_ID', 'CURRENT_USER_ID')  # Set USER_ID in environment or replace
    device_id = os.getenv('DEVICE_ID', 'pebo_rpi_1')  # Unique identifier for this Raspberry Pi

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
            elif not current_ip and (last_ip or last_ssid):
                logger.info("No Wi-Fi connection detected")
                # Clear IP and SSID in Firebase if disconnected
                store_ip_to_firebase(user_id, device_id, None, None)
                last_ip = None
                last_ssid = None

            # Wait before checking again (30 seconds)
            time.sleep(30)
        except KeyboardInterrupt:
            logger.info("Program terminated by user")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            time.sleep(60)  # Wait longer after an error to avoid spamming

if __name__ == "__main__":
    main()

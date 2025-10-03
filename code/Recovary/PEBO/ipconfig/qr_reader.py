from picamera2 import Picamera2
import pyzbar.pyzbar as pyzbar
import json
import subprocess
import time
import logging
import sys
import os
import socket
import fcntl
import struct
import numpy as np
import cv2
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/pi/pebo_qr_scanner.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Path to save the JSON file
JSON_CONFIG_PATH = "/home/pi/pebo_config.json"

# Firebase configuration
SERVICE_ACCOUNT_PATH = '/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/ipconfig/firebase_config.json'
DATABASE_URL = 'https://pebo-task-manager-767f3-default-rtdb.asia-southeast1.firebasedatabase.app'

def initialize_firebase():
    """Initialize Firebase with the provided service account key."""
    if not firebase_admin._apps:
        try:
            if not os.path.exists(SERVICE_ACCOUNT_PATH):
                logger.error(f"Service account key not found at {SERVICE_ACCOUNT_PATH}")
                raise FileNotFoundError(f"Service account key not found at {SERVICE_ACCOUNT_PATH}")
            
            cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
            firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
            logger.info("Firebase initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            raise

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
        logger.error(f"Error storing data to Firebase: {e}")

def save_to_json(data):
    """Save the QR code data to a JSON file."""
    try:
        directory = os.path.dirname(JSON_CONFIG_PATH) or '.'
        os.makedirs(directory, exist_ok=True)
        
        if not os.access(directory, os.W_OK):
            logger.error(f"Directory {directory} is not writable. Check permissions.")
            return False
        
        with open(JSON_CONFIG_PATH, 'w') as f:
            json.dump(data, f, indent=4)
        logger.info(f"Successfully saved QR code data to {JSON_CONFIG_PATH}")
        return True
    except PermissionError as e:
        logger.error(f"Permission denied when saving to {JSON_CONFIG_PATH}: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to save JSON data to {JSON_CONFIG_PATH}: {e}")
        return False

def connect_to_wifi(ssid, password):
    """Attempt to connect to a Wi-Fi network using nmcli."""
    try:
        logger.info(f"Attempting to connect to Wi-Fi SSID: {ssid}")
        subprocess.run(['nmcli', 'connection', 'delete', ssid], check=False)
        
        result = subprocess.run(
            ['nmcli', 'dev', 'wifi', 'connect', ssid, 'password', password],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info("Successfully connected to Wi-Fi")
            return True
        else:
            logger.error(f"Failed to connect to Wi-Fi: {result.stderr}")
            return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Error connecting to Wi-Fi: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during Wi-Fi connection: {e}")
        return False

def process_qr_code(data):
    """Process the decoded QR code data, save to JSON, and upload IP to Firebase."""
    try:
        # Decode JSON data from QR code
        qr_data = json.loads(data)
        logger.info(f"Decoded QR code data: {qr_data}")

        # Extract fields
        ssid = qr_data.get('ssid')
        password = qr_data.get('password')
        device_id = qr_data.get('deviceId')
        user_id = qr_data.get('userId')

        if not all([ssid, password, device_id, user_id]):
            logger.error("Missing required fields in QR code data")
            return False

        # Log device and user info
        logger.info(f"Device ID: {device_id}, User ID: {user_id}")

        # Save to JSON
        config_data = {
            "ssid": ssid,
            "password": password,
            "deviceId": device_id,
            "userId": user_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        if not save_to_json(config_data):
            logger.warning("Continuing despite failure to save JSON")

        # Connect to Wi-Fi
        if connect_to_wifi(ssid, password):
            logger.info("Wi-Fi connection successful")
            # Wait briefly to ensure network is stable
            time.sleep(5)
            # Get IP and SSID
            ip_address = get_ip_address()
            current_ssid = get_wifi_ssid()
            # Store to Firebase
            store_ip_to_firebase(user_id, device_id, ip_address, current_ssid)
            return True
        else:
            logger.error("Wi-Fi connection failed")
            return False

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in QR code: {e}")
        return False
    except Exception as e:
        logger.error(f"Error processing QR code: {e}")
        return False

def run_qr_scanner():
    """Run the QR code scanner using Picamera2 to capture and process QR codes."""
    camera = None
    try:
        # Initialize Firebase
        try:
            initialize_firebase()
        except Exception as e:
            logger.error("Exiting due to Firebase initialization failure")
            return False

        # Initialize camera
        try:
            camera = Picamera2()
            camera.configure(camera.create_preview_configuration(main={"size": (640, 480)}))
            camera.start()
            logger.info("Camera initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            return False

        qr_detected = False
        try:
            while not qr_detected:
                # Capture frame
                frame = camera.capture_array()
                if frame is None:
                    logger.error("Failed to capture frame")
                    break

                # Convert frame to grayscale for QR code detection
                gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

                # Decode QR codes in the frame
                decoded_objects = pyzbar.decode(gray)
                for obj in decoded_objects:
                    qr_data = obj.data.decode('utf-8')
                    logger.info(f"QR code detected: {qr_data}")
                    
                    # Process the QR code
                    if process_qr_code(qr_data):
                        qr_detected = True
                        logger.info("QR code processed successfully, exiting...")
                    else:
                        logger.warning("Failed to process QR code, continuing to scan...")
                    
                    # Draw rectangle around QR code
                    points = obj.polygon
                    if len(points) >= 4:
                        pts = [(point.x, point.y) for point in points]
                        cv2.polylines(frame, [np.array(pts, dtype=np.int32)], True, (0, 255, 0), 3)

                # Display the frame
                cv2.imshow('PEBO QR Scanner', frame)

                # Exit on 'q' key press
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logger.info("User terminated the scanner")
                    break

                # Small delay to prevent excessive CPU usage
                time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Scanner terminated by user")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        
        return qr_detected

    finally:
        # Ensure camera is stopped and closed
        if camera is not None:
            try:
                camera.stop()
                camera.close()
                logger.info("Camera stopped and closed")
            except Exception as e:
                logger.error(f"Error stopping/closing camera: {e}")
        try:
            cv2.destroyAllWindows()
            logger.info("OpenCV windows closed")
        except Exception as e:
            logger.error(f"Error closing OpenCV windows: {e}")
        try:
            if firebase_admin._apps:
                firebase_admin.delete_app(firebase_admin.get_app())
                logger.info("Firebase app cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up Firebase app: {e}")

if __name__ == "__main__":
    run_qr_scanner()

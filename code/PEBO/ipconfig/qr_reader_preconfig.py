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

# Fixed name for preconfigured Wi-Fi profile
PRECONFIGURED_PROFILE = "preconfigured"

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

def load_config():
    """Load existing configuration from pebo_config.json."""
    try:
        if os.path.exists(JSON_CONFIG_PATH):
            with open(JSON_CONFIG_PATH, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading config from {JSON_CONFIG_PATH}: {e}")
        return {}

def save_to_json(data):
    """Save the QR code data to a JSON file, overwriting existing SSID and password."""
    try:
        directory = os.path.dirname(JSON_CONFIG_PATH) or '.'
        os.makedirs(directory, exist_ok=True)
        
        if not os.access(directory, os.W_OK):
            logger.error(f"Directory {directory} is not writable. Check permissions.")
            return False
        
        # Load existing config to preserve other fields
        existing_config = load_config()
        # Update only ssid, password, and timestamp
        existing_config.update({
            "ssid": data.get("ssid"),
            "password": data.get("password"),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        # Ensure deviceId and userId are preserved if present
        if "deviceId" in data:
            existing_config["deviceId"] = data["deviceId"]
        if "userId" in data:
            existing_config["userId"] = data["userId"]
        
        with open(JSON_CONFIG_PATH, 'w') as f:
            json.dump(existing_config, f, indent=4)
        logger.info(f"Successfully saved updated config to {JSON_CONFIG_PATH}")
        return True
    except PermissionError as e:
        logger.error(f"Permission denied when saving to {JSON_CONFIG_PATH}: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to save JSON data to {JSON_CONFIG_PATH}: {e}")
        return False

def delete_all_wifi_connections(exclude_profile=PRECONFIGURED_PROFILE):
    """Delete all Wi-Fi connection profiles except the specified profile."""
    try:
        # List all connection profiles
        result = subprocess.run(['nmcli', '--terse', '--fields', 'NAME,TYPE', 'connection', 'show'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Failed to list connections: {result.stderr}")
            return False
        
        connections = result.stdout.strip().split('\n')
        wifi_connections = [conn.split(':')[0] for conn in connections if conn and ':802-11-wireless' in conn]
        
        # Delete each Wi-Fi connection except the excluded profile
        for conn in wifi_connections:
            if conn == exclude_profile:
                logger.info(f"Preserving preconfigured Wi-Fi connection: {conn}")
                continue
            try:
                subprocess.run(['nmcli', 'connection', 'delete', conn], check=True)
                logger.info(f"Deleted Wi-Fi connection: {conn}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to delete connection {conn}: {e}")
        
        logger.info("All non-excluded Wi-Fi connections deleted successfully")
        return True
    except Exception as e:
        logger.error(f"Error deleting Wi-Fi connections: {e}")
        return False

def connect_to_wifi(ssid, password, temp_profile="temp-qr-wifi"):
    """Connect to the specified Wi-Fi network using a temporary profile."""
    try:
        logger.info(f"Attempting to connect to Wi-Fi SSID: {ssid} using temporary profile")
        # Create a temporary connection profile
        result = subprocess.run(
            ['nmcli', 'connection', 'add', 'type', 'wifi', 'con-name', temp_profile, 
             'ssid', ssid, 'wifi-sec.key-mgmt', 'wpa-psk', 'wifi-sec.psk', password],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.error(f"Failed to create temporary connection profile for SSID {ssid}: {result.stderr}")
            return False
        
        # Connect to the temporary Wi-Fi profile
        result = subprocess.run(['nmcli', 'connection', 'up', temp_profile], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("Successfully connected to temporary Wi-Fi")
            return True
        else:
            logger.error(f"Failed to connect to Wi-Fi: {result.stderr}")
            # Delete the temporary profile on failure
            subprocess.run(['nmcli', 'connection', 'delete', temp_profile], check=False)
            return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Error connecting to Wi-Fi: {e}")
        subprocess.run(['nmcli', 'connection', 'delete', temp_profile], check=False)
        return False
    except Exception as e:
        logger.error(f"Unexpected error during Wi-Fi connection: {e}")
        subprocess.run(['nmcli', 'connection', 'delete', temp_profile], check=False)
        return False

def update_preconfigured_wifi(ssid, password):
    """Update or create the preconfigured Wi-Fi profile."""
    try:
        logger.info(f"Updating/creating preconfigured Wi-Fi profile for SSID: {ssid}")
        # Check if the preconfigured profile exists
        result = subprocess.run(['nmcli', 'connection', 'show', PRECONFIGURED_PROFILE], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            # Update existing preconfigured profile
            logger.info(f"Updating preconfigured profile: {PRECONFIGURED_PROFILE}")
            subprocess.run(['nmcli', 'connection', 'modify', PRECONFIGURED_PROFILE, 
                           'wifi.ssid', ssid, 'wifi-sec.psk', password], check=True)
        else:
            # Create new preconfigured profile
            logger.info(f"Creating new preconfigured profile: {PRECONFIGURED_PROFILE}")
            subprocess.run(
                ['nmcli', 'connection', 'add', 'type', 'wifi', 'con-name', PRECONFIGURED_PROFILE, 
                 'ssid', ssid, 'wifi-sec.key-mgmt', 'wpa-psk', 'wifi-sec.psk', password],
                capture_output=True, text=True
            )
        
        # Connect to the preconfigured Wi-Fi
        result = subprocess.run(['nmcli', 'connection', 'up', PRECONFIGURED_PROFILE], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("Successfully connected to preconfigured Wi-Fi")
            return True
        else:
            logger.error(f"Failed to connect to preconfigured Wi-Fi: {result.stderr}")
            return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Error updating/connecting to preconfigured Wi-Fi: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during preconfigured Wi-Fi update: {e}")
        return False

def process_qr_code(data):
    """Process the decoded QR code data, connect to new Wi-Fi, update preconfigured Wi-Fi, and clean up."""
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

        # Connect to the new Wi-Fi using a temporary profile
        temp_profile = "temp-qr-wifi"
        if not connect_to_wifi(ssid, password, temp_profile=temp_profile):
            logger.error("Failed to connect to new Wi-Fi, aborting")
            return False

        # Delete all Wi-Fi connections except the preconfigured profile
        if not delete_all_wifi_connections(exclude_profile=PRECONFIGURED_PROFILE):
            logger.warning("Failed to delete non-excluded Wi-Fi connections, proceeding anyway")

        # Delete the temporary profile
        subprocess.run(['nmcli', 'connection', 'delete', temp_profile], check=False)
        logger.info(f"Deleted temporary Wi-Fi profile: {temp_profile}")

        # Save updated config to JSON
        config_data = {
            "ssid": ssid,
            "password": password,
            "deviceId": device_id,
            "userId": user_id
        }
        if not save_to_json(config_data):
            logger.warning("Continuing despite failure to save JSON")

        # Update and connect to the preconfigured Wi-Fi
        if update_preconfigured_wifi(ssid, password):
            logger.info("Preconfigured Wi-Fi updated and connected successfully")
            # Wait briefly to ensure network is stable
            time.sleep(5)
            # Get IP and SSID
            ip_address = get_ip_address()
            current_ssid = get_wifi_ssid()
            # Store to Firebase
            store_ip_to_firebase(user_id, device_id, ip_address, current_ssid)
            return True
        else:
            logger.error("Failed to update/connect to preconfigured Wi-Fi")
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
        if camera is None:
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

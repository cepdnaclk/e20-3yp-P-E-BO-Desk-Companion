from picamera2 import Picamera2
import pyzbar.pyzbar as pyzbar
import json
import subprocess
import time
import logging
import sys
import os
import numpy as np
import cv2  # Still needed for displaying frames and drawing QR code rectangles

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

def save_to_json(data):
    """Save the QR code data to a JSON file."""
    try:
        # Ensure the directory exists
        directory = os.path.dirname(JSON_CONFIG_PATH) or '.'
        os.makedirs(directory, exist_ok=True)
        
        # Check if the directory is writable
        if not os.access(directory, os.W_OK):
            logger.error(f"Directory {directory} is not writable. Check permissions.")
            return False
        
        # Write data to JSON file
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
        # Delete existing connection if it exists to avoid conflicts
        subprocess.run(['nmcli', 'connection', 'delete', ssid], check=False)
        
        # Add and connect to the Wi-Fi network
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
    """Process the decoded QR code data and save to JSON."""
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

def main():
    """Main function to capture video and scan QR codes using Picamera2."""
    # Initialize camera
    try:
        camera = Picamera2()
        camera.configure(camera.create_preview_configuration(main={"size": (640, 480)}))
        camera.start()
        logger.info("Camera initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize camera: {e}")
        return

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
    finally:
        camera.stop()
        cv2.destroyAllWindows()
        logger.info("Camera stopped and windows closed")

if __name__ == "__main__":
    main()

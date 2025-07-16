#!/usr/bin/env python3
"""
Combined face tracking with photo capture and QR code scanning for Wi-Fi connection.
Captures and saves cropped face image as captured.jpg.enc (encrypted) when a person is detected.
Connects to Wi-Fi from QR code, deletes other profiles except 'preconfigured' if connection succeeds.
Face tracking continues during and after QR code processing.
"""

import cv2
import mediapipe as mp
from picamera2 import Picamera2
import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
import threading
import queue
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
import pyzbar.pyzbar as pyzbar
import json
import subprocess
import socket
import fcntl
import struct
import numpy as np
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

class CombinedFaceTracking:
    # Fixed name for preconfigured Wi-Fi profile (defined at class level)
    PRECONFIGURED_PROFILE = "preconfigured"

    def __init__(self):
        # Setup I2C and PCA9685 PWM controller
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.pwm = PCA9685(self.i2c)
        self.pwm.frequency = 50  # Standard servo frequency (50Hz)
        
        # Setup servos
        self.h_servo_channel = 7
        self.v_servo_channel = 6
        self.center_servo_channel = 5
        
        self.h_servo = servo.Servo(self.pwm.channels[self.h_servo_channel])
        self.v_servo = servo.Servo(self.pwm.channels[self.v_servo_channel])
        self.center_servo = servo.Servo(self.pwm.channels[self.center_servo_channel])
        
        # Initialize camera
        self.picam2 = Picamera2()
        self.picam2.configure(self.picam2.create_video_configuration(main={"size": (640, 480)}))
        self.picam2.start()
        
        # Initialize MediaPipe
        self.mp_face = mp.solutions.face_detection.FaceDetection(
            model_selection=0, 
            min_detection_confidence=0.6
        )
        
        # Frame dimensions
        self.width, self.height = 640, 480
        
        # Minimum face size threshold
        self.min_face_area_percent = 3.0
        
        # Shared variables with locks
        self.face_data_lock = threading.Lock()
        self.qr_data_lock = threading.Lock()
        self.shared_face_data = None
        self.last_detection_time = time.time()
        self.qr_processed = False  # Flag to process QR code only once
        
        # Control flags
        self.running = True
        self.frame_queue = queue.Queue(maxsize=2)
        
        # Dual servo parameters
        self.h_partition_angles = {1: 110, 2: 105, 3: 100, 4: 80, 5: 60, 6: 55, 7: 50}
        self.v_partition_angles = {1: 130, 2: 110, 3: 95}
        self.h_partition_boundaries = [(0, 70, 1), (90, 160, 2), (180, 250, 3), (270, 370, 4),
                                       (390, 460, 5), (480, 550, 6), (570, 640, 7)]
        self.v_partition_boundaries = [(0, 120, 1), (170, 290, 2), (340, 480, 3)]
        
        self.h_current_angle = 80
        self.v_current_angle = 100
        self.h_current_partition = 4
        self.v_current_partition = 2
        
        # Center servo parameters
        self.center_current_angle = 90
        self.center_target_angle = 90
        self.center_zone_width = 90
        self.center_zone_left = (self.width // 2) - (self.center_zone_width // 2)
        self.center_zone_right = (self.width // 2) + (self.center_zone_width // 2)
        self.center_kp = 0.1
        self.direction_multiplier = 1
        
        # Photo capture parameters
        self.last_capture_time = time.time()
        self.capture_interval = 5.0

        # Encryption setup
        aes_key = os.getenv("AES_KEY")
        print(f"DEBUG: AES_KEY from env: {aes_key}")
        if not aes_key:
            key_file = "/home/pi/.pebo_key"
            if os.path.exists(key_file):
                print(f"Reading AES_KEY from {key_file}")
                with open(key_file, 'r') as f:
                    aes_key = f.read().strip()
            else:
                print("⚠️ AES_KEY not set. Generating temporary key (not persisted).")
                self.key = os.urandom(32)
                print("Set AES_KEY environment variable or create /home/pi/.pebo_key for persistent encryption.")
                return
        try:
            if isinstance(aes_key, bytes):
                aes_key_bytes = aes_key
            else:
                aes_key_bytes = aes_key.encode()
            self.key = base64.b64decode(aes_key_bytes)
            if len(self.key) != 32:
                raise ValueError("AES key must be 32 bytes")
        except Exception as e:
            raise ValueError(f"Invalid AES key: {e}")

        # Wi-Fi configuration
        self.JSON_CONFIG_PATH = "/home/pi/pebo_config.json"
        self.SERVICE_ACCOUNT_PATH = '/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/ipconfig/firebase_config.json'
        self.DATABASE_URL = 'https://pebo-task-manager-767f3-default-rtdb.asia-southeast1.firebasedatabase.app'
        
        # Initialize Firebase
        self.initialize_firebase()

    def initialize_firebase(self):
        """Initialize Firebase with the provided service account key."""
        if not firebase_admin._apps:
            try:
                if not os.path.exists(self.SERVICE_ACCOUNT_PATH):
                    print(f"Service account key not found at {self.SERVICE_ACCOUNT_PATH}")
                    raise FileNotFoundError(f"Service account key not found at {self.SERVICE_ACCOUNT_PATH}")
                
                cred = credentials.Certificate(self.SERVICE_ACCOUNT_PATH)
                firebase_admin.initialize_app(cred, {'databaseURL': self.DATABASE_URL})
                print("Firebase initialized successfully")
            except Exception as e:
                print(f"Failed to initialize Firebase: {str(e)}")
                raise

    def get_ip_address(self, ifname='wlan0'):
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
            print(f"Error getting IP address for {ifname}: {str(e)}")
            return None

    def get_wifi_ssid(self):
        """Retrieve the current Wi-Fi SSID."""
        try:
            result = subprocess.run(['iwgetid', '-r'], capture_output=True, text=True, timeout=5)
            ssid = result.stdout.strip()
            return ssid if ssid else None
        except subprocess.TimeoutExpired:
            print("Timeout while getting SSID")
            return None
        except Exception as e:
            print(f"Error getting SSID: {str(e)}")
            return None

    def store_ip_to_firebase(self, user_id, device_id, ip_address, ssid):
        """Store IP address and SSID in Firebase for the given user and device."""
        try:
            ref = db.reference(f'users/{user_id}/peboDevices/{device_id}')
            ref.update({
                'ipAddress': ip_address or 'Disconnected',
                'ssid': ssid or 'Unknown',
                'lastUpdated': int(time.time() * 1000)  # Timestamp in milliseconds
            })
            print(f"Stored IP {ip_address or 'Disconnected'} and SSID {ssid or 'Unknown'} for user {user_id}, device {device_id}")
        except Exception as e:
            print(f"Error storing data to Firebase: {e}")

    def load_config(self):
        """Load existing configuration from pebo_config.json."""
        try:
            if os.path.exists(self.JSON_CONFIG_PATH):
                with open(self.JSON_CONFIG_PATH, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading config from {self.JSON_CONFIG_PATH}: {e}")
            return {}

    def save_to_json(self, data):
        """Save the QR code data to a JSON file, overwriting existing SSID and password."""
        try:
            directory = os.path.dirname(self.JSON_CONFIG_PATH) or '.'
            os.makedirs(directory, exist_ok=True)
            
            if not os.access(directory, os.W_OK):
                print(f"Directory {directory} is not writable. Check permissions.")
                return False
            
            # Load existing config to preserve other fields
            existing_config = self.load_config()
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
            
            with open(self.JSON_CONFIG_PATH, 'w') as f:
                json.dump(existing_config, f, indent=4)
            print(f"Successfully saved updated config to {self.JSON_CONFIG_PATH}")
            return True
        except PermissionError as e:
            print(f"Permission denied when saving to {self.JSON_CONFIG_PATH}: {e}")
            return False
        except Exception as e:
            print(f"Failed to save JSON data to {self.JSON_CONFIG_PATH}: {e}")
            return False

    def delete_all_wifi_connections(self, exclude_profile=PRECONFIGURED_PROFILE):
        """Delete all Wi-Fi connection profiles except the specified profile."""
        try:
            # List all connection profiles
            result = subprocess.run(['nmcli', '--terse', '--fields', 'NAME,TYPE', 'connection', 'show'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Failed to list connections: {result.stderr}")
                return False
            
            connections = result.stdout.strip().split('\n')
            wifi_connections = [conn.split(':')[0] for conn in connections if conn and ':802-11-wireless' in conn]
            
            # Delete each Wi-Fi connection except the excluded profile
            for conn in wifi_connections:
                if conn == exclude_profile:
                    print(f"Preserving preconfigured Wi-Fi connection: {conn}")
                    continue
                try:
                    subprocess.run(['nmcli', 'connection', 'delete', conn], check=True)
                    print(f"Deleted Wi-Fi connection: {conn}")
                except subprocess.CalledProcessError as e:
                    print(f"Failed to delete connection {conn}: {e}")
            
            print("All non-excluded Wi-Fi connections deleted successfully")
            return True
        except Exception as e:
            print(f"Error deleting Wi-Fi connections: {e}")
            return False

    def connect_to_wifi(self, ssid, password, temp_profile="temp-qr-wifi"):
        """Connect to the specified Wi-Fi network using a temporary profile."""
        try:
            print(f"Attempting to connect to Wi-Fi SSID: {ssid} using temporary profile")
            # Create a temporary connection profile
            result = subprocess.run(
                ['nmcli', 'connection', 'add', 'type', 'wifi', 'con-name', temp_profile, 
                 'ssid', ssid, 'wifi-sec.key-mgmt', 'wpa-psk', 'wifi-sec.psk', password],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                print(f"Failed to create temporary connection profile for SSID {ssid}: {result.stderr}")
                return False
            
            # Connect to the temporary Wi-Fi profile
            result = subprocess.run(['nmcli', 'connection', 'up', temp_profile], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("Successfully connected to temporary Wi-Fi")
                return True
            else:
                print(f"Failed to connect to Wi-Fi: {result.stderr}")
                # Delete the temporary profile on failure
                subprocess.run(['nmcli', 'connection', 'delete', temp_profile], check=False)
                return False
        except subprocess.CalledProcessError as e:
            print(f"Error connecting to Wi-Fi: {e}")
            subprocess.run(['nmcli', 'connection', 'delete', temp_profile], check=False)
            return False
        except Exception as e:
            print(f"Unexpected error during Wi-Fi connection: {e}")
            subprocess.run(['nmcli', 'connection', 'delete', temp_profile], check=False)
            return False

    def update_preconfigured_wifi(self, ssid, password):
        """Update or create the preconfigured Wi-Fi profile."""
        try:
            print(f"Updating/creating preconfigured Wi-Fi profile for SSID: {ssid}")
            # Check if the preconfigured profile exists
            result = subprocess.run(['nmcli', 'connection', 'show', self.PRECONFIGURED_PROFILE], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                # Update existing preconfigured profile
                print(f"Updating preconfigured profile: {self.PRECONFIGURED_PROFILE}")
                subprocess.run(['nmcli', 'connection', 'modify', self.PRECONFIGURED_PROFILE, 
                               'wifi.ssid', ssid, 'wifi-sec.psk', password], check=True)
            else:
                # Create new preconfigured profile
                print(f"Creating new preconfigured profile: {self.PRECONFIGURED_PROFILE}")
                subprocess.run(
                    ['nmcli', 'connection', 'add', 'type', 'wifi', 'con-name', self.PRECONFIGURED_PROFILE, 
                     'ssid', ssid, 'wifi-sec.key-mgmt', 'wpa-psk', 'wifi-sec.psk', password],
                    capture_output=True, text=True
                )
            
            # Connect to the preconfigured Wi-Fi
            result = subprocess.run(['nmcli', 'connection', 'up', self.PRECONFIGURED_PROFILE], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("Successfully connected to preconfigured Wi-Fi")
                return True
            else:
                print(f"Failed to connect to preconfigured Wi-Fi: {result.stderr}")
                return False
        except subprocess.CalledProcessError as e:
            print(f"Error updating/connecting to preconfigured Wi-Fi: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error during preconfigured Wi-Fi update: {e}")
            return False

    def encrypt_image(self, input_path, output_path):
        """Encrypt the captured image and save it."""
        try:
            aesgcm = AESGCM(self.key)
            with open(input_path, 'rb') as f:
                data = f.read()
            nonce = os.urandom(12)
            ciphertext = aesgcm.encrypt(nonce, data, None)
            with open(output_path, 'wb') as f:
                f.write(nonce + ciphertext)
            print("********Encrypted********")
            os.remove(input_path)
        except Exception as e:
            print(f"Encryption error: {e}")

    def get_nearest_face(self, detections):
        """Find the largest face that meets the minimum area threshold."""
        if not detections:
            return None
        min_area = (self.width * self.height) * (self.min_face_area_percent / 100.0)
        largest_area = 0
        nearest_face = None
        for detection in detections:
            bbox = detection.location_data.relative_bounding_box
            x = int(bbox.xmin * self.width)
            y = int(bbox.ymin * self.height)
            w = int(bbox.width * self.width)
            h = int(bbox.height * self.height)
            area = w * h
            if area >= min_area and area > largest_area:
                largest_area = area
                nearest_face = {
                    'detection': detection,
                    'bbox': (x, y, w, h),
                    'center': (x + w // 2, y + h // 2),
                    'area': area
                }
        return nearest_face

    def process_qr_code(self, qr_data):
        """Process the QR code data, connect to Wi-Fi, and update preconfigured profile."""
        try:
            with self.qr_data_lock:
                if self.qr_processed:
                    return False
                self.qr_processed = True  # Mark QR as processed

            # Decode JSON data from QR code
            qr_data = json.loads(qr_data)
            print(f"Decoded QR code data: {qr_data}")

            # Extract fields
            ssid = qr_data.get('ssid')
            password = qr_data.get('password')
            device_id = qr_data.get('deviceId')
            user_id = qr_data.get('userId')

            if not all([ssid, password, device_id, user_id]):
                print("Missing required fields in QR code data")
                return False

            # Log device and user info
            print(f"Device ID: {device_id}, User ID: {user_id}")

            # Connect to the new Wi-Fi using a temporary profile
            temp_profile = "temp-qr-wifi"
            if not self.connect_to_wifi(ssid, password, temp_profile=temp_profile):
                print("Failed to connect to new Wi-Fi, remaining on previous network")
                return False

            # Delete all Wi-Fi connections except the preconfigured profile
            if not self.delete_all_wifi_connections(exclude_profile=self.PRECONFIGURED_PROFILE):
                print("Failed to delete non-excluded Wi-Fi connections, proceeding anyway")

            # Delete the temporary profile
            subprocess.run(['nmcli', 'connection', 'delete', temp_profile], check=False)
            print(f"Deleted temporary Wi-Fi profile: {temp_profile}")

            # Save updated config to JSON
            config_data = {
                "ssid": ssid,
                "password": password,
                "deviceId": device_id,
                "userId": user_id
            }
            if not self.save_to_json(config_data):
                print("Continuing despite failure to save JSON")

            # Update and connect to the preconfigured Wi-Fi
            if self.update_preconfigured_wifi(ssid, password):
                print("Preconfigured Wi-Fi updated and connected successfully")
                # Wait briefly to ensure network is stable
                time.sleep(5)
                # Get IP and SSID
                ip_address = self.get_ip_address()
                current_ssid = self.get_wifi_ssid()
                # Store to Firebase
                self.store_ip_to_firebase(user_id, device_id, ip_address, current_ssid)
                return True
            else:
                print("Failed to update/connect to preconfigured Wi-Fi")
                return False

        except json.JSONDecodeError as e:
            print(f"Invalid JSON in QR code: {e}")
            return False
        except Exception as e:
            print(f"Error processing QR code: {e}")
            return False
        finally:
            with self.qr_data_lock:
                self.qr_processed = False  # Reset for next QR scan

    def face_detection_thread(self):
        """Detect faces and QR codes in frames."""
        while self.running:
            try:
                frame = self.picam2.capture_array()
                frame = cv2.resize(frame, (self.width, self.height))
                frame = cv2.rotate(frame, cv2.ROTATE_180)
                image_input = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Face detection
                results = self.mp_face.process(image_input)
                nearest_face = None
                if results.detections:
                    nearest_face = self.get_nearest_face(results.detections)
                with self.face_data_lock:
                    self.shared_face_data = nearest_face
                    if nearest_face:
                        self.last_detection_time = time.time()
                
                # QR code detection
                gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                decoded_objects = pyzbar.decode(gray)
                qr_data = None
                if decoded_objects:
                    qr_data = decoded_objects[0].data.decode('utf-8')
                    print(f"QR code detected: {qr_data}")
                    self.process_qr_code(qr_data)
                
                # Add frame to queue for display
                if not self.frame_queue.full():
                    self.frame_queue.put((frame, results.detections, nearest_face, decoded_objects))
                time.sleep(0.01)
            except Exception as e:
                print(f"Face/QR detection error: {e}")
                time.sleep(0.1)

    def dual_servo_thread(self):
        """Control dual servos for face tracking."""
        face_timeout = 2.0
        def set_angle_smooth_fast(servo_obj, current_angle, target_angle, step=2):
            if current_angle == target_angle:
                return current_angle
            direction = 1 if target_angle > current_angle else -1
            for angle in range(current_angle, target_angle + direction, direction):
                servo_obj.angle = angle
                time.sleep(0.01)
            servo_obj.angle = target_angle
            time.sleep(0.01)
            return target_angle
        def get_partition(position, boundaries):
            for start, end, partition in boundaries:
                if start <= position <= end:
                    return partition, False
            return None, True
        self.h_current_angle = set_angle_smooth_fast(self.h_servo, 80, self.h_current_angle)
        self.v_current_angle = set_angle_smooth_fast(self.v_servo, 110, self.v_current_angle)
        while self.running:
            try:
                current_time = time.time()
                with self.face_data_lock:
                    face_data = self.shared_face_data
                    last_detection = self.last_detection_time
                if face_data:
                    cx, cy = face_data['center']
                    h_partition, h_in_gap = get_partition(cx, self.h_partition_boundaries)
                    v_partition, v_in_gap = get_partition(cy, self.v_partition_boundaries)
                    if not h_in_gap and h_partition != self.h_current_partition:
                        h_target_angle = self.h_partition_angles[h_partition]
                        self.h_current_angle = set_angle_smooth_fast(self.h_servo, self.h_current_angle, h_target_angle)
                        self.h_current_partition = h_partition
                    if not v_in_gap and v_partition != self.v_current_partition:
                        v_target_angle = self.v_partition_angles[v_partition]
                        self.v_current_angle = set_angle_smooth_fast(self.v_servo, self.v_current_angle, v_target_angle)
                        self.v_current_partition = v_partition
                elif current_time - last_detection > face_timeout:
                    if self.h_current_angle != 80 or self.v_current_angle != 110:
                        self.h_current_angle = set_angle_smooth_fast(self.h_servo, self.h_current_angle, 80)
                        self.v_current_angle = set_angle_smooth_fast(self.v_servo, self.v_current_angle, 110)
                        self.h_current_partition = 4
                        self.v_current_partition = 2
                time.sleep(0.01)
            except Exception as e:
                print(f"Dual servo error: {e}")
                time.sleep(0.1)

    def center_servo_thread(self):
        """Control center servo for fine face tracking."""
        face_timeout = 5.0
        def set_angle_smooth_slow(servo_obj, current_angle, target_angle, step=2):
            if abs(current_angle - target_angle) < step:
                servo_obj.angle = target_angle
                return target_angle
            direction = 1 if target_angle > current_angle else -1
            new_angle = current_angle + (direction * step)
            servo_obj.angle = new_angle
            return new_angle
        self.center_servo.angle = self.center_current_angle
        while self.running:
            try:
                current_time = time.time()
                with self.face_data_lock:
                    face_data = self.shared_face_data
                    last_detection = self.last_detection_time
                if face_data:
                    face_center_x, _ = face_data['center']
                    center_x = self.width // 2
                    face_centered = self.center_zone_left <= face_center_x <= self.center_zone_right
                    if not face_centered:
                        error = center_x - face_center_x
                        adjustment = self.center_kp * error * self.direction_multiplier
                        self.center_target_angle = self.center_current_angle + adjustment
                        self.center_target_angle = max(0, min(180, self.center_target_angle))
                elif current_time - last_detection > face_timeout:
                    self.center_target_angle = 90
                if self.center_current_angle != self.center_target_angle:
                    self.center_current_angle = set_angle_smooth_slow(
                        self.center_servo, self.center_current_angle, self.center_target_angle
                    )
                time.sleep(0.1)
            except Exception as e:
                print(f"Center servo error: {e}")
                time.sleep(0.1)

    def display_thread(self):
        """Display frames with face and QR code annotations."""
        while self.running:
            try:
                if not self.frame_queue.empty():
                    frame, detections, nearest_face, qr_codes = self.frame_queue.get()
                    current_time = time.time()
                    if nearest_face and (current_time - self.last_capture_time) >= self.capture_interval:
                        x, y, w, h = nearest_face['bbox']
                        margin_x = int(w * 0.2)
                        margin_y = int(h * 0.2)
                        x1 = max(0, x - margin_x)
                        y1 = max(0, y - margin_y)
                        x2 = min(self.width, x + w + margin_x)
                        y2 = min(self.height, y + h + margin_y)
                        cropped_face = frame[y1:y2, x1:x2]
                        new_width = int(cropped_face.shape[1] * 1.5)
                        new_height = int(cropped_face.shape[0] * 1.5)
                        resized_face = cv2.resize(cropped_face, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
                        temp_path = '/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/temp_captured.jpg'
                        output_path = '/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/captured.jpg.enc'
                        cv2.imwrite(temp_path, resized_face)
                        self.encrypt_image(temp_path, output_path)
                        print(f"Captured and encrypted face at {time.ctime()}")
                        self.last_capture_time = current_time
                    if nearest_face:
                        x, y, w, h = nearest_face['bbox']
                        cx, cy = nearest_face['center']
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
                        area_text = f"Area: {nearest_face['area']:.0f}px²"
                        cv2.putText(frame, area_text, (x, y - 10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                        face_centered = self.center_zone_left <= cx <= self.center_zone_right
                        status_text = "CENTERED" if face_centered else "NOT CENTERED"
                        status_color = (0, 255, 0) if face_centered else (0, 0, 255)
                        cv2.putText(frame, status_text, (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
                        if detections:
                            for detection in detections:
                                if detection != nearest_face['detection']:
                                    bbox = detection.location_data.relative_bounding_box
                                    other_x = int(bbox.xmin * self.width)
                                    other_y = int(bbox.ymin * self.height)
                                    other_w = int(bbox.width * self.width)
                                    other_h = int(bbox.height * self.height)
                                    cv2.rectangle(frame, (other_x, other_y), 
                                                (other_x + other_w, other_y + other_h), 
                                                (0, 0, 255), 1)
                    else:
                        cv2.putText(frame, "No qualifying faces", (10, 70),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                    # Draw QR code rectangles
                    for qr in qr_codes:
                        points = qr.polygon
                        if len(points) >= 4:
                            pts = [(point.x, point.y) for point in points]
                            cv2.polylines(frame, [np.array(pts, dtype=np.int32)], True, (255, 255, 0), 3)
                    cv2.putText(frame, f"Dual H: {self.h_current_angle}°, P: {self.h_current_partition}",
                                (self.width - 300, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                    cv2.putText(frame, f"Dual V: {self.v_current_angle}°, P: {self.v_current_partition}",
                                (self.width - 300, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                    cv2.putText(frame, f"Center: {self.center_current_angle:.1f}°",
                                (self.width - 200, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                    direction_text = "Normal" if self.direction_multiplier == 1 else "Reversed"
                    cv2.putText(frame, f"Direction: {direction_text}",
                                (self.width - 200, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                    cv2.putText(frame, "Combined Face Tracking & QR", (self.width//2 - 150, self.height - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.imshow("Combined Face Tracking & QR", frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == 27:
                        self.running = False
                        break
                    elif key == ord('+'):
                        self.min_face_area_percent += 0.5
                        print(f"Min face area: {self.min_face_area_percent:.1f}%")
                    elif key == ord('-'):
                        self.min_face_area_percent = max(0.5, self.min_face_area_percent - 0.5)
                        print(f"Min face area: {self.min_face_area_percent:.1f}%")
                    elif key == ord('r'):
                        self.direction_multiplier *= -1
                time.sleep(0.03)
            except Exception as e:
                print(f"Display error: {e}")
                time.sleep(0.1)

    def stop_servo(self, servo_channel):
        """De-energize a servo channel."""
        try:
            self.pwm.channels[servo_channel].duty_cycle = 0
            print(f"Servo channel {servo_channel} de-energized")
        except Exception as e:
            print(f"Error stopping servo channel {servo_channel}: {e}")

    def cleanup(self):
        """Clean up servos, camera, and Firebase."""
        print("Returning servos to safe positions...")
        try:
            def set_angle_smooth(servo_obj, current_angle, target_angle, step=2):
                if current_angle == target_angle:
                    return
                direction = 1 if target_angle > current_angle else -1
                for angle in range(current_angle, target_angle + direction, direction):
                    servo_obj.angle = angle
                    time.sleep(0.02)
                servo_obj.angle = target_angle
            set_angle_smooth(self.h_servo, int(self.h_current_angle), 80)
            set_angle_smooth(self.v_servo, int(self.v_current_angle), 110)
            set_angle_smooth(self.center_servo, int(self.center_current_angle), 90)
            time.sleep(1.0)
            self.stop_servo(self.h_servo_channel)
            self.stop_servo(self.v_servo_channel)
            self.stop_servo(self.center_servo_channel)
        except Exception as e:
            print(f"Error during servo cleanup: {e}")
        try:
            self.pwm.deinit()
            self.i2c.deinit()
            print("PWM and I2C de-initialized")
        except Exception as e:
            print(f"Error de-initializing PWM/I2C: {e}")
        try:
            cv2.destroyAllWindows()
            self.picam2.stop()
            print("Camera and display cleaned up")
        except Exception as e:
            print(f"Error cleaning up camera/display: {e}")
        try:
            if firebase_admin._apps:
                firebase_admin.delete_app(firebase_admin.get_app())
                print("Firebase app cleaned up")
        except Exception as e:
            print(f"Error cleaning up Firebase app: {e}")
        print("Cleanup complete")

    def run(self):
        """Start all threads for face tracking and QR scanning."""
        threads = [
            threading.Thread(target=self.face_detection_thread, daemon=True),
            threading.Thread(target=self.dual_servo_thread, daemon=True),
            threading.Thread(target=self.center_servo_thread, daemon=True),
            threading.Thread(target=self.display_thread, daemon=True)
        ]
        for thread in threads:
            thread.start()
        try:
            threads[3].join()
        except KeyboardInterrupt:
            print("Program interrupted by user")
        finally:
            self.running = False
            self.cleanup()

if __name__ == "__main__":
    tracker = CombinedFaceTracking()
    tracker.run()

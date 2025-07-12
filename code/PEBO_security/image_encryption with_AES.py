import cv2
import mediapipe as mp
import RPi.GPIO as GPIO
from picamera2 import Picamera2
import time
import os
import io
import json
from datetime import datetime
from PIL import Image
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from base64 import b64encode, b64decode
import hashlib

# Configuration
SECURE_FOLDER = "/home/pi/encrypted_images"
MASTER_PASSWORD = "your_secure_password"  # Change this!
CAPTURE_KEY = ord('c')
DECRYPT_KEY = ord('v')  # 'v' for view
LIST_KEY = ord('l')

# Create secure folder
if not os.path.exists(SECURE_FOLDER):
    os.makedirs(SECURE_FOLDER)

class SecureImageManager:
    def __init__(self):
        self.master_key = self._derive_master_key(MASTER_PASSWORD)
    
    def _derive_master_key(self, password):
        """Derive a master key from password using PBKDF2"""
        salt = b'robot_salt_2024'  # In production, use random salt per user
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)[:32]
    
    def encrypt_image_from_array(self, image_array):
        """
        Encrypts an OpenCV image array using AES-256-CBC
        
        Args:
            image_array: OpenCV image array (numpy array)
            
        Returns:
            (encrypted_data, iv, metadata): Encrypted data and parameters
        """
        # Convert OpenCV array to PIL Image
        image_rgb = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        
        # Convert image to bytes
        img_bytes = io.BytesIO()
        pil_image.save(img_bytes, format='JPEG', quality=90)
        raw_data = img_bytes.getvalue()
        
        # Generate random IV for this image
        iv = get_random_bytes(16)
        
        # Create cipher and encrypt
        cipher = AES.new(self.master_key, AES.MODE_CBC, iv)
        encrypted_data = cipher.encrypt(pad(raw_data, AES.block_size))
        
        # Create metadata
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'size': len(raw_data),
            'encrypted_size': len(encrypted_data),
            'algorithm': 'AES-256-CBC'
        }
        
        return encrypted_data, iv, metadata
    
    def decrypt_image(self, encrypted_data, iv):
        """
        Decrypts image data back to PIL Image
        
        Args:
            encrypted_data: The encrypted image data
            iv: The initialization vector
            
        Returns:
            PIL Image object
        """
        try:
            # Create cipher and decrypt
            cipher = AES.new(self.master_key, AES.MODE_CBC, iv)
            decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
            
            # Convert back to image
            img = Image.open(io.BytesIO(decrypted_data))
            return img
        except Exception as e:
            print(f"Decryption failed: {e}")
            return None
    
    def save_encrypted_image(self, image_array, face_detected=False):
        """Save encrypted image with metadata"""
        timestamp = datetime.now()
        base_filename = f"secure_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        # Encrypt the image
        encrypted_data, iv, metadata = self.encrypt_image_from_array(image_array)
        
        # Add additional metadata
        metadata.update({
            'face_detected': face_detected,
            'filename': base_filename
        })
        
        # Save encrypted image data
        encrypted_file = os.path.join(SECURE_FOLDER, f"{base_filename}.enc")
        with open(encrypted_file, 'wb') as f:
            f.write(encrypted_data)
        
        # Save IV (initialization vector)
        iv_file = os.path.join(SECURE_FOLDER, f"{base_filename}.iv")
        with open(iv_file, 'wb') as f:
            f.write(iv)
        
        # Save metadata
        meta_file = os.path.join(SECURE_FOLDER, f"{base_filename}.json")
        with open(meta_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✓ Encrypted image saved: {base_filename}")
        return base_filename
    
    def load_encrypted_image(self, base_filename):
        """Load and decrypt an image"""
        try:
            encrypted_file = os.path.join(SECURE_FOLDER, f"{base_filename}.enc")
            iv_file = os.path.join(SECURE_FOLDER, f"{base_filename}.iv")
            meta_file = os.path.join(SECURE_FOLDER, f"{base_filename}.json")
            
            # Read encrypted data
            with open(encrypted_file, 'rb') as f:
                encrypted_data = f.read()
            
            # Read IV
            with open(iv_file, 'rb') as f:
                iv = f.read()
            
            # Read metadata
            with open(meta_file, 'r') as f:
                metadata = json.load(f)
            
            # Decrypt image
            pil_image = self.decrypt_image(encrypted_data, iv)
            
            return pil_image, metadata
        except Exception as e:
            print(f"Failed to load encrypted image: {e}")
            return None, None
    
    def list_encrypted_images(self):
        """List all encrypted images"""
        print("\n=== ENCRYPTED IMAGES ===")
        enc_files = [f for f in os.listdir(SECURE_FOLDER) if f.endswith('.enc')]
        
        if not enc_files:
            print("No encrypted images found.")
            return []
        
        image_list = []
        for enc_file in sorted(enc_files):
            base_name = enc_file.replace('.enc', '')
            meta_file = os.path.join(SECURE_FOLDER, f"{base_name}.json")
            
            if os.path.exists(meta_file):
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                
                print(f"📷 {base_name}")
                print(f"   Time: {metadata['timestamp']}")
                print(f"   Face: {'✓' if metadata['face_detected'] else '✗'}")
                print(f"   Size: {metadata['size']} bytes")
                print()
                image_list.append(base_name)
        
        return image_list

# Robot Control System
class RobotController:
    def __init__(self):
        # Setup GPIO
        GPIO.setwarnings(False)
        self.h_servo_pin = 23
        self.v_servo_pin = 24
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.h_servo_pin, GPIO.OUT)
        GPIO.setup(self.v_servo_pin, GPIO.OUT)
        self.h_pwm = GPIO.PWM(self.h_servo_pin, 50)
        self.v_pwm = GPIO.PWM(self.v_servo_pin, 50)
        self.h_pwm.start(0)
        self.v_pwm.start(0)
        
        # Setup camera
        self.picam2 = Picamera2()
        self.picam2.configure(self.picam2.create_video_configuration(main={"size": (640, 480)}))
        self.picam2.start()
        
        # Setup face detection
        self.mp_face = mp.solutions.face_detection.FaceDetection(
            model_selection=0, min_detection_confidence=0.5
        )
        
        # Security manager
        self.security = SecureImageManager()
        
        # Servo positions
        self.h_angle = 90
        self.v_angle = 90
    
    def set_servo_angle(self, pwm_obj, angle):
        """Set servo to specific angle"""
        duty = (angle / 18.0) + 2.5
        pwm_obj.ChangeDutyCycle(duty)
        time.sleep(0.1)
        pwm_obj.ChangeDutyCycle(0)
    
    def track_face(self, frame):
        """Simple face tracking logic"""
        image_input = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.mp_face.process(image_input)
        
        face_detected = bool(results.detections)
        
        if results.detections:
            detection = results.detections[0]
            bbox = detection.location_data.relative_bounding_box
            
            # Draw face rectangle
            x = int(bbox.xmin * 640)
            y = int(bbox.ymin * 480)
            w = int(bbox.width * 640)
            h = int(bbox.height * 480)
            
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
            cv2.putText(frame, "FACE DETECTED", (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Simple tracking
            cx = x + w // 2
            cy = y + h // 2
            
            # Horizontal tracking
            if cx < 200:
                self.h_angle = 110
                self.set_servo_angle(self.h_pwm, self.h_angle)
            elif cx > 440:
                self.h_angle = 70
                self.set_servo_angle(self.h_pwm, self.h_angle)
            else:
                self.h_angle = 90
                self.set_servo_angle(self.h_pwm, self.h_angle)
            
            # Vertical tracking
            if cy < 160:
                self.v_angle = 120
                self.set_servo_angle(self.v_pwm, self.v_angle)
            elif cy > 320:
                self.v_angle = 60
                self.set_servo_angle(self.v_pwm, self.v_angle)
            else:
                self.v_angle = 90
                self.set_servo_angle(self.v_pwm, self.v_angle)
        
        return face_detected
    
    def run(self):
        """Main control loop"""
        try:
            print("🤖 SECURE ROBOT SYSTEM STARTED 🤖")
            print("Controls:")
            print("  'c' - Capture & encrypt image")
            print("  'v' - View encrypted images")
            print("  'l' - List encrypted images")
            print("  ESC/q - Exit")
            print("=" * 40)
            
            # Center servos
            self.set_servo_angle(self.h_pwm, 90)
            self.set_servo_angle(self.v_pwm, 90)
            
            while True:
                # Capture frame
                frame = self.picam2.capture_array()
                frame = cv2.resize(frame, (640, 480))
                frame = cv2.rotate(frame, cv2.ROTATE_180)
                
                # Track faces
                face_detected = self.track_face(frame)
                
                # Add UI elements
                cv2.putText(frame, "🔒 ENCRYPTED MODE", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                
                # Count encrypted images
                enc_count = len([f for f in os.listdir(SECURE_FOLDER) if f.endswith('.enc')])
                cv2.putText(frame, f"Encrypted Images: {enc_count}", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                cv2.putText(frame, f"Servo: H{self.h_angle}° V{self.v_angle}°", (10, 90), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                
                # Display frame
                cv2.imshow("Secure Robot Camera", frame)
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                
                if key == 27 or key == ord('q'):  # ESC or 'q'
                    break
                elif key == CAPTURE_KEY:
                    self.security.save_encrypted_image(frame, face_detected)
                elif key == LIST_KEY:
                    self.security.list_encrypted_images()
                elif key == DECRYPT_KEY:
                    self.view_encrypted_images()
                
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            print("\nProgram terminated by user")
        finally:
            self.cleanup()
    
    def view_encrypted_images(self):
        """View encrypted images (decrypt and display)"""
        image_list = self.security.list_encrypted_images()
        
        if not image_list:
            return
        
        print("Enter image number to view (or 'q' to cancel):")
        for i, img_name in enumerate(image_list):
            print(f"{i+1}. {img_name}")
        
        try:
            choice = input("Choice: ").strip()
            if choice.lower() == 'q':
                return
            
            idx = int(choice) - 1
            if 0 <= idx < len(image_list):
                selected_image = image_list[idx]
                pil_image, metadata = self.security.load_encrypted_image(selected_image)
                
                if pil_image:
                    # Convert PIL to OpenCV for display
                    cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                    
                    # Display decrypted image
                    cv2.imshow(f"Decrypted: {selected_image}", cv_image)
                    print(f"Displaying decrypted image. Press any key to close.")
                    cv2.waitKey(0)
                    cv2.destroyWindow(f"Decrypted: {selected_image}")
                else:
                    print("Failed to decrypt image!")
            else:
                print("Invalid choice!")
        except (ValueError, IndexError):
            print("Invalid input!")
    
    def cleanup(self):
        """Clean up resources"""
        # Center servos
        self.set_servo_angle(self.h_pwm, 90)
        self.set_servo_angle(self.v_pwm, 90)
        
        # Stop PWM and cleanup GPIO
        self.h_pwm.stop()
        self.v_pwm.stop()
        GPIO.cleanup()
        
        # Close camera and windows
        cv2.destroyAllWindows()
        self.picam2.stop()
        print("🔒 Secure cleanup complete")

if __name__ == "__main__":
    # Import numpy for image conversion
    import numpy as np
    
    robot = RobotController()
    robot.run()
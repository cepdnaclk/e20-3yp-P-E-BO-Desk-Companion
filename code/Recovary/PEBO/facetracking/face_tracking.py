#!/usr/bin/env python3
"""
Combined face tracking with photo capture every 5 seconds
Captures and saves cropped face image as captured.jpg.enc (encrypted) when a person is detected
Resizes captured image by 1.5x and ensures proper servo cleanup
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

class CombinedFaceTracking:
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
        self.shared_face_data = None
        self.last_detection_time = time.time()
        
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

    def encrypt_image(self, input_path, output_path):
        try:
            aesgcm = AESGCM(self.key)
            with open(input_path, 'rb') as f:
                data = f.read()
            nonce = os.urandom(12)
            ciphertext = aesgcm.encrypt(nonce, data, None)
            with open(output_path, 'wb') as f:
                f.write(nonce + ciphertext)
            # ~ print(f"Encrypted {input_path} to {output_path}")
            print ("********Encrypted********")
            os.remove(input_path)
        except Exception as e:
            print(f"Encryption error: {e}")

    def get_nearest_face(self, detections):
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

    def face_detection_thread(self):
        while self.running:
            try:
                frame = self.picam2.capture_array()
                frame = cv2.resize(frame, (self.width, self.height))
                frame = cv2.rotate(frame, cv2.ROTATE_180)
                image_input = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.mp_face.process(image_input)
                nearest_face = None
                if results.detections:
                    nearest_face = self.get_nearest_face(results.detections)
                with self.face_data_lock:
                    self.shared_face_data = nearest_face
                    if nearest_face:
                        self.last_detection_time = time.time()
                if not self.frame_queue.full():
                    self.frame_queue.put((frame, results.detections, nearest_face))
                time.sleep(0.01)
            except Exception as e:
                print(f"Face detection error: {e}")
                time.sleep(0.1)

    def dual_servo_thread(self):
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
                time.sleep(0.1)

    def center_servo_thread(self):
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
                time.sleep(0.1)

    def display_thread(self):
        while self.running:
            try:
                if not self.frame_queue.empty():
                    frame, detections, nearest_face = self.frame_queue.get()
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
                    cv2.putText(frame, f"Dual H: {self.h_current_angle}°, P: {self.h_current_partition}",
                                (self.width - 300, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                    cv2.putText(frame, f"Dual V: {self.v_current_angle}°, P: {self.v_current_partition}",
                                (self.width - 300, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                    cv2.putText(frame, f"Center: {self.center_current_angle:.1f}°",
                                (self.width - 200, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                    direction_text = "Normal" if self.direction_multiplier == 1 else "Reversed"
                    cv2.putText(frame, f"Direction: {direction_text}",
                                (self.width - 200, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                    cv2.putText(frame, "Combined Face Tracking", (self.width//2 - 150, self.height - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.imshow("Combined Face Tracking", frame)
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
        try:
            self.pwm.channels[servo_channel].duty_cycle = 0
            print(f"Servo channel {servo_channel} de-energized")
        except Exception as e:
            print(f"Error stopping servo channel {servo_channel}: {e}")

    def cleanup(self):
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
        print("Cleanup complete")

    def run(self):
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

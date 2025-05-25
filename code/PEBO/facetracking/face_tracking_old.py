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

class CombinedFaceTracking:
    def __init__(self):
        # Setup I2C and PCA9685 PWM controller
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.pwm = PCA9685(self.i2c)
        self.pwm.frequency = 50  # Standard servo frequency (50Hz)
        
        # Setup servos
        self.h_servo_channel = 7  # Dual servo - Horizontal on channel 7
        self.v_servo_channel = 6  # Dual servo - Vertical on channel 6
        self.center_servo_channel = 4  # Center servo on channel 4
        
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
        self.v_partition_angles = {1: 130, 2: 100, 3: 90}
        self.h_partition_boundaries = [(0, 70, 1), (90, 160, 2), (180, 250, 3), (270, 370, 4),
                                       (390, 460, 5), (480, 550, 6), (570, 640, 7)]
        self.v_partition_boundaries = [(0, 120, 1), (170, 290, 2), (340, 480, 3)]
        
        self.h_current_angle = 80
        self.v_current_angle = 70
        self.h_current_partition = 4
        self.v_current_partition = 2
        
        # Center servo parameters
        self.center_current_angle = 90
        self.center_target_angle = 90
        self.center_zone_width = 80
        self.center_zone_left = (self.width // 2) - (self.center_zone_width // 2)
        self.center_zone_right = (self.width // 2) + (self.center_zone_width // 2)
        self.center_kp = 0.1
        self.direction_multiplier = 1

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
        """Thread for capturing frames and detecting faces"""
        while self.running:
            try:
                frame = self.picam2.capture_array()
                frame = cv2.resize(frame, (self.width, self.height))
                frame = cv2.rotate(frame, cv2.ROTATE_180)
                image_input = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.mp_face.process(image_input)
                
                # Get nearest face
                nearest_face = None
                if results.detections:
                    nearest_face = self.get_nearest_face(results.detections)
                
                # Update shared data
                with self.face_data_lock:
                    self.shared_face_data = nearest_face
                    if nearest_face:
                        self.last_detection_time = time.time()
                
                # Put frame in queue for display
                if not self.frame_queue.full():
                    self.frame_queue.put((frame, results.detections, nearest_face))
                
                time.sleep(0.01)  # Small delay for face detection
                
            except Exception as e:
                print(f"Face detection error: {e}")
                time.sleep(0.1)

    def dual_servo_thread(self):
        """Thread for controlling dual servos (fast motion)"""
        face_timeout = 2.0
        
        def set_angle_smooth_fast(servo_obj, current_angle, target_angle, step=2):
            if current_angle == target_angle:
                return current_angle
            direction = 1 if target_angle > current_angle else -1
            for angle in range(current_angle, target_angle + direction, direction):
                servo_obj.angle = angle
                time.sleep(0.01)  # Fast motion
            servo_obj.angle = target_angle
            time.sleep(0.01)
            return target_angle

        def get_partition(position, boundaries):
            for start, end, partition in boundaries:
                if start <= position <= end:
                    return partition, False
            return None, True
        
        # Set initial positions
        self.h_current_angle = set_angle_smooth_fast(self.h_servo, 80, self.h_current_angle)
        self.v_current_angle = set_angle_smooth_fast(self.v_servo, 110, self.v_current_angle)
        
        while self.running:
            try:
                current_time = time.time()
                
                # Get face data
                with self.face_data_lock:
                    face_data = self.shared_face_data
                    last_detection = self.last_detection_time
                
                if face_data:
                    cx, cy = face_data['center']
                    
                    h_partition, h_in_gap = get_partition(cx, self.h_partition_boundaries)
                    v_partition, v_in_gap = get_partition(cy, self.v_partition_boundaries)
                    
                    # Update horizontal servo
                    if not h_in_gap and h_partition != self.h_current_partition:
                        h_target_angle = self.h_partition_angles[h_partition]
                        self.h_current_angle = set_angle_smooth_fast(self.h_servo, self.h_current_angle, h_target_angle)
                        self.h_current_partition = h_partition
                    
                    # Update vertical servo
                    if not v_in_gap and v_partition != self.v_current_partition:
                        v_target_angle = self.v_partition_angles[v_partition]
                        self.v_current_angle = set_angle_smooth_fast(self.v_servo, self.v_current_angle, v_target_angle)
                        self.v_current_partition = v_partition
                
                elif current_time - last_detection > face_timeout:
                    # Return to center position
                    if self.h_current_angle != 80 or self.v_current_angle != 110:
                        self.h_current_angle = set_angle_smooth_fast(self.h_servo, self.h_current_angle, 80)
                        self.v_current_angle = set_angle_smooth_fast(self.v_servo, self.v_current_angle, 110)
                        self.h_current_partition = 4
                        self.v_current_partition = 2
                
                time.sleep(0.01)  # Fast update rate for dual servos
                
            except Exception as e:
                print(f"Dual servo error: {e}")
                time.sleep(0.1)

    def center_servo_thread(self):
        """Thread for controlling center servo (slow motion)"""
        face_timeout = 5.0
        
        def set_angle_smooth_slow(servo_obj, current_angle, target_angle, step=2):
            if abs(current_angle - target_angle) < step:
                servo_obj.angle = target_angle
                return target_angle
                
            direction = 1 if target_angle > current_angle else -1
            new_angle = current_angle + (direction * step)
            servo_obj.angle = new_angle
            return new_angle
        
        # Set initial position
        self.center_servo.angle = self.center_current_angle
        
        while self.running:
            try:
                current_time = time.time()
                
                # Get face data
                with self.face_data_lock:
                    face_data = self.shared_face_data
                    last_detection = self.last_detection_time
                
                if face_data:
                    face_center_x, _ = face_data['center']
                    center_x = self.width // 2
                    
                    # Check if face is centered
                    face_centered = self.center_zone_left <= face_center_x <= self.center_zone_right
                    
                    if not face_centered:
                        # Calculate error and adjustment
                        error = center_x - face_center_x
                        adjustment = self.center_kp * error * self.direction_multiplier
                        self.center_target_angle = self.center_current_angle + adjustment
                        
                        # Ensure angle is within limits
                        self.center_target_angle = max(0, min(180, self.center_target_angle))
                
                elif current_time - last_detection > face_timeout:
                    # Return to center position
                    self.center_target_angle = 90
                
                # Move servo toward target angle smoothly
                if self.center_current_angle != self.center_target_angle:
                    self.center_current_angle = set_angle_smooth_slow(
                        self.center_servo, self.center_current_angle, self.center_target_angle
                    )
                
                time.sleep(0.1)  # Slow update rate for center servo
                
            except Exception as e:
                print(f"Center servo error: {e}")
                time.sleep(0.1)

    def display_thread(self):
        """Thread for displaying the video feed"""
        while self.running:
            try:
                if not self.frame_queue.empty():
                    frame, detections, nearest_face = self.frame_queue.get()
                    
                    # Draw partition lines
                    for start_x, end_x, p in self.h_partition_boundaries:
                        cv2.rectangle(frame, (start_x, 20), (end_x, 40), (0, 255, 0), -1)
                        cv2.putText(frame, str(p), (start_x + (end_x - start_x)//2 - 5, 35),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
                        cv2.line(frame, (start_x, 0), (start_x, self.height), (200, 200, 200), 1)
                    
                    for start_y, end_y, p in self.v_partition_boundaries:
                        cv2.rectangle(frame, (self.width-40, start_y), (self.width-20, end_y), (255, 165, 0), -1)
                        cv2.putText(frame, str(p), (self.width-35, start_y + (end_y - start_y)//2),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
                        cv2.line(frame, (0, start_y), (self.width, start_y), (200, 200, 200), 1)
                    
                    # Draw center reference
                    center_x = self.width // 2
                    cv2.line(frame, (center_x, 0), (center_x, self.height), (0, 255, 0), 2)
                    cv2.rectangle(frame, (self.center_zone_left, 0), (self.center_zone_right, self.height), (0, 255, 0), 1)
                    
                    # Draw face detection
                    if nearest_face:
                        x, y, w, h = nearest_face['bbox']
                        cx, cy = nearest_face['center']
                        
                        # Draw bounding box
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
                        
                        # Display face area
                        area_text = f"Area: {nearest_face['area']:.0f}px²"
                        cv2.putText(frame, area_text, (x, y - 10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                        
                        # Check centering status
                        face_centered = self.center_zone_left <= cx <= self.center_zone_right
                        status_text = "CENTERED" if face_centered else "NOT CENTERED"
                        status_color = (0, 255, 0) if face_centered else (0, 0, 255)
                        cv2.putText(frame, status_text, (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
                        
                        # Draw other faces in red
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
                    
                    # Display servo information
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
                    
                    # Handle keyboard input
                    key = cv2.waitKey(1) & 0xFF
                    if key == 27:  # ESC key
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
                        print(f"Center servo direction: {'Normal' if self.direction_multiplier == 1 else 'Reversed'}")
                
                time.sleep(0.03)  # ~30 FPS display
                
            except Exception as e:
                print(f"Display error: {e}")
                time.sleep(0.1)

    def stop_servo(self, servo_channel):
        """Stop a servo by setting duty cycle to 0"""
        self.pwm.channels[servo_channel].duty_cycle = 0

    def cleanup(self):
        """Clean up resources"""
        print("Returning servos to safe positions...")
        
        # Set servos to safe positions
        self.h_servo.angle = 80
        self.v_servo.angle = 100
        self.center_servo.angle = 90
        time.sleep(0.5)
        
        # De-energize all servos
        self.stop_servo(self.h_servo_channel)
        self.stop_servo(self.v_servo_channel)
        self.stop_servo(self.center_servo_channel)
        
        # Cleanup
        self.pwm.deinit()
        cv2.destroyAllWindows()
        self.picam2.stop()
        print("Cleanup complete")

    def run(self):
        """Main function to run all threads"""
        print("Combined face tracking started.")
        print("Press ESC to exit")
        print("Press '+' to increase min face area")
        print("Press '-' to decrease min face area")
        print("Press 'r' to reverse center servo direction")
        
        # Create and start threads
        threads = [
            threading.Thread(target=self.face_detection_thread, daemon=True),
            threading.Thread(target=self.dual_servo_thread, daemon=True),
            threading.Thread(target=self.center_servo_thread, daemon=True),
            threading.Thread(target=self.display_thread, daemon=True)
        ]
        
        for thread in threads:
            thread.start()
        
        try:
            # Wait for display thread to finish (user presses ESC)
            threads[3].join()
        except KeyboardInterrupt:
            print("Program interrupted by user")
        finally:
            self.running = False
            self.cleanup()

# Main execution
if __name__ == "__main__":
    tracker = CombinedFaceTracking()
    tracker.run()

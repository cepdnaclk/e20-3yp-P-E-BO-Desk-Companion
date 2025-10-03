import cv2
import mediapipe as mp
from picamera2 import Picamera2
import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

def horizontal_face_centering():
    # Setup I2C and PCA9685 PWM controller
    i2c = busio.I2C(board.SCL, board.SDA)
    pwm = PCA9685(i2c)
    pwm.frequency = 50  # Standard servo frequency (50Hz)
    
    # Setup servo - using horizontal servo on channel 4
    servo_channel = 4
    h_servo = servo.Servo(pwm.channels[servo_channel])
    
    # Initialize camera
    picam2 = Picamera2()
    picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
    picam2.start()
    
    # Initialize MediaPipe face detection
    mp_face = mp.solutions.face_detection.FaceDetection(
        model_selection=0,
        min_detection_confidence=0.6
    )
    
    # Frame dimensions
    width, height = 640, 480
    center_x = width // 2
    
    # Define center zone (the area we consider "centered")
    center_zone_width = 80  # pixels total (40 pixels on each side of center)
    center_zone_left = center_x - (center_zone_width // 2)
    center_zone_right = center_x + (center_zone_width // 2)
    
    # Servo parameters - DIRECTION CORRECTED
    current_angle = 90  # Start at center position (90 degrees)
    target_angle = 90
    min_angle = 0  # Minimum angle for the servo (leftmost position)
    max_angle = 180  # Maximum angle for the servo (rightmost position)
    
    # Minimum face size threshold (as percentage of frame area)
    min_face_area_percent = 3.0  # Adjust this value as needed
    
    # PID control parameters
    kp = 0.1  # Proportional gain - adjust as needed
    
    # Function to smoothly transition the servo to a target angle
    def set_angle_smooth(servo_obj, current_angle, target_angle, step=2):
        if abs(current_angle - target_angle) < step:
            servo_obj.angle = target_angle
            return target_angle
            
        direction = 1 if target_angle > current_angle else -1
        new_angle = current_angle + (direction * step)
        servo_obj.angle = new_angle
        return new_angle
    
    # Function to get the nearest face in the frame
    def get_nearest_face(detections, frame_width, frame_height):
        if not detections:
            return None
            
        # Calculate minimum face size threshold
        min_area = (frame_width * frame_height) * (min_face_area_percent / 100.0)
        
        largest_area = 0
        nearest_face = None
        
        for detection in detections:
            bbox = detection.location_data.relative_bounding_box
            x = int(bbox.xmin * frame_width)
            y = int(bbox.ymin * frame_height)
            w = int(bbox.width * frame_width)
            h = int(bbox.height * frame_height)
            
            # Calculate area of face bounding box
            area = w * h
            
            # Check if this face is larger than minimum size
            if area >= min_area and area > largest_area:
                largest_area = area
                nearest_face = {
                    'detection': detection,
                    'bbox': (x, y, w, h),
                    'center': (x + w // 2, y + h // 2),
                    'area': area
                }
        
        return nearest_face
    
    try:
        print("Horizontal face centering started. Press ESC to exit.")
        print("Press 'r' to reverse servo direction if needed")
        
        # Set initial servo position
        h_servo.angle = current_angle
        last_detection_time = time.time()
        face_timeout = 5.0  # seconds
        
        # Direction multiplier (can be toggled with 'r' key)
        direction_multiplier = 1  # 1 for normal, -1 for reversed
        
        while True:
            # Capture frame and process
            frame = picam2.capture_array()
            frame = cv2.resize(frame, (width, height))
            frame = cv2.rotate(frame, cv2.ROTATE_180)  # Rotate if needed
            image_input = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = mp_face.process(image_input)
            current_time = time.time()
            
            # Draw center reference
            cv2.line(frame, (center_x, 0), (center_x, height), (0, 255, 0), 2)  # Center line
            cv2.rectangle(frame, (center_zone_left, 0), (center_zone_right, height), (0, 255, 0), 1)  # Center zone
            
            # Process face detections
            if results.detections:
                # Get nearest/largest face
                nearest_face = get_nearest_face(results.detections, width, height)
                
                if nearest_face:
                    # Extract face information
                    x, y, w, h = nearest_face['bbox']
                    face_center_x, face_center_y = nearest_face['center']
                    
                    # Update last detection time
                    last_detection_time = current_time
                    
                    # Draw the face bounding box
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.circle(frame, (face_center_x, face_center_y), 5, (0, 0, 255), -1)
                    
                    # Display face area
                    area_text = f"Area: {nearest_face['area']:.0f}px²"
                    cv2.putText(frame, area_text, (x, y - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    
                    # Check if face is centered
                    face_centered = center_zone_left <= face_center_x <= center_zone_right
                    
                    if not face_centered:
                        # Calculate error (distance from center)
                        error = center_x - face_center_x
                        
                        # CORRECTED LOGIC: 
                        # If face is to the left (positive error), servo should move left (increase angle)
                        # If face is to the right (negative error), servo should move right (decrease angle)
                        adjustment = kp * error * direction_multiplier
                        
                        # Update target angle - DIRECTION CORRECTED
                        target_angle = current_angle + adjustment
                        
                        # Ensure angle is within limits
                        target_angle = max(min_angle, min(max_angle, target_angle))
                    
                    # Display centering status
                    status_text = "CENTERED" if face_centered else "NOT CENTERED"
                    status_color = (0, 255, 0) if face_centered else (0, 0, 255)
                    cv2.putText(frame, status_text, (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
                else:
                    # Found faces but none met the size criteria
                    cv2.putText(frame, "No qualifying faces", (10, 70),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            
            elif current_time - last_detection_time > face_timeout:
                # No face detected for a while, return to center
                if current_angle != 90:
                    target_angle = 90
                    
                cv2.putText(frame, "No face detected", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Move servo toward target angle smoothly
            if current_angle != target_angle:
                current_angle = set_angle_smooth(h_servo, current_angle, target_angle)
            
            # Display angle information
            cv2.putText(frame, f"Servo Angle: {current_angle:.1f}°", (width - 200, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            cv2.putText(frame, f"Target Angle: {target_angle:.1f}°", (width - 200, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            
            # Display direction status
            direction_text = "Normal" if direction_multiplier == 1 else "Reversed"
            cv2.putText(frame, f"Direction: {direction_text}", (width - 200, 90), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            
            cv2.putText(frame, "Horizontal Face Centering", (width//2 - 150, height - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Display the frame
            cv2.imshow("Face Centering", frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC key
                break
            elif key == ord('+'): 
                # Increase minimum face area threshold
                min_face_area_percent += 0.5
                print(f"Min face area: {min_face_area_percent:.1f}%")
            elif key == ord('-'):
                # Decrease minimum face area threshold
                min_face_area_percent = max(0.5, min_face_area_percent - 0.5)
                print(f"Min face area: {min_face_area_percent:.1f}%")
            elif key == ord('r'):
                # Reverse servo direction
                direction_multiplier *= -1
                print(f"Servo direction: {'Normal' if direction_multiplier == 1 else 'Reversed'}")
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("Program interrupted by user")
    
    finally:
        print("Returning servo to center position (90°)")
        h_servo.angle = 90
        time.sleep(0.5)
        
        # De-energize servo by setting pulse width to 0
        pwm.channels[servo_channel].duty_cycle = 0
        
        pwm.deinit()
        cv2.destroyAllWindows()
        picam2.stop()
        print("Cleanup complete")

# Run the function
if __name__ == "__main__":
    horizontal_face_centering()
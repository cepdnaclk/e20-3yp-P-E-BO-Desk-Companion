import cv2
import mediapipe as mp
import RPi.GPIO as GPIO
from picamera2 import Picamera2
import time

# Setup GPIO for controlling the servos
GPIO.setwarnings(False)
# Horizontal servo
h_servo_pin = 23 # pin 16
# Vertical servo
v_servo_pin = 24 # pin 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(h_servo_pin, GPIO.OUT)
GPIO.setup(v_servo_pin, GPIO.OUT)
h_pwm = GPIO.PWM(h_servo_pin, 50)
v_pwm = GPIO.PWM(v_servo_pin, 50)
h_pwm.start(0)
v_pwm.start(0)

# Setup Picamera2 for accessing the camera
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
picam2.start()

# Initialize MediaPipe face detection
mp_face = mp.solutions.face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5)

# Frame dimensions
width = 640
height = 480

# Define 7 main horizontal partitions with angle assignments
h_partition_angles = {
    1: 70,   # Far left
    2: 75,
    3: 80,
    4: 90,    # Center
    5: 100,
    6: 105,
    7: 110     # Far right
}

# Define 3 vertical partitions with angle assignments
v_partition_angles = {
    1: 50,    # Bottom
    2: 70,   # Middle
    3: 90    # Top
}

# Define horizontal partition boundaries with gaps
h_partition_boundaries = [
    (0, 70, 1),       # Partition 1: 0-70px
    (90, 160, 2),     # Partition 2: 90-160px (gap between 70-90)
    (180, 250, 3),    # Partition 3: 180-250px (gap between 160-180)
    (270, 370, 4),    # Partition 4: 270-370px (gap between 250-270)
    (390, 460, 5),    # Partition 5: 390-460px (gap between 370-390)
    (480, 550, 6),    # Partition 6: 480-550px (gap between 460-480)
    (570, 640, 7)     # Partition 7: 570-640px (gap between 550-570)
]

# Define vertical partition boundaries with 50px gaps
v_partition_boundaries = [
    (0, 120, 1),      # Partition 1 (Bottom): 0-120px
    (170, 290, 2),    # Partition 2 (Middle): 170-290px (gap between 120-170)
    (340, 480, 3)     # Partition 3 (Top): 340-480px (gap between 290-340)
]

# Store the current angles to smooth transitions
h_current_angle = 90    # Start at 90 degrees as default for horizontal
v_current_angle = 70    # Start at 90 degrees as default for vertical
h_current_partition = 4 # Start partition based on default angle (90 degrees)
v_current_partition = 2 # Start at bottom partition
last_detection_time = time.time()
face_timeout = 1.0    # Time in seconds before considering face lost

def set_angle_smooth(pwm_obj, current_angle, target_angle, step=2):
    """Smoothly move the servo from current angle to target angle."""
    if current_angle == target_angle:
        return current_angle
    
    # Determine direction
    direction = 1 if target_angle > current_angle else -1
    
    # Move in steps
    for angle in range(current_angle, target_angle + direction, direction):
        duty = (angle / 18.0) + 2.5  # Convert angle to duty cycle
        pwm_obj.ChangeDutyCycle(duty)
        time.sleep(0.05)  # Smaller delay for faster response
    
    # Ensure we end at exactly the target angle
    duty = (target_angle / 18.0) + 2.5
    pwm_obj.ChangeDutyCycle(duty)
    time.sleep(0.01)
    pwm_obj.ChangeDutyCycle(0)  # Stop the PWM signal to prevent jitter
    
    return target_angle

def get_partition(position, boundaries):
    """Determine which partition the position falls into, or if it's in a gap"""
    for start_pos, end_pos, partition in boundaries:
        if start_pos <= position <= end_pos:
            return partition, False  # Return partition number and flag indicating not in a gap
    
    # If we get here, the position is in a gap between partitions
    return None, True  # Return None for partition and flag indicating in a gap

try:
    print("Dual servo face tracking started. Press ESC to exit.")
    
    # Initial servo positions
    h_current_angle = set_angle_smooth(h_pwm, 90, h_current_angle)  # Move to starting horizontal position
    v_current_angle = set_angle_smooth(v_pwm, 70, v_current_angle)  # Move to starting vertical position
    
    while True:
        # Capture frame from Picamera2
        frame = picam2.capture_array()
        frame = cv2.resize(frame, (width, height))
        
        # Add this line to flip the image horizontally (mirror effect)
        frame = cv2.flip(frame, cv2.ROTATE_180)  # 1 means horizontal flip, 0 would be vertical flip

        
        # Convert color for MediaPipe
        image_input = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = mp_face.process(image_input)
        
        current_time = time.time()
        face_detected = False
        
        # Draw horizontal partition boundaries for visualization
        for start_x, end_x, partition in h_partition_boundaries:
            # Draw the partition area
            cv2.rectangle(frame, (start_x, 20), (end_x, 40), (0, 255, 0), -1)
            cv2.putText(frame, str(partition), (start_x + (end_x - start_x)//2 - 5, 35), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
            # Draw full height lines at boundaries
            cv2.line(frame, (start_x, 0), (start_x, height), (200, 200, 200), 1)
            cv2.line(frame, (end_x, 0), (end_x, height), (200, 200, 200), 1)
        
        # Draw vertical partition boundaries for visualization
        for start_y, end_y, partition in v_partition_boundaries:
            # Draw the partition area
            cv2.rectangle(frame, (width-40, start_y), (width-20, end_y), (255, 165, 0), -1)
            cv2.putText(frame, str(partition), (width-35, start_y + (end_y - start_y)//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
            # Draw full width lines at boundaries
            cv2.line(frame, (0, start_y), (width, start_y), (200, 200, 200), 1)
            cv2.line(frame, (0, end_y), (width, end_y), (200, 200, 200), 1)
        
        if results.detections:
            # Take only the first (most prominent) face
            detection = results.detections[0]
            bbox = detection.location_data.relative_bounding_box
            
            # Calculate coordinates
            x = int(bbox.xmin * width)
            y = int(bbox.ymin * height)
            w = int(bbox.width * width)
            h = int(bbox.height * height)
            
            # Calculate the center point of the face
            cx = x + w // 2
            cy = y + h // 2
            
            # Determine the horizontal partition or if in a gap
            h_partition, h_in_gap = get_partition(cx, h_partition_boundaries)
            
            # Determine the vertical partition or if in a gap
            v_partition, v_in_gap = get_partition(cy, v_partition_boundaries)
            
            face_detected = True
            last_detection_time = current_time
            
            # Display face location
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            
            # Handle horizontal movement
            h_info_text = ""
            if h_in_gap:
                # Face is in a horizontal gap - no servo movement
                h_info_text = f"H: Face in gap: Position {cx}px"
                cv2.putText(frame, h_info_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 2)
            elif h_partition != h_current_partition:
                # Face is in a defined horizontal partition different from current - move servo
                h_target_angle = h_partition_angles[h_partition]
                h_info_text = f"H: Partition {h_partition}, Angle: {h_target_angle}°"
                cv2.putText(frame, h_info_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                print(f"Moving H servo: Partition {h_partition}, Angle {h_target_angle}°")
                h_current_angle = set_angle_smooth(h_pwm, h_current_angle, h_target_angle)
                h_current_partition = h_partition
            else:
                # Face is in the same horizontal partition - no movement needed
                h_info_text = f"H: Partition {h_partition}, No change"
                cv2.putText(frame, h_info_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Handle vertical movement
            v_info_text = ""
            if v_in_gap:
                # Face is in a vertical gap - no servo movement
                v_info_text = f"V: Face in gap: Position {cy}px"
                cv2.putText(frame, v_info_text, (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 2)
            elif v_partition != v_current_partition:
                # Face is in a defined vertical partition different from current - move servo
                v_target_angle = v_partition_angles[v_partition]
                v_info_text = f"V: Partition {v_partition}, Angle: {v_target_angle}°"
                cv2.putText(frame, v_info_text, (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                print(f"Moving V servo: Partition {v_partition}, Angle {v_target_angle}°")
                v_current_angle = set_angle_smooth(v_pwm, v_current_angle, v_target_angle)
                v_current_partition = v_partition
            else:
                # Face is in the same vertical partition - no movement needed
                v_info_text = f"V: Partition {v_partition}, No change"
                cv2.putText(frame, v_info_text, (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        elif current_time - last_detection_time > face_timeout:
            # If no face detected for a while, return to center positions
            if h_current_angle != 90 or v_current_angle != 90:
                print("No face detected, returning to center position")
                h_current_angle = set_angle_smooth(h_pwm, h_current_angle, 90)
                v_current_angle = set_angle_smooth(v_pwm, v_current_angle, 90)
                h_current_partition = 4
                v_current_partition = 2
            
            cv2.putText(frame, "No face detected", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Display current angles on frame
        cv2.putText(frame, f"H Angle: {h_current_angle}°, Partition: {h_current_partition}", 
                    (width - 300, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        cv2.putText(frame, f"V Angle: {v_current_angle}°, Partition: {v_current_partition}", 
                    (width - 300, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        
        # Display frame title
        cv2.putText(frame, "Dual Servo Face Tracking", (width//2 - 150, height - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Display frame
        cv2.imshow("Face Tracking", frame)
        
        # Check for ESC key
        if cv2.waitKey(1) & 0xFF == 27:
            break
        
        # Small delay to reduce CPU usage
        time.sleep(0.01)

except KeyboardInterrupt:
    print("Program terminated by user")
finally:
    # Return servos to safe position before cleanup
    print("Returning servos to safe position (H:90°, V:70°)")
    set_angle_smooth(h_pwm, h_current_angle, 90)  # Set horizontal servo to 90 degrees
    set_angle_smooth(v_pwm, v_current_angle, 70)  # Set vertical servo to 70 degrees
    time.sleep(0.5)  # Short delay to ensure servos reach position
    
    # Clean up
    h_pwm.stop()
    v_pwm.stop()
    GPIO.cleanup()
    cv2.destroyAllWindows()
    picam2.stop()
    print("Cleanup complete")

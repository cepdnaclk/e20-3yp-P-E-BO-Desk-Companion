import cv2
import mediapipe as mp
import RPi.GPIO as GPIO
from picamera2 import Picamera2
import time

# Setup GPIO for controlling the servo
GPIO.setwarnings(False)
servo_pin = 23 # pin 16
GPIO.setmode(GPIO.BCM)
GPIO.setup(servo_pin, GPIO.OUT)
pwm = GPIO.PWM(servo_pin, 50)
pwm.start(0)

# Setup Picamera2 for accessing the camera
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
picam2.start()

# Initialize MediaPipe face detection
mp_face = mp.solutions.face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5)

# Frame dimensions
width = 640
height = 480

# Define 7 main partitions with angle assignments
partition_angles = {
    1: 120,   # Far left
    2: 110,
    3: 100,
    4: 90,   # Center
    5: 80,
    6: 70,
    7: 60   # Far right
}

# Define partition boundaries with gaps
# Format: [(start_x1, end_x1, partition1), (start_x2, end_x2, partition2), ...]
# Gaps exist between end_x of one partition and start_x of the next partition
partition_boundaries = [
    (0, 70, 1),       # Partition 1: 0-70px
    (90, 160, 2),     # Partition 2: 90-160px (gap between 70-90)
    (180, 250, 3),    # Partition 3: 180-250px (gap between 160-180)
    (270, 370, 4),    # Partition 4: 270-370px (gap between 250-270)
    (390, 460, 5),    # Partition 5: 390-460px (gap between 370-390)
    (480, 550, 6),    # Partition 6: 480-550px (gap between 460-480)
    (570, 640, 7)     # Partition 7: 570-640px (gap between 550-570)
]

# Store the current angle to smooth transitions
current_angle = 90    # Start at 90 degrees as default
current_partition = 4 # Start partition based on default angle (90 degrees)
last_detection_time = time.time()
face_timeout = 1.0    # Time in seconds before considering face lost

def set_angle_smooth(current_angle, target_angle, step=2):
    """Smoothly move the servo from current angle to target angle."""
    if current_angle == target_angle:
        return
    
    # Determine direction
    direction = 1 if target_angle > current_angle else -1
    
    # Move in steps
    for angle in range(current_angle, target_angle + direction, direction):
        duty = (angle / 18.0) + 2.5  # Convert angle to duty cycle
        pwm.ChangeDutyCycle(duty)
        time.sleep(0.05)  # Smaller delay for faster response
    
    # Ensure we end at exactly the target angle
    duty = (target_angle / 18.0) + 2.5
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.01)
    pwm.ChangeDutyCycle(0)  # Stop the PWM signal to prevent jitter

def get_partition(cx):
    """Determine which partition the face center falls into, or if it's in a gap"""
    for start_x, end_x, partition in partition_boundaries:
        if start_x <= cx <= end_x:
            return partition, False  # Return partition number and flag indicating not in a gap
    
    # If we get here, the face is in a gap between partitions
    return None, True  # Return None for partition and flag indicating in a gap

try:
    print("Face tracking started. Press ESC to exit.")
    
    # Initial servo position
    set_angle_smooth(0, current_angle)  # Move to starting position
    
    while True:
        # Capture frame from Picamera2
        frame = picam2.capture_array()
        frame = cv2.resize(frame, (width, height))
        
        # Convert color for MediaPipe
        image_input = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = mp_face.process(image_input)
        
        current_time = time.time()
        face_detected = False
        
        # Draw partition boundaries for visualization
        for start_x, end_x, partition in partition_boundaries:
            # Draw the partition area
            cv2.rectangle(frame, (start_x, 20), (end_x, 40), (0, 255, 0), -1)
            cv2.putText(frame, str(partition), (start_x + (end_x - start_x)//2 - 5, 35), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
            # Draw full height lines at boundaries
            cv2.line(frame, (start_x, 0), (start_x, height), (200, 200, 200), 1)
            cv2.line(frame, (end_x, 0), (end_x, height), (200, 200, 200), 1)
        
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
            
            # Determine the partition or if in a gap
            partition, in_gap = get_partition(cx)
            
            face_detected = True
            last_detection_time = current_time
            
            # Display face location
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            
            if in_gap:
                # Face is in a gap - no servo movement
                info_text = f"Face in gap: Position {cx}px"
                cv2.putText(frame, info_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 2)
                cv2.putText(frame, "No movement", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 2)
            elif partition != current_partition:
                # Face is in a defined partition different from current - move servo
                target_angle = partition_angles[partition]
                info_text = f"Face in partition {partition}, Angle: {target_angle}°"
                cv2.putText(frame, info_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                print(f"Moving servo: Partition {partition}, Angle {target_angle}°")
                set_angle_smooth(current_angle, target_angle)
                current_angle = target_angle
                current_partition = partition
            else:
                # Face is in the same partition - no movement needed
                info_text = f"Face in partition {partition}, No change needed"
                cv2.putText(frame, info_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        elif current_time - last_detection_time > face_timeout:
            # If no face detected for a while, return to center
            if current_angle != 90:
                print("No face detected, returning to center position")
                set_angle_smooth(current_angle, 90)
                current_angle = 90
                current_partition = 4
            
            cv2.putText(frame, "No face detected", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Display current angle on frame
        cv2.putText(frame, f"Current Angle: {current_angle}°", (width - 200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        cv2.putText(frame, f"Current Partition: {current_partition}", (width - 200, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        
        # Display frame title
        cv2.putText(frame, "Face Tracking with Gap Zones", (width//2 - 150, height - 20), 
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
    # Clean up
    pwm.stop()
    GPIO.cleanup()
    cv2.destroyAllWindows()
    picam2.stop()
    print("Cleanup complete")
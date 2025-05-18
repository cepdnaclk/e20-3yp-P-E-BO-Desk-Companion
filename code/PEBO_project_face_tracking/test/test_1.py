import cv2
import mediapipe as mp
import RPi.GPIO as GPIO
from picamera2 import Picamera2
import time

# Setup GPIO for controlling the servo
GPIO.setwarnings(False)
servo_pin = 23
GPIO.setmode(GPIO.BCM)
GPIO.setup(servo_pin, GPIO.OUT)
pwm = GPIO.PWM(servo_pin, 50)
pwm.start(0)

# Setup Picamera2 for accessing the camera
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration())
picam2.start()

mp_face = mp.solutions.face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5)
width = 640  # Frame width
height = 480  # Frame height

# Servo angle mapping based on face center position
position_to_angle = {
    1: 50,
    2: 60,
    3: 70,
    4: 80,
    5: 90,
    6: 100,
    7: 110,
    8: 120
}

# Store the current angle to smooth transitions
current_angle = 90  # Start at 90 degrees as default
current_position = 5  # Start position based on default angle (90 degrees)

def set_angle_smooth(current_angle, target_angle, step=1):
    """Smoothly move the servo from current angle to target angle."""
    for angle in range(current_angle, target_angle, step if target_angle > current_angle else -step):
        duty = (angle / 18.0) + 2.5  # Convert angle to duty cycle
        pwm.ChangeDutyCycle(duty)
        time.sleep(0.02)  # Small delay to allow the servo to move

def set_angle(angle, speed=0.05):
    duty = (angle / 18.0) + 2.5  # Convert angle to duty cycle
    pwm.ChangeDutyCycle(duty)
    time.sleep(speed)  # Adjust speed of movement

while True:
    frame = picam2.capture_array()  # Capture frame from Picamera2
    frame = cv2.resize(frame, (width, height))
    
    image_input = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = mp_face.process(image_input)
    # time.sleep(2)
    
    if results.detections:
        for detection in results.detections:
            time.sleep(2)
            bbox = detection.location_data.relative_bounding_box
            x, y, w, h = int(bbox.xmin * width), int(bbox.ymin * height), int(bbox.width * width), int(bbox.height * height)
            
            # Calculate the center point of the face
            cx = x + w // 2
            cy = y + h // 2
            
            # Determine the range the face center falls into
            position = min(max(cx // 80 + 1, 1), 8)
            target_angle = position_to_angle.get(position, 90)  # Default to 90 degrees
            
            print(f"Face Center X: {cx}, Position: {position}, Target Angle: {target_angle}")
            
            # Only update the servo if the position has changed
            if position != current_position:
                # Smoothly transition from the current angle to the target angle
                set_angle_smooth(current_angle, target_angle)
                # Update the current angle and position
                current_angle = target_angle
                current_position = position
            else:
                print("Position unchanged, skipping servo update.")
            
            # Draw rectangle and center point
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
    
    cv2.imshow("FRAME", frame)
    if cv2.waitKey(1) & 0xFF == 27:  # Exit on 'ESC' key
        break
    
    # time.sleep(1)  # Capture frames every 1 second

pwm.stop()
GPIO.cleanup()
cv2.destroyAllWindows()

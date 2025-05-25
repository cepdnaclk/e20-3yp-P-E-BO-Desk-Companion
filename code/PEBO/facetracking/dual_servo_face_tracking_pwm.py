import cv2
import mediapipe as mp
from picamera2 import Picamera2
import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

def dual_servo_face_tracking():
    # Setup I2C and PCA9685 PWM controller
    i2c = busio.I2C(board.SCL, board.SDA)
    pwm = PCA9685(i2c)
    pwm.frequency = 50  # Standard servo frequency (50Hz)
    
    # Define a function to completely stop the servo (no holding torque)
    def stop_servo(servo_channel):
        pwm.channels[servo_channel].duty_cycle = 0
    
    # Setup servos
    h_servo_channel = 7  # Horizontal servo on channel 7
    v_servo_channel = 6  # Vertical servo on channel 6
    h_servo = servo.Servo(pwm.channels[h_servo_channel])
    v_servo = servo.Servo(pwm.channels[v_servo_channel])

    # Initialize camera
    picam2 = Picamera2()
    picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
    picam2.start()

    # Initialize MediaPipe
    # Increased detection confidence to focus on clearer faces
    mp_face = mp.solutions.face_detection.FaceDetection(
        model_selection=0, 
        min_detection_confidence=0.6
    )

    # Frame dimensions
    width, height = 640, 480

    # Minimum face size threshold (as percentage of frame area)
    min_face_area_percent = 3.0  # Adjust this value as needed

    h_partition_angles = {1: 110, 2: 105, 3: 100, 4: 80, 5: 60, 6: 55, 7: 50}
    v_partition_angles = {1: 130, 2: 100, 3: 90}
    h_partition_boundaries = [(0, 70, 1), (90, 160, 2), (180, 250, 3), (270, 370, 4),
                              (390, 460, 5), (480, 550, 6), (570, 640, 7)]
    v_partition_boundaries = [(0, 120, 1), (170, 290, 2), (340, 480, 3)]

    h_current_angle = 80
    v_current_angle = 70
    h_current_partition = 4
    v_current_partition = 2
    last_detection_time = time.time()
    face_timeout = 2.0

    def set_angle_smooth(servo_obj, current_angle, target_angle, step=2):
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
        print("Dual servo face tracking started. Press ESC to exit.")
        h_current_angle = set_angle_smooth(h_servo, 80, h_current_angle)
        v_current_angle = set_angle_smooth(v_servo, 110, v_current_angle)

        while True:
            frame = picam2.capture_array()
            frame = cv2.resize(frame, (width, height))
            frame = cv2.rotate(frame, cv2.ROTATE_180)
            image_input = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = mp_face.process(image_input)
            current_time = time.time()
            face_detected = False

            # Draw partition lines
            for start_x, end_x, p in h_partition_boundaries:
                cv2.rectangle(frame, (start_x, 20), (end_x, 40), (0, 255, 0), -1)
                cv2.putText(frame, str(p), (start_x + (end_x - start_x)//2 - 5, 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
                cv2.line(frame, (start_x, 0), (start_x, height), (200, 200, 200), 1)
                cv2.line(frame, (end_x, 0), (end_x, height), (200, 200, 200), 1)
            for start_y, end_y, p in v_partition_boundaries:
                cv2.rectangle(frame, (width-40, start_y), (width-20, end_y), (255, 165, 0), -1)
                cv2.putText(frame, str(p), (width-35, start_y + (end_y - start_y)//2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
                cv2.line(frame, (0, start_y), (width, start_y), (200, 200, 200), 1)
                cv2.line(frame, (0, end_y), (width, end_y), (200, 200, 200), 1)

            # Process facial detections
            if results.detections:
                # Get nearest/largest face (if any meet criteria)
                nearest_face = get_nearest_face(results.detections, width, height)
                
                if nearest_face:
                    # Extract face information
                    x, y, w, h = nearest_face['bbox']
                    cx, cy = nearest_face['center']
                    
                    h_partition, h_in_gap = get_partition(cx, h_partition_boundaries)
                    v_partition, v_in_gap = get_partition(cy, v_partition_boundaries)

                    face_detected = True
                    last_detection_time = current_time

                    # Draw bounding box for the nearest face (green)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
                    
                    # Display face area (helps with tuning)
                    area_text = f"Area: {nearest_face['area']:.0f}px²"
                    cv2.putText(frame, area_text, (x, y - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                    if not h_in_gap and h_partition != h_current_partition:
                        h_target_angle = h_partition_angles[h_partition]
                        h_current_angle = set_angle_smooth(h_servo, h_current_angle, h_target_angle)
                        h_current_partition = h_partition

                    if not v_in_gap and v_partition != v_current_partition:
                        v_target_angle = v_partition_angles[v_partition]
                        v_current_angle = set_angle_smooth(v_servo, v_current_angle, v_target_angle)
                        v_current_partition = v_partition
                        
                    # If there are other faces, draw them in a different color (red)
                    for detection in results.detections:
                        if detection != nearest_face['detection']:
                            bbox = detection.location_data.relative_bounding_box
                            other_x = int(bbox.xmin * width)
                            other_y = int(bbox.ymin * height)
                            other_w = int(bbox.width * width)
                            other_h = int(bbox.height * height)
                            # Draw other faces with red rectangles
                            cv2.rectangle(frame, (other_x, other_y), 
                                        (other_x + other_w, other_y + other_h), 
                                        (0, 0, 255), 1)
                else:
                    # Found faces but none met the size criteria
                    cv2.putText(frame, "No qualifying faces", (10, 70),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

            elif current_time - last_detection_time > face_timeout:
                if h_current_angle != 80 or v_current_angle != 110:
                    h_current_angle = set_angle_smooth(h_servo, h_current_angle, 80)
                    v_current_angle = set_angle_smooth(v_servo, v_current_angle, 110)
                    h_current_partition = 4
                    v_current_partition = 2
                cv2.putText(frame, "No face detected", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            # Annotations
            cv2.putText(frame, f"H Angle: {h_current_angle}°, Partition: {h_current_partition}",
                        (width - 300, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            cv2.putText(frame, f"V Angle: {v_current_angle}°, Partition: {v_current_partition}",
                        (width - 300, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            cv2.putText(frame, "Nearest Face Tracking", (width//2 - 150, height - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            cv2.imshow("Face Tracking", frame)

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
                
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("Program interrupted by user")

    finally:
        print("Returning servos to safe position (H:80°, V:110°)")
        set_angle_smooth(h_servo, h_current_angle, 80)
        set_angle_smooth(v_servo, v_current_angle, 110)
        time.sleep(0.5)
        
        # De-energize servos by setting pulse width to 0
        # This removes the holding torque and allows free movement
        pwm.channels[h_servo_channel].duty_cycle = 0
        pwm.channels[v_servo_channel].duty_cycle = 0
        
        pwm.deinit()
        cv2.destroyAllWindows()
        picam2.stop()
        print("Cleanup complete")

# Run the function
if __name__ == "__main__":
    dual_servo_face_tracking()

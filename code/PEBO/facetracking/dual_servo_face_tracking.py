import cv2
import mediapipe as mp
import RPi.GPIO as GPIO
from picamera2 import Picamera2
import time

def dual_servo_face_tracking():
    # Setup GPIO
    GPIO.setwarnings(False)
    h_servo_pin = 23  # Horizontal
    v_servo_pin = 24  # Vertical
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(h_servo_pin, GPIO.OUT)
    GPIO.setup(v_servo_pin, GPIO.OUT)
    h_pwm = GPIO.PWM(h_servo_pin, 50)
    v_pwm = GPIO.PWM(v_servo_pin, 50)
    h_pwm.start(0)
    v_pwm.start(0)

    # Initialize camera
    picam2 = Picamera2()
    picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
    picam2.start()

    # Initialize MediaPipe
    mp_face = mp.solutions.face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5)

    # Frame dimensions
    width, height = 640, 480

    h_partition_angles = {1: 110, 2: 105, 3: 100, 4: 90, 5: 80, 6: 75, 7: 70}
    v_partition_angles = {1: 130, 2: 100, 3: 90}
    h_partition_boundaries = [(0, 70, 1), (90, 160, 2), (180, 250, 3), (270, 370, 4),
                              (390, 460, 5), (480, 550, 6), (570, 640, 7)]
    v_partition_boundaries = [(0, 120, 1), (170, 290, 2), (340, 480, 3)]

    h_current_angle = 90
    v_current_angle = 70
    h_current_partition = 4
    v_current_partition = 2
    last_detection_time = time.time()
    face_timeout = 1.0

    def set_angle_smooth(pwm_obj, current_angle, target_angle, step=2):
        if current_angle == target_angle:
            return current_angle
        direction = 1 if target_angle > current_angle else -1
        for angle in range(current_angle, target_angle + direction, direction):
            duty = (angle / 18.0) + 2.5
            pwm_obj.ChangeDutyCycle(duty)
            time.sleep(0.05)
        duty = (target_angle / 18.0) + 2.5
        pwm_obj.ChangeDutyCycle(duty)
        time.sleep(0.01)
        pwm_obj.ChangeDutyCycle(0)
        return target_angle

    def get_partition(position, boundaries):
        for start, end, partition in boundaries:
            if start <= position <= end:
                return partition, False
        return None, True

    try:
        print("Dual servo face tracking started. Press ESC to exit.")
        h_current_angle = set_angle_smooth(h_pwm, 90, h_current_angle)
        v_current_angle = set_angle_smooth(v_pwm, 70, v_current_angle)

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

            if results.detections:
                detection = results.detections[0]
                bbox = detection.location_data.relative_bounding_box
                x = int(bbox.xmin * width)
                y = int(bbox.ymin * height)
                w = int(bbox.width * width)
                h = int(bbox.height * height)
                cx, cy = x + w // 2, y + h // 2
                h_partition, h_in_gap = get_partition(cx, h_partition_boundaries)
                v_partition, v_in_gap = get_partition(cy, v_partition_boundaries)

                face_detected = True
                last_detection_time = current_time

                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

                if not h_in_gap and h_partition != h_current_partition:
                    h_target_angle = h_partition_angles[h_partition]
                    #print(f"Moving H servo: Partition {h_partition}, Angle {h_target_angle}°")
                    h_current_angle = set_angle_smooth(h_pwm, h_current_angle, h_target_angle)
                    h_current_partition = h_partition

                if not v_in_gap and v_partition != v_current_partition:
                    v_target_angle = v_partition_angles[v_partition]
                    #print(f"Moving V servo: Partition {v_partition}, Angle {v_target_angle}°")
                    v_current_angle = set_angle_smooth(v_pwm, v_current_angle, v_target_angle)
                    v_current_partition = v_partition

            elif current_time - last_detection_time > face_timeout:
                if h_current_angle != 90 or v_current_angle != 90:
                    #print("No face detected, returning to center position")
                    h_current_angle = set_angle_smooth(h_pwm, h_current_angle, 90)
                    v_current_angle = set_angle_smooth(v_pwm, v_current_angle, 90)
                    h_current_partition = 4
                    v_current_partition = 2
                cv2.putText(frame, "No face detected", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            # Annotations
            cv2.putText(frame, f"H Angle: {h_current_angle}°, Partition: {h_current_partition}",
                        (width - 300, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            cv2.putText(frame, f"V Angle: {v_current_angle}°, Partition: {v_current_partition}",
                        (width - 300, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            cv2.putText(frame, "Dual Servo Face Tracking", (width//2 - 150, height - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            #cv2.imshow("Face Tracking", frame)

            if cv2.waitKey(1) & 0xFF == 27:
                break
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("Program interrupted by user")

    finally:
        print("Returning servos to safe position (H:90°, V:70°)")
        set_angle_smooth(h_pwm, h_current_angle, 90)
        set_angle_smooth(v_pwm, v_current_angle, 70)
        time.sleep(0.5)
        h_pwm.stop()
        v_pwm.stop()
        GPIO.cleanup()
        cv2.destroyAllWindows()
        picam2.stop()
        print("Cleanup complete")

# Run the function
if __name__ == "__main__":
    dual_servo_face_tracking()

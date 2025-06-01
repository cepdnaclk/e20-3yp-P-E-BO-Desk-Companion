import threading
import time
import asyncio
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
from display.eyes import RoboEyesDual
from facetracking.face_tracking import CombinedFaceTracking
from interaction.touch_sensor import detect_continuous_touch
from arms.arms_pwm import say_hi
from recognition.person_recognition import recognize_image 
from assistant import monitor_for_trigger, monitor_start

# Initialize I2C and PCA9685 PWM controller
i2c = busio.I2C(board.SCL, board.SDA)
pwm = PCA9685(i2c)
pwm.frequency = 50  # Standard servo frequency (50Hz)

# Shared variable for recognition result with thread-safe access
recognition_result = {"name": "NONE", "emotion": "NONE"}
result_lock = threading.Lock()

def run_eye_display():
    eyes = RoboEyesDual(left_address=0x3D, right_address=0x3C)
    eyes.begin(128, 64, 50)
    eyes.Default()

def run_face_tracking():
    tracker = CombinedFaceTracking()
    tracker.run()

def run_say_hi_once():
    say_hi()

def run_periodic_recognition():
    global recognition_result
    while True:
        print("🔍 Running periodic recognition...")
        result = recognize_image()
        print(f"Recognition Result: {result}")
        with result_lock:
            recognition_result = result  # Update shared result
        time.sleep(5)

def run_voice_monitoring():
    """Run the voice monitoring loop in a separate thread, using emotion from periodic recognition."""
    valid_emotions = {"SAD", "HAPPY", "CONFUSED", "FEAR", "ANGRY"}
    
    while True:
        try:
            # Get the latest recognition result
            with result_lock:
                user = recognition_result.get("name", "NONE")
                emotion = recognition_result.get("emotion", "NONE").upper()
            print(f"[Voice] Using Recognition Result: name={user}, emotion={emotion}")

            # Decide which monitor function to run based on emotion
            if emotion in valid_emotions:
                print(f"[Voice] Detected emotion {emotion}, running monitor_start...")
                asyncio.run(monitor_start(user, emotion))
            else:
                print(f"[Voice] Emotion {emotion} not in valid emotions, running monitor_for_trigger...")
                asyncio.run(monitor_for_trigger(user, emotion))

            # Brief pause before next iteration to avoid overwhelming the system
            time.sleep(1)
        except Exception as e:
            print(f"[Voice] Error: {e}")
            time.sleep(5)  # Wait before retrying on error

def stop_servo(servo_channel):
    """Stop a servo by setting duty cycle to 0."""
    try:
        pwm.channels[servo_channel].duty_cycle = 0
        print(f"Servo channel {servo_channel} de-energized")
    except Exception as e:
        print(f"Error stopping servo channel {servo_channel}: {e}")

def cleanup():
    """Clean up servo resources for channels 0, 1, 4, 6, and 7."""
    print("Returning servos to safe positions...")
    servo_channels = [0, 1, 4, 6, 7]  # Channels to clean up
    safe_angle = 90  # Safe position for all servos

    try:
        # Initialize servos for all specified channels
        servos = {ch: servo.Servo(pwm.channels[ch]) for ch in servo_channels}

        # Smoothly move servos to safe position
        for ch, servo_obj in servos.items():
            try:
                current_angle = servo_obj.angle if servo_obj.angle is not None else safe_angle
                if current_angle != safe_angle:
                    direction = 1 if safe_angle > current_angle else -1
                    for angle in range(int(current_angle), safe_angle + direction, direction):
                        servo_obj.angle = angle
                        time.sleep(0.02)  # Slower movement for cleanup
                    servo_obj.angle = safe_angle
                print(f"Servo channel {ch} moved to safe position {safe_angle}°")
            except Exception as e:
                print(f"Error moving servo channel {ch} to safe position: {e}")

        # Wait to ensure servos reach their positions
        time.sleep(1.0)

        # De-energize all servos
        for ch in servo_channels:
            stop_servo(ch)

    except Exception as e:
        print(f"Error during servo cleanup: {e}")

    # De-initialize PWM and I2C
    try:
        pwm.deinit()
        i2c.deinit()
        print("PWM and I2C de-initialized")
    except Exception as e:
        print(f"Error de-initializing PWM/I2C: {e}")

def main():
    print("🕹️ Waiting for 3-second touch to begin...")
    if detect_continuous_touch(duration=3):
        print("✅ Touch confirmed. Starting recognition...")
        
        # Start eyes, face tracking, arm wave, periodic recognition, and voice monitoring simultaneously
        #threading.Thread(target=run_eye_display, daemon=True).start()
        threading.Thread(target=run_face_tracking, daemon=True).start()
        #threading.Thread(target=run_say_hi_once, daemon=True).start()
        threading.Thread(target=run_periodic_recognition, daemon=True).start()
        threading.Thread(target=run_voice_monitoring, daemon=True).start()

        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("🛑 Exiting...")
            cleanup()  # Perform servo cleanup on exit

if __name__ == "__main__":
    main()

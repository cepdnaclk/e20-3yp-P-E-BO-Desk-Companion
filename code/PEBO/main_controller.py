import threading
import time
from display.eyes import RoboEyesDual
from facetracking.face_tracking import CombinedFaceTracking
from interaction.touch_sensor import detect_continuous_touch
from arms.arms_pwm import say_hi
from recognition.person_recognition import recognize_from_existing_image  # Adjust if your function is in a different file

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
    while True:
        print("🔍 Running periodic recognition...")
        result = recognize_from_existing_image()
        print(f"Recognition Result: {result}")
        time.sleep(20)

def main():
    print("🕹️ Waiting for 3-second touch to begin...")
    if detect_continuous_touch(duration=3):
        print("✅ Touch confirmed. Starting display, face tracking, arm wave, and periodic recognition...")

        # Start eyes, facetracking, and arm wave all simultaneously
        threading.Thread(target=run_eye_display, daemon=True).start()
        threading.Thread(target=run_face_tracking, daemon=True).start()
        threading.Thread(target=run_say_hi_once, daemon=True).start()

        # Start periodic recognition every 20 seconds
        threading.Thread(target=run_periodic_recognition, daemon=True).start()

        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("🛑 Exiting...")

if __name__ == "__main__":
    main()
c

import threading
from display.eyes import RoboEyesDual
from facetracking.face_tracking import CombinedFaceTracking
from interaction.touch_sensor import detect_continuous_touch
from arms.arms_pwm import say_hi

def run_eye_display():
    eyes = RoboEyesDual(left_address=0x3D, right_address=0x3C)
    eyes.begin(128, 64, 50)
    eyes.Default()

def run_face_tracking():
    tracker = CombinedFaceTracking()
    tracker.run()

def run_say_hi_once():
    say_hi()

def main():
    print("?? Waiting for 3-second touch to begin...")
    if detect_continuous_touch(duration=3):
        print("? Touch confirmed. Starting display, face tracking, and arm wave...")

        # Start eyes, facetracking, and arm wave all simultaneously
        threading.Thread(target=run_eye_display, daemon=True).start()
        threading.Thread(target=run_face_tracking, daemon=True).start()
        threading.Thread(target=run_say_hi_once, daemon=True).start()

        # Keep the main thread alive
        try:
            while True:
                pass
        except KeyboardInterrupt:
            print("?? Exiting...")

if __name__ == "__main__":
    main()

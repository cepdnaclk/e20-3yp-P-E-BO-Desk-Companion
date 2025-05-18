import threading
import time
import asyncio
from interaction.touch_sensor import detect_continuous_touch
from display.eyes import RoboEyesDual
from facetrack.dual_servo_face_tracking import dual_servo_face_tracking
from interaction.user_check import recognize_person
from voice.assistant import speak_text, listen, start_assistant_from_text

# Control flags and threads
is_running = False
eye_thread = None
face_thread = None

def run_blinking_neutral_eyes():
    eyes = RoboEyesDual(left_address=0x3C, right_address=0x3D)
    eyes.begin(128, 64, 50)
    eyes.set_autoblinker(True, 5, 1)
    eyes.set_mood(0)

    try:
        while is_running:
            eyes.update()
            time.sleep(0.01)
    except Exception as e:
        print(f"[Eyes] Error: {e}")
    finally:
        eyes.display_left.fill(0)
        eyes.display_left.show()
        eyes.display_right.fill(0)
        eyes.display_right.show()
        print("[Eyes] Display cleared.")

def start_pebo_services():
    global eye_thread, face_thread, is_running
    is_running = True

    eye_thread = threading.Thread(target=run_blinking_neutral_eyes)
    eye_thread.start()

    face_thread = threading.Thread(target=dual_servo_face_tracking)
    face_thread.start()

    print("? PEBO is active.")

def stop_pebo_services():
    global is_running
    is_running = False
    print("?? Stopping PEBO... Waiting for threads to shut down.")
    time.sleep(1.5)

def main():
    global is_running

    print("?? Hold PEBO's head for 3 seconds to begin...")

    try:
        while True:
            if detect_continuous_touch(3):
                print("?? Capturing image and checking user identity...")
                result = recognize_person()

                if result.get("name"):
                    name = result["name"]
                    emotion = result.get("emotion", "neutral")
                    print(f"? Recognized: {name} | Emotion: {emotion}")
                    time.sleep(2)
                    start_pebo_services()

                    # Start assistant loop with prompt
                    assistant_prompt = f"I am {name}, I look like {emotion}. Ask why."
                    asyncio.run(start_assistant_from_text(assistant_prompt))
                else:
                    print("? User not recognized. Try again later.")
                    continue

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[PEBO] Interrupted by user.")
        if is_running:
            stop_pebo_services()

if __name__ == "__main__":
    main()
 
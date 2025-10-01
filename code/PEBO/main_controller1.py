#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main controller for PEBO

- Starts face tracking, periodic recognition, voice assistant loop, touch-to-shutdown, and reminders.
- Writes recognition_result.txt for assistant to react silently with eyes/arms while TTS stays ~25 tokens.
- Uses safe cleanup for PWM, I2C, and GPIO even if errors occur.
"""

import logging
import time
import threading
import asyncio
import os

import board
import busio
import RPi.GPIO as GPIO

from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

# Optional display import if used elsewhere (eyes are driven inside assistant module)
# from display.eyes import RoboEyesDual

from facetracking.face_tracking_qr import CombinedFaceTracking
from interaction.touch_sensor import detect_continuous_touch
from arms.arms_pwm import say_hi  # kept if needed for quick gestures elsewhere
from recognition.person_recognition import recognize_image
from assistant_combined1 import monitor_new  # async assistant loop that reads recognition_result.txt
from ipconfig.qr_reader import run_qr_scanner  # imported if started elsewhere
from reminders.reminders_1 import reminder_loop


# main_controller1.py (top-level toggles)
SKIP_USER_CHECK = bool(int(os.getenv("PEBO_SKIP_USER_CHECK", "1")))

# ---------------------------
# Logging
# ---------------------------
LOG_FILE = '/home/pi/main_controller.log'
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logging.getLogger().addHandler(console)
logging.info("Main controller started at %s", time.strftime("%Y-%m-%d %H:%M:%S"))

# ---------------------------
# I2C and PWM init (Servos)
# ---------------------------
i2c = busio.I2C(board.SCL, board.SDA)
pwm = PCA9685(i2c)
pwm.frequency = 50  # Standard servo frequency (50Hz)

# ---------------------------
# Recognition shared state
# ---------------------------
recognition_result = {"name": "NONE", "emotion": "NONE"}
result_lock = threading.Lock()

# ---------------------------
# Fallback exception mapping
# ---------------------------
try:
    # If a specific NoAudioReceived exists in the stack, alias it; otherwise define a local one
    from speech_recognition import WaitTimeoutError as NoAudioReceived  # best-effort fallback
except Exception:
    class NoAudioReceived(Exception):
        """Raised when no audio is captured."""
        pass

# ---------------------------
# Servo helpers
# ---------------------------
def stop_servo(servo_channel: int):
    """Stop a servo by setting duty cycle to 0."""
    try:
        pwm.channels[servo_channel].duty_cycle = 0
        print(f"Servo channel {servo_channel} de-energized")
    except Exception as e:
        print(f"Error stopping servo channel {servo_channel}: {e}")

def clamp_angle(val, lo=0, hi=180):
    try:
        return max(lo, min(hi, int(val)))
    except Exception:
        return lo

def cleanup():
    """Clean up servo resources for channels 0, 1, 5, 6, and 7."""
    print("Returning servos to safe positions...")
    servo_channels = [0, 1, 5, 6, 7]
    safe_angle = 90

    try:
        # Initialize servo objects per channel (best-effort)
        servos = {}
        for ch in servo_channels:
            try:
                servos[ch] = servo.Servo(pwm.channels[ch])
            except Exception as e:
                servos[ch] = None
                logging.error("Init servo channel %s failed: %s", ch, e)

        # Move each servo smoothly to safe position
        for ch, s in servos.items():
            if s is None:
                continue
            try:
                current_angle = s.angle if s.angle is not None else safe_angle
                current_angle = clamp_angle(current_angle)
                target = clamp_angle(safe_angle)
                step = 1 if target >= current_angle else -1
                for ang in range(int(current_angle), int(target) + step, step):
                    s.angle = ang
                    time.sleep(0.02)
                s.angle = target
                print(f"Servo channel {ch} moved to safe position {target}\N{DEGREE SIGN}")
            except Exception as e:
                logging.error("Error moving servo channel %s to safe position: %s", ch, e)

        time.sleep(0.5)

        # Stop PWM signals to servos (per-channel best-effort)
        for ch in servo_channels:
            try:
                stop_servo(ch)
            except Exception as e:
                logging.error("Error stopping servo channel %s: %s", ch, e)

    except Exception as e:
        logging.exception("Error during servo cleanup: %s", e)
    finally:
        # Deinitialize hardware independently so one failure doesn't block others
        try:
            pwm.deinit()
            print("PWM de-initialized")
        except Exception as e:
            logging.error("Error de-initializing PWM: %s", e)

        try:
            i2c.deinit()
            print("I2C de-initialized")
        except Exception as e:
            logging.error("Error de-initializing I2C: %s", e)

        try:
            GPIO.cleanup()
        except Exception as e:
            logging.error("Error during GPIO cleanup: %s", e)

# ---------------------------
# Workers
# ---------------------------
def run_face_tracking():
    """Start combined face tracking pipeline."""
    try:
        tracker = CombinedFaceTracking()
        tracker.run()
    except Exception as e:
        logging.exception("Face tracking crashed: %s", e)

def run_periodic_recognition():
    """Run periodic face recognition and save results to recognition_result.txt for assistant."""
    global recognition_result
    file_path = "/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/recognition_result.txt"
    while True:
        try:
            print("🔍 Running periodic recognition...")
            result = recognize_image()
            print(f"Recognition Result: {result}")
            with result_lock:
                recognition_result = result or {}
                try:
                    name = recognition_result.get("name", "NONE")
                    emotion = recognition_result.get("emotion", "NONE")
                    with open(file_path, 'w', encoding="utf-8") as file:
                        file.write(f"Name: {name}\nEmotion: {emotion}\n")
                    print(f"📝 Saved to {file_path}: Name={name}, Emotion={emotion}")
                except IOError as e:
                    print(f"× Error writing to {file_path}: {e}")
                except Exception as e:
                    print(f"× Unexpected error writing to {file_path}: {e}")
        except Exception as e:
            print(f"× Error in periodic recognition: {e}")
        time.sleep(0.5)  # 0.5s cadence

def run_voice_monitoring():
    """Run the voice monitoring loop in a separate thread."""
    try:
        asyncio.run(monitor_new())
    except NoAudioReceived:
        logging.exception("No audio received in assistant monitor_new")
    except Exception as e:
        logging.exception("Assistant monitor_new crashed: %s", e)

def shutdown_on_touch():
    """Monitor for a 5-second touch to clean up and shut down the Raspberry Pi."""
    print("🖐️ Monitoring for 5-second touch to shut down...")
    try:
        if detect_continuous_touch(duration=5):
            print("✅ 5-second touch detected. Cleaning up and shutting down...")
            logging.info("5-second touch detected, initiating shutdown at %s", time.strftime("%Y-%m-%d %H:%M:%S"))
            cleanup()
            try:
                os.system("sudo shutdown -h now")
            except Exception as e:
                logging.error("Shutdown command failed: %s", e)
    except Exception as e:
        logging.exception("shutdown_on_touch loop failed: %s", e)

# ---------------------------
# Main
# ---------------------------
def main():
    print("✅ Starting main controller...")
    logging.info("Main controller launching worker threads...")

    # Workers
    threading.Thread(target=run_face_tracking, daemon=True).start()
    if not SKIP_USER_CHECK:
        threading.Thread(target=run_periodic_recognition, daemon=True).start()
    threading.Thread(target=run_voice_monitoring, daemon=True).start()
    threading.Thread(target=shutdown_on_touch, daemon=True).start()


    # Stagger reminders to allow Firebase init by assistant
    print("⏳ Waiting 20 seconds for Firebase initialization before starting reminder loop...")
    logging.info("Waiting 20 seconds for Firebase initialization before starting reminder loop")
    time.sleep(20)

    print("🚀 Starting reminder loop...")
    logging.info("Starting reminder loop")
    threading.Thread(target=lambda: asyncio.run(reminder_loop()), daemon=True).start()

    # Keep main alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛠️ Exiting via KeyboardInterrupt...")
        cleanup()
        logging.info("Main controller stopped via KeyboardInterrupt at %s", time.strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
    main()

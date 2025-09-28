#!/usr/bin/env python3

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

from facetracking.face_tracking_qr import CombinedFaceTracking
from interaction.touch_sensor import detect_continuous_touch
from recognition.person_recognition import recognize_image
from assistant_combined1 import monitor_new
from edge_tts.exceptions import NoAudioReceived 
from reminders.reminders_1 import reminder_loop

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------
logging.basicConfig(
    filename='/home/pi/main_controller.log',
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logging.getLogger().addHandler(console)
logging.info("Main controller starting...")

# ------------------------------------------------------------------------------
# GPIO: set numbering mode ONCE before any threads
# ------------------------------------------------------------------------------
TOUCH_PIN = 17  # must match the pin used inside interaction.touch_sensor
GPIO.setwarnings(False)
if not GPIO.getmode():
    GPIO.setmode(GPIO.BCM)
GPIO.setup(TOUCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# ------------------------------------------------------------------------------
# I2C + PCA9685 (servos)
# ------------------------------------------------------------------------------
i2c = busio.I2C(board.SCL, board.SDA)
pwm = PCA9685(i2c)
pwm.frequency = 50  # 50 Hz for standard servos

# ------------------------------------------------------------------------------
# Shared face recognition result (optional)
# ------------------------------------------------------------------------------
recognition_result = {"name": "NONE", "emotion": "NONE"}
result_lock = threading.Lock()

# ------------------------------------------------------------------------------
# Thread targets with error isolation
# ------------------------------------------------------------------------------
def run_face_tracking():
    log = logging.getLogger("face_tracking")
    try:
        tracker = CombinedFaceTracking()
        tracker.run()
    except Exception as e:
        log.exception(f"Face tracking crashed: {e}")

def run_periodic_recognition():
    """
    Optional: periodic face recognition writing Name/Emotion into a file
    used by the voice assistant. Disabled by default (thread not started).
    """
    log = logging.getLogger("periodic_recognition")
    global recognition_result
    file_path = "/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/recognition_result.txt"

    while True:
        try:
            print("Running periodic recognition...")
            result = recognize_image()
            print(f"Recognition Result: {result}")

            with result_lock:
                recognition_result = result

                try:
                    name = result.get("name", "NONE")
                    emotion = result.get("emotion", "NONE")
                    with open(file_path, 'w') as f:
                        f.write(f"Name: {name}\nEmotion: {emotion}\n")
                    print(f"Saved to {file_path}: Name={name}, Emotion={emotion}")
                except Exception as write_err:
                    log.error(f"Error writing recognition result: {write_err}")

        except Exception as e:
            log.exception(f"Error in periodic recognition: {e}")

        time.sleep(0.5)

def run_voice_monitoring():
    log = logging.getLogger("voice_monitor")
    try:
         asyncio.run(monitor_new())
    except Exception as e:
        log.exception(f"Voice monitoring crashed: {e}")

def stop_servo(servo_channel: int):
    try:
        pwm.channels[servo_channel].duty_cycle = 0
        print(f"Servo channel {servo_channel} de-energized")
    except Exception as e:
        print(f"Error stopping servo channel {servo_channel}: {e}")

def cleanup():
    """
    Move servos to a safe angle and de-energize, then deinit PWM and I2C.
    Do NOT call GPIO.cleanup() here because other threads may still use GPIO.
    """
    print("Returning servos to safe positions...")
    servo_channels = [0, 1, 5, 6, 7]
    safe_angle = 90

    try:
        servos = {ch: servo.Servo(pwm.channels[ch]) for ch in servo_channels}

        for ch, servo_obj in servos.items():
            try:
                current_angle = servo_obj.angle if servo_obj.angle is not None else safe_angle
                if current_angle != safe_angle:
                    step = 1 if safe_angle > current_angle else -1
                    for angle in range(int(current_angle), safe_angle + step, step):
                        servo_obj.angle = angle
                        time.sleep(0.02)
                    servo_obj.angle = safe_angle
                print(f"Servo channel {ch} moved to safe position {safe_angle}°")
            except Exception as e:
                print(f"Error moving servo channel {ch} to safe position: {e}")

        time.sleep(1.0)
        for ch in servo_channels:
            stop_servo(ch)

    except Exception as e:
        print(f"Error during servo cleanup: {e}")

    try:
        pwm.deinit()
        i2c.deinit()
        print("PWM and I2C de-initialized")
    except Exception as e:
        print(f"Error de-initializing PWM/I2C: {e}")

def shutdown_on_touch():
    """
    Monitor for a 5-second touch to trigger cleanup and shutdown.
    Requires GPIO mode to be set at process start (done above).
    """
    log = logging.getLogger("shutdown_touch")
    print("Monitoring for 5-second touch to shut down...")
    try:
        if detect_continuous_touch(duration=5):
            print("5-second touch detected. Cleaning up and shutting down...")
            log.info("5-second touch detected, initiating shutdown...")
            cleanup()
            try:
                os.system("sudo shutdown -h now")
            except Exception as e:
                print(f"Error during shutdown: {e}")
                log.error(f"Error during shutdown: {e}")
    except Exception as e:
        log.exception(f"Touch monitor crashed: {e}")

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
def main():
    print("Starting main controller...")

    # Start the long-running components
    threading.Thread(target=run_face_tracking, name="FaceTracking", daemon=True).start()
    # threading.Thread(target=run_periodic_recognition, name="PeriodicRecognition", daemon=True).start()
    threading.Thread(target=run_voice_monitoring, name="VoiceMonitor", daemon=True).start()
    threading.Thread(target=shutdown_on_touch, name="ShutdownTouch", daemon=True).start()

    # Allow face tracking time to initialize Firebase before reminders
    print("Waiting 20 seconds for Firebase initialization before starting reminder loop...")
    logging.info("Waiting 20 seconds for Firebase initialization before starting reminder loop")
    time.sleep(20)
    print("Starting reminder loop...")
    logging.info("Starting reminder loop")

    def _run_reminders():
        log = logging.getLogger("reminders")
        try:
            asyncio.run(reminder_loop())
        except Exception as e:
            log.exception(f"Reminder loop crashed: {e}")

    threading.Thread(target=_run_reminders, name="Reminders", daemon=True).start()

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting via KeyboardInterrupt...")
        cleanup()
        logging.info("Main controller stopped via KeyboardInterrupt")

if __name__ == "__main__":
    main()

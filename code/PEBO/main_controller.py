#!/usr/bin/env python3

import logging
import time
import threading
import asyncio
import board
import busio
import os
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
from display.eyes import RoboEyesDual
from facetracking.face_tracking_qr_hi import CombinedFaceTracking
from interaction.touch_sensor import detect_continuous_touch
from arms.arms_pwm import say_hi
from recognition.person_recognition import recognize_image 
from assistant_combined import monitor_for_trigger, monitor_start, monitor_new
from ipconfig.qr_reader import run_qr_scanner
from reminders.reminders_1 import reminder_loop
from edge_tts.exceptions import NoAudioReceived  # add this with your imports

# Initialize logging
logging.basicConfig(filename='/home/pi/main_controller.log', level=logging.DEBUG)
logging.info("Main controller started at %s", time.strftime("%Y-%m-%d %H:%M:%S"))

# Initialize I2C and PCA9685 PWM controller
i2c = busio.I2C(board.SCL, board.SDA)
pwm = PCA9685(i2c)
pwm.frequency = 50  # Standard servo frequency (50Hz)

# Shared variable for recognition result with thread-safe access
recognition_result = {"name": "NONE", "emotion": "NONE"}
result_lock = threading.Lock()

def run_face_tracking():
    tracker = CombinedFaceTracking()
    tracker.run()

def run_periodic_recognition():
    """Run periodic face recognition and save results to recognition_result.txt."""
    global recognition_result
    file_path = "/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/recognition_result.txt"
    
    while True:
        try:
            print("🔍 Running periodic recognition...")
            result = recognize_image()
            print(f"Recognition Result: {result}")
            
            # Update shared result with thread-safe access
            with result_lock:
                recognition_result = result
                
                # Save result to file
                try:
                    name = result.get("name", "NONE")
                    emotion = result.get("emotion", "NONE")
                    with open(file_path, 'w') as file:
                        file.write(f"Name: {name}\nEmotion: {emotion}\n")
                    print(f"📝 Saved to {file_path}: Name={name}, Emotion={emotion}")
                except IOError as e:
                    print(f"❌ Error writing to {file_path}: {e}")
                except Exception as e:
                    print(f"❌ Unexpected error writing to {file_path}: {e}")
                    
        except Exception as e:
            print(f"❌ Error in periodic recognition: {e}")
        
        time.sleep(0.5)  # Wait 0.5 seconds before next recognition

def run_voice_monitoring():
    """Run the voice monitoring loop in a separate thread, using emotion from periodic recognition."""
    asyncio.run(monitor_new())

def stop_servo(servo_channel):
    """Stop a servo by setting duty cycle to 0."""
    try:
        pwm.channels[servo_channel].duty_cycle = 0
        print(f"Servo channel {servo_channel} de-energized")
    except Exception as e:
        print(f"Error stopping servo channel {servo_channel}: {e}")

def cleanup():
    """Clean up servo resources for channels 0, 1, 5, 6, and 7."""
    print("Returning servos to safe positions...")
    servo_channels = [0, 1, 5, 6, 7]  # Channels to clean up
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

def shutdown_on_touch():
    """Monitor for a 5-second touch to clean up and shut down the Raspberry Pi."""
    print("🖐️ Monitoring for 5-second touch to shut down...")
    if detect_continuous_touch(duration=5):
        print("✅ 5-second touch detected. Cleaning up and shutting down...")
        logging.info("5-second touch detected, initiating shutdown at %s", time.strftime("%Y-%m-%d %H:%M:%S"))
        cleanup()  # Perform servo cleanup
        # Initiate Raspberry Pi shutdown
        try:
            os.system("sudo shutdown -h now")
        except Exception as e:
            print(f"❌ Error during shutdown: {e}")
            logging.error("Error during shutdown: %s", e)

def main():
    print("✅ Starting main controller...")
    
    # Start eyes, face tracking, periodic recognition, voice monitoring, and shutdown monitor immediately
    threading.Thread(target=run_face_tracking, daemon=True).start()
    #threading.Thread(target=run_periodic_recognition, daemon=True).start()
    threading.Thread(target=run_voice_monitoring, daemon=True).start()
    threading.Thread(target=shutdown_on_touch, daemon=True).start()

    # Delay starting the reminder loop to allow Firebase initialization by face tracking
    print("⏳ Waiting 20 seconds for Firebase initialization before starting reminder loop...")
    logging.info("Waiting 20 seconds for Firebase initialization before starting reminder loop")
    time.sleep(20)
    print("🚀 Starting reminder loop...")
    logging.info("Starting reminder loop")
    threading.Thread(target=lambda: asyncio.run(reminder_loop()), daemon=True).start()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Exiting via KeyboardInterrupt...")
        cleanup()  # Perform servo cleanup on manual exit
        logging.info("Main controller stopped via KeyboardInterrupt at %s", time.strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
    main()

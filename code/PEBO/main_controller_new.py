#!/usr/bin/env python3

import logging
import time
import threading
import asyncio
import board
import busio
import os
import random
import edge_tts
import pygame
import RPi.GPIO as GPIO
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
from display.eyes import RoboEyesDual
from facetracking.face_tracking_qy_hi import CombinedFaceTracking
from arms.arms_pwm import say_hi
from recognition.person_recognition import recognize_image 
from assistant_combined import monitor_for_trigger, monitor_start, monitor_new
from ipconfig.qr_reader import run_qr_scanner
from reminders.reminders_1 import reminder_loop
from edge_tts.exceptions import NoAudioReceived

# Initialize logging
logging.basicConfig(filename='/home/pi/main_controller.log', level=logging.DEBUG)
logging.info("Main controller started at %s", time.strftime("%Y-%m-%d %H:%M:%S"))

# Initialize I2C and PCA9685 PWM controller
i2c = busio.I2C(board.SCL, board.SDA)
pwm = PCA9685(i2c)
pwm.frequency = 50

# Initialize eyes
LEFT_EYE_ADDRESS = 0x3C
RIGHT_EYE_ADDRESS = 0x3D
eyes = RoboEyesDual(LEFT_EYE_ADDRESS, RIGHT_EYE_ADDRESS)
eyes.begin(128, 64, 40)

# GPIO pin for touch sensor (BCM)
TOUCH_PIN = 17
MIN_TOUCH_DURATION = 0.5
SHUTDOWN_TOUCH_DURATION = 5.0

# Cute phrases for touch response
CUTE_PHRASES = [
    "Hehe, I love pets!",
    "Yay, you tickled me!",
    "Aww, thanks for the love!",
    "Ooh, that feels nice!",
    "Pet me more, please!",
    "You're so sweet to me!"
]

# Shared variable for recognition result
recognition_result = {"name": "NONE", "emotion": "NONE"}
result_lock = threading.Lock()

# Touch counter
touch_count = 0
touch_count_lock = threading.Lock()

def setup_touch_sensor():
    """Configure GPIO for touch sensor."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TOUCH_PIN, GPIO.IN)

def detect_continuous_touch():
    """
    Detect a touch and return its duration if >= 0.5 seconds.
    Returns 0 if touch is too short or no touch is detected.
    """
    if GPIO.input(TOUCH_PIN) == GPIO.HIGH:
        start_time = time.time()
        while GPIO.input(TOUCH_PIN) == GPIO.HIGH:
            time.sleep(0.01)
        duration = time.time() - start_time
        if duration >= MIN_TOUCH_DURATION:
            return duration
        return 0
    return 0

async def speak_text_async(text):
    """Speak text using edge-tts with en-US-AnaNeural voice."""
    voice = "en-US-AnaNeural"
    filename = "/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/response.mp3"
    boosted_file = "/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/boosted_response.mp3"
    try:
        tts = edge_tts.Communicate(text, voice)
        await tts.save(filename)
        from pydub import AudioSegment
        audio = AudioSegment.from_file(filename)
        boosted_audio = audio + 20
        boosted_audio.export(boosted_file, format="mp3")
        pygame.mixer.init()
        pygame.mixer.music.load(boosted_file)
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.25)
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        if os.path.exists(filename):
            os.remove(filename)
        if os.path.exists(boosted_file):
            os.remove(boosted_file)
    except NoAudioReceived as e:
        print(f"Error in speak_text: No audio received - {e}")
        logging.error("No audio received in speak_text: %s", e)
    except Exception as e:
        print(f"Error in speak_text: {e}")
        logging.error("Error in speak_text: %s", e)

def speak_text(text):
    """Run speak_text_async in a new event loop."""
    loop = asyncio.new_event_loop()
    loop.run_until_complete(speak_text_async(text))
    loop.close()

def handle_touch_response():
    """Trigger happy eyes and speak a cute phrase."""
    phrase = random.choice(CUTE_PHRASES)
    print(f"😊 Touch response: {phrase}")
    logging.info("Touch response: %s", phrase)
    
    # Run happy eyes
    stop_event = threading.Event()
    eye_thread = threading.Thread(target=eyes.Happy, args=(stop_event,))
    eye_thread.daemon = True
    eye_thread.start()
    
    # Speak phrase in parallel
    speech_thread = threading.Thread(target=speak_text, args=(phrase,))
    speech_thread.daemon = True
    speech_thread.start()
    
    # Wait for animation duration (2 seconds) then revert to default eyes
    time.sleep(2)
    stop_event.set()
    eye_thread.join(timeout=1.0)
    eyes.Default(threading.Event())

def run_face_tracking():
    tracker = CombinedFaceTracking()
    tracker.run()

def run_periodic_recognition():
    global recognition_result
    file_path = "/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/recognition_result.txt"
    while True:
        try:
            print("🔍 Running periodic recognition...")
            result = recognize_image()
            print(f"Recognition Result: {result}")
            with result_lock:
                recognition_result = result
                try:
                    name = result.get("name", "NONE")
                    emotion = result.get("emotion", "NONE")
                    with open(file_path, 'w') as file:
                        file.write(f"Name: {name}\nEmotion: {emotion}\n")
                    print(f"📝 Saved to {file_path}: Name={name}, Emotion={emotion}")
                except IOError as e:
                    print(f"❌ Error writing to {file_path}: {e}")
                    logging.error("Error writing to %s: %s", file_path, e)
                except Exception as e:
                    print(f"❌ Unexpected error writing to {file_path}: {e}")
                    logging.error("Unexpected error writing to %s: %s", file_path, e)
        except Exception as e:
            print(f"❌ Error in periodic recognition: {e}")
            logging.error("Error in periodic recognition: %s", e)
        time.sleep(0.5)

def run_voice_monitoring():
    asyncio.run(monitor_new())

def stop_servo(servo_channel):
    try:
        pwm.channels[servo_channel].duty_cycle = 0
        print(f"Servo channel {servo_channel} de-energized")
        logging.info("Servo channel %d de-energized", servo_channel)
    except Exception as e:
        print(f"Error stopping servo channel {servo_channel}: {e}")
        logging.error("Error stopping servo channel %d: %s", servo_channel, e)

def cleanup():
    print("Returning servos to safe positions...")
    logging.info("Returning servos to safe positions")
    servo_channels = [0, 1, 5, 6, 7]
    safe_angle = 90
    try:
        servos = {ch: servo.Servo(pwm.channels[ch]) for ch in servo_channels}
        for ch, servo_obj in servos.items():
            try:
                current_angle = servo_obj.angle if servo_obj.angle is not None else safe_angle
                if current_angle != safe_angle:
                    direction = 1 if safe_angle > current_angle else -1
                    for angle in range(int(current_angle), safe_angle + direction, direction):
                        servo_obj.angle = angle
                        time.sleep(0.02)
                    servo_obj.angle = safe_angle
                print(f"Servo channel {ch} moved to safe position {safe_angle}°")
                logging.info("Servo channel %d moved to safe position %d°", ch, safe_angle)
            except Exception as e:
                print(f"Error moving servo channel {ch} to safe position: {e}")
                logging.error("Error moving servo channel %d to safe position: %s", ch, e)
        time.sleep(1.0)
        for ch in servo_channels:
            stop_servo(ch)
    except Exception as e:
        print(f"Error during servo cleanup: {e}")
        logging.error("Error during servo cleanup: %s", e)
    try:
        eyes.display_left.fill(0)
        eyes.display_left.show()
        eyes.display_right.fill(0)
        eyes.display_right.show()
        print("Eyes cleared")
        logging.info("Eyes cleared")
    except Exception as e:
        print(f"Error clearing eyes: {e}")
        logging.error("Error clearing eyes: %s", e)
    try:
        pwm.deinit()
        i2c.deinit()
        print("PWM and I2C de-initialized")
        logging.info("PWM and I2C de-initialized")
    except Exception as e:
        print(f"Error de-initializing PWM/I2C: {e}")
        logging.error("Error de-initializing PWM/I2C: %s", e)
    try:
        GPIO.cleanup()
        print("GPIO cleaned up")
        logging.info("GPIO cleaned up")
    except Exception as e:
        print(f"Error cleaning up GPIO: {e}")
        logging.error("Error cleaning up GPIO: %s", e)

def monitor_touch():
    """Monitor touch sensor for 0.5s+ touches (happy response) and 5s touches (shutdown)."""
    setup_touch_sensor()
    global touch_count
    print("🖐️ Monitoring touch sensor for responses and shutdown...")
    logging.info("Monitoring touch sensor for responses and shutdown")
    while True:
        try:
            duration = detect_continuous_touch()
            if duration >= SHUTDOWN_TOUCH_DURATION:
                print(f"🛑 5-second touch detected ({duration:.1f}s). Cleaning up and shutting down...")
                logging.info("5-second touch detected (%.1fs), initiating shutdown", duration)
                with touch_count_lock:
                    touch_count += 1
                    print(f"Total touches: {touch_count}")
                    logging.info("Touch count updated: %d", touch_count)
                cleanup()
                os.system("sudo shutdown -h now")
                return
            elif duration >= MIN_TOUCH_DURATION:
                with touch_count_lock:
                    touch_count += 1
                    print(f"✋ Touch detected: {duration:.1f}s")
                    print(f"Total touches: {touch_count}")
                    logging.info("Touch detected: %.1fs, Total touches: %d", duration, touch_count)
                threading.Thread(target=handle_touch_response, daemon=True).start()
            time.sleep(0.1)  # Debounce
        except Exception as e:
            print(f"❌ Error in touch monitoring: {e}")
            logging.error("Error in touch monitoring: %s", e)
            time.sleep(0.1)

def main():
    print("✅ Starting main controller...")
    logging.info("Starting main controller")
    
    # Start all threads
    threading.Thread(target=run_face_tracking, daemon=True).start()
    #threading.Thread(target=run_periodic_recognition, daemon=True).start()
    threading.Thread(target=run_voice_monitoring, daemon=True).start()
    threading.Thread(target=monitor_touch, daemon=True).start()
    
    # Delay reminder loop for Firebase initialization
    print("⏳ Waiting 20 seconds for Firebase initialization...")
    logging.info("Waiting 20 seconds for Firebase initialization")
    time.sleep(20)
    print("🚀 Starting reminder loop...")
    logging.info("Starting reminder loop")
    threading.Thread(target=lambda: asyncio.run(reminder_loop()), daemon=True).start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Exiting via KeyboardInterrupt...")
        logging.info("Exiting via KeyboardInterrupt at %s", time.strftime("%Y-%m-%d %H:%M:%S"))
        cleanup()

if __name__ == "__main__":
    main()

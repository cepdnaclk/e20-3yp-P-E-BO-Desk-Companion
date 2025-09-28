#!/usr/bin/env python3
"""
Simplified Reminder Script for PEBO Desk Companion
Monitors Firebase tasks every minute, pauses main controller, plays a sound and speaks the task description,
repeats for 1 minute or until a double-tap is detected, then resumes main controller.
No arm or eye display interactions.
"""

import firebase_admin
from firebase_admin import credentials, db
import json
import asyncio
import pygame
import time
import os
import logging
import RPi.GPIO as GPIO
from datetime import datetime, timezone, timedelta
import dateutil.parser
import edge_tts
import subprocess

# Configuration
SERVICE_ACCOUNT_PATH = '/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/ipconfig/firebase_config.json'
DATABASE_URL = 'https://pebo-task-manager-767f3-default-rtdb.asia-southeast1.firebasedatabase.app/'
JSON_CONFIG_PATH = '/home/pi/pebo_config.json'
TOUCH_PIN = 17  # GPIO pin for touch sensor (Pin 11)
REMINDER_SOUND = '/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/reminders/reminder.wav'
LOG_FILE = '/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/ipconfig/reminder.log'
PAUSE_FILE = '/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/pause_main_controller.txt'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(TOUCH_PIN, GPIO.IN)

# Initialize pygame for sound
pygame.mixer.init()

async def speak_text(text):
    """Speak text using Edge TTS."""
    voice = "en-GB-SoniaNeural"
    filename = "response.mp3"
    boosted_file = "boosted_response.mp3"
    
    try:
        tts = edge_tts.Communicate(text, voice)
        await tts.save(filename)
        
        # Amplify audio
        subprocess.run([
            "ffmpeg", "-y", "-i", filename,
            "-filter:a", "volume=20dB",
            boosted_file
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        pygame.mixer.music.load(boosted_file)
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.25)
        
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        
        os.remove(filename)
        os.remove(boosted_file)
    except Exception as e:
        logger.error(f"Error in speak_text: {str(e)}")

def play_reminder_sound():
    """Play the reminder sound."""
    try:
        if not os.path.exists(REMINDER_SOUND):
            logger.error(f"Reminder sound file {REMINDER_SOUND} not found")
            return
        pygame.mixer.music.load(REMINDER_SOUND)
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.25)
        pygame.mixer.music.unload()
    except Exception as e:
        logger.error(f"Error playing reminder sound: {str(e)}")

def detect_double_tap(pin, timeout=0.5, max_taps=2):
    """Detect double-tap on the touch sensor."""
    tap_count = 0
    last_tap_time = 0
    start_time = time.time()
    
    while time.time() - start_time < timeout and tap_count < max_taps:
        if GPIO.input(pin) == GPIO.HIGH:
            current_time = time.time()
            if current_time - last_tap_time > 0.1:  # Debounce
                tap_count += 1
                last_tap_time = current_time
                logger.info(f"Tap detected: {tap_count}/{max_taps}")
            while GPIO.input(pin) == GPIO.HIGH:  # Wait for release
                time.sleep(0.01)
        time.sleep(0.01)
    
    return tap_count >= max_taps

def set_pause_flag(pause=True):
    """Set or clear the pause flag file to control main controller."""
    try:
        if pause:
            with open(PAUSE_FILE, 'w') as f:
                f.write("paused")
            logger.info("Main controller paused")
        else:
            if os.path.exists(PAUSE_FILE):
                os.remove(PAUSE_FILE)
                logger.info("Main controller resumed")
    except Exception as e:
        logger.error(f"Error setting pause flag: {str(e)}")

def fetch_user_tasks(user_id):
    """Fetch tasks from Firebase and return those with active reminders."""
    try:
        tasks_ref = db.reference(f'users/{user_id}/tasks')
        tasks = tasks_ref.get()
        if not tasks:
            logger.info(f"No tasks found for user {user_id}")
            return []

        current_time = datetime.now(timezone.utc)
        reminder_tasks = []

        for task_id, task_data in tasks.items():
            if task_data.get('completed', False) or not task_data.get('reminderEnabled', False):
                continue
                
            deadline_str = task_data.get('deadline')
            try:
                deadline = dateutil.parser.isoparse(deadline_str)
                reminder_time1 = task_data.get('reminderTime1')
                reminder_time2 = task_data.get('reminderTime2')
                
                # Check if current time is within 1 minute of reminder times
                for reminder_minutes in [reminder_time1, reminder_time2]:
                    if reminder_minutes:
                        reminder_time = deadline - timedelta(minutes=reminder_minutes)
                        time_diff = (current_time - reminder_time).total_seconds() / 60
                        if 0 <= time_diff <= 1:  # Within 1-minute window
                            description = task_data.get('description', 'No description')
                            time_remaining = (deadline - current_time).total_seconds() / 60
                            minutes_remaining = round(time_remaining) if time_remaining > 0 else 0
                            reminder_tasks.append({
                                'id': task_id,
                                'description': description,
                                'deadline': deadline,
                                'priority': task_data.get('priority', 'Unknown'),
                                'reminder_time': reminder_minutes,
                                'minutes_remaining': minutes_remaining
                            })
            except ValueError:
                logger.warning(f"Invalid deadline format for task {task_id}: {deadline_str}")
                continue

        return reminder_tasks
    except Exception as e:
        logger.error(f"Error fetching tasks for user {user_id}: {str(e)}")
        return []

async def reminder_loop():
    """Main loop to check Firebase for reminders every minute and pause/resume main controller."""
    # Initialize Firebase
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
            firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
            logger.info("Firebase initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {str(e)}")
        await speak_text("Sorry, I couldn't connect to the database.")
        return

    # Read user ID
    try:
        with open(JSON_CONFIG_PATH, 'r') as config_file:
            config = json.load(config_file)
            user_id = config.get('userId')
        if not user_id:
            logger.error("Missing userId in config file")
            await speak_text("Sorry, I couldn't find your user ID.")
            return
    except FileNotFoundError:
        logger.error(f"Config file {JSON_CONFIG_PATH} not found")
        await speak_text("Sorry, I couldn't read the user configuration.")
        return

    try:
        while True:
            logger.info("Checking for reminders...")
            tasks = fetch_user_tasks(user_id)
            
            if tasks:
                # Pause main controller
                set_pause_flag(pause=True)
                await asyncio.sleep(1)  # Ensure main controller detects pause

                for task in tasks:
                    logger.info(f"Reminder triggered for task: {task['description']}")
                    minutes_remaining = task['minutes_remaining']
                    reminder_message = f"Reminder: {task['description']} is due in {minutes_remaining} minute{'s' if minutes_remaining != 1 else ''}!"
                    
                    # Reminder loop for 1 minute
                    start_time = time.time()
                    max_duration = 60  # 1 minute in seconds
                    while time.time() - start_time < max_duration:
                        sound_task = asyncio.to_thread(play_reminder_sound)
                        speak_task = speak_text(reminder_message)
                        await asyncio.gather(sound_task, speak_task)
                        
                        if detect_double_tap(TOUCH_PIN):
                            logger.info("Double-tap detected, stopping reminder")
                            await speak_text(f"Reminder for {task['description']} stopped.")
                            break
                        await asyncio.sleep(5)  # Repeat every 5 seconds
                
                # Resume main controller
                set_pause_flag(pause=False)

            await asyncio.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        logger.info("Reminder loop interrupted by user")
    finally:
        # Clean up
        set_pause_flag(pause=False)  # Ensure main controller is resumed
        try:
            if firebase_admin._apps:
                firebase_admin.delete_app(firebase_admin.get_app())
                logger.info("Firebase app cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up Firebase app: {str(e)}")
        
        GPIO.cleanup()
        pygame.mixer.quit()
        logger.info("Program terminated")

if __name__ == "__main__":
    asyncio.run(reminder_loop())

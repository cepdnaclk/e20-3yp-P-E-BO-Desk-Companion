#!/usr/bin/env python3
"""
Simplified Reminder Script for PEBO Desk Companion
Monitors Firebase tasks every minute, writes the task description with time remaining to a text file for reminders.
No arm, eye display, or sound interactions.
"""

import firebase_admin
from firebase_admin import db
import json
import asyncio
import os
import logging
from datetime import datetime, timezone, timedelta
import dateutil.parser

# Configuration
JSON_CONFIG_PATH = '/home/pi/pebo_config.json'
LOG_FILE = '/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/ipconfig/reminder.log'
REMINDER_TEXT_FILE = '/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/reminders/reminder_output.txt'

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

def fetch_user_tasks(user_id):
    """Fetch tasks from Firebase and return those with active reminders, including time remaining."""
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
                            # Calculate time remaining until deadline
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
    """Main loop to check Firebase for reminders every minute and write to text file."""
    # Check if Firebase is initialized
    try:
        firebase_admin.get_app()  # Raises ValueError if no app is initialized
        logger.info("Using existing Firebase app")
    except ValueError:
        logger.error("Firebase app not initialized. Ensure CombinedFaceTracking initializes Firebase.")
        return

    # Read user ID
    try:
        with open(JSON_CONFIG_PATH, 'r') as config_file:
            config = json.load(config_file)
            user_id = config.get('userId')
        if not user_id:
            logger.error("Missing userId in config file")
            return
    except FileNotFoundError:
        logger.error(f"Config file {JSON_CONFIG_PATH} not found")
        return

    try:
        while True:
            logger.info("Checking for reminders...")
            tasks = fetch_user_tasks(user_id)
            
            for task in tasks:
                logger.info(f"Reminder triggered for task: {task['description']}")
                minutes_remaining = task['minutes_remaining']
                reminder_message = f"Reminder: {task['description']} is due in {minutes_remaining} minute{'s' if minutes_remaining != 1 else ''}!"
                
                # Write reminder to text file
                try:
                    with open(REMINDER_TEXT_FILE, 'w') as file:
                        file.write(f"{reminder_message}\n")
                    logger.info(f"Reminder written to {REMINDER_TEXT_FILE}: {reminder_message}")
                except Exception as e:
                    logger.error(f"Error writing to {REMINDER_TEXT_FILE}: {str(e)}")
                
            await asyncio.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        logger.info("Reminder loop interrupted by user")
    finally:
        logger.info("Program terminated")

if __name__ == "__main__":
    asyncio.run(reminder_loop())

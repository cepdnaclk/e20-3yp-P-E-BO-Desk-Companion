#!/usr/bin/env python3
"""
Interaction module to coordinate eye display and arm movements for robot emotions
Synchronizes expressions between eyes (display) and arms, then resets to default/neutral
"""

import time
import threading
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from display.eyes import RoboEyesDual, DEFAULT, TIRED, ANGRY, HAPPY
from arms.arms_pwm import (say_hi, search_movement, end_robot, express_angry,
                           express_sad, express_surprise, express_confused,
                           express_excited, express_tired, express_happy)

# Emotion configuration mapping
EMOTION_CONFIG = {
    'HI': {
        'display_mood': HAPPY,
        'display_func': lambda eyes, stop_event: eyes.Happy() if not stop_event.is_set() else None,
        'arm_func': say_hi
    },
    'SEARCH': {
        'display_mood': DEFAULT,
        'display_func': lambda eyes, stop_event: eyes.Default() if not stop_event.is_set() else None,
        'arm_func': search_movement
    },
    'END': {
        'display_mood': DEFAULT,
        'display_func': lambda eyes, stop_event: eyes.Default() if not stop_event.is_set() else None,
        'arm_func': end_robot
    },
    'ANGRY': {
        'display_mood': ANGRY,
        'display_func': lambda eyes, stop_event: eyes.Angry() if not stop_event.is_set() else None,
        'arm_func': express_angry
    },
    'SAD': {
        'display_mood': TIRED,
        'display_func': lambda eyes, stop_event: eyes.Tired() if not stop_event.is_set() else None,
        'arm_func': express_sad
    },
    'SURPRISE': {
        'display_mood': HAPPY,
        'display_func': lambda eyes, stop_event: eyes.Happy() if not stop_event.is_set() else None,
        'arm_func': express_surprise
    },
    'CONFUSED': {
        'display_mood': DEFAULT,
        'display_func': lambda eyes, stop_event: eyes.Default() if not stop_event.is_set() else None,
        'arm_func': express_confused
    },
    'EXCITED': {
        'display_mood': DEFAULT,
        'display_func': lambda eyes, stop_event: eyes.Default() if not stop_event.is_set() else None,
        'arm_func': express_excited
    },
    'TIRED': {
        'display_mood': TIRED,
        'display_func': lambda eyes, stop_event: eyes.Tired() if not stop_event.is_set() else None,
        'arm_func': express_tired
    },
    'HAPPY': {
        'display_mood': HAPPY,
        'display_func': lambda eyes, stop_event: eyes.Happy() if not stop_event.is_set() else None,
        'arm_func': express_happy
    }
}

class RobotInteraction:
    def __init__(self, left_eye_address=0x3C, right_eye_address=0x3D):
        """Initialize interaction with eye and arm controllers"""
        self.eyes = RoboEyesDual(left_address=left_eye_address, right_address=right_eye_address)
        self.eyes.begin(128, 64, 50)  # Initialize eyes with screen size and frame rate
        self.current_eye_thread = None
        self.stop_eye_event = threading.Event()

    def stop_current_eye_animation(self):
        """Stop the current eye animation if running"""
        if self.current_eye_thread and self.current_eye_thread.is_alive():
            self.stop_eye_event.set()  # Signal the eye thread to stop
            self.current_eye_thread.join()  # Wait for the thread to finish
            self.stop_eye_event.clear()  # Reset the event for the next use

    def express_emotion(self, emotion):
        """Express an emotion by coordinating eyes and arms, then reset to default/neutral"""
        emotion = emotion.upper()
        if emotion not in EMOTION_CONFIG:
            print(f"Unknown emotion: {emotion}. Available emotions: {list(EMOTION_CONFIG.keys())}")
            return

        config = EMOTION_CONFIG[emotion]
        display_func = config['display_func']
        arm_func = config['arm_func']

        # Stop any existing eye animation
        self.stop_current_eye_animation()

        # Function to handle eye updates in a separate thread
        def eye_thread_func():
            try:
                display_func(self.eyes, self.stop_eye_event)
            except Exception as e:
                print(f"Error in eye animation: {e}")

        # Create threads for eyes and arms
        self.current_eye_thread = threading.Thread(target=eye_thread_func)
        arm_thread = threading.Thread(target=arm_func)

        # Start both threads to run simultaneously
        self.current_eye_thread.start()
        arm_thread.start()

        # Wait for arm movement to complete
        arm_thread.join()

        # Stop eye animation and reset to default
        self.stop_current_eye_animation()
        
        # Run Default mood briefly to reset
        def default_eye_thread():
            try:
                self.eyes.Default()
            except Exception as e:
                print(f"Error in default eye animation: {e}")
        
        self.current_eye_thread = threading.Thread(target=default_eye_thread)
        self.current_eye_thread.start()
        
        # Reset arms to neutral
        reset_to_neutral()

        # Wait briefly to ensure smooth reset
        time.sleep(1.0)
        
        print(f"Completed emotion: {emotion}, reset to default/neutral")

def main():
    eyes = RoboEyesDual(left_address=0x3D, right_address=0x3C)
    
    # Initialize with screen size and frame rate
    eyes.begin(128, 64, 50)
    """Main function to test interaction module"""
    try:
        robot = RobotInteraction()
        emotions = list(EMOTION_CONFIG.keys())
        
        print("\n🤖 Robot Interaction System 🤖")
        print("=" * 35)
        print("Available emotions:", ", ".join(emotions))
        
        while True:
            emotion = input("\nEnter emotion (or 'q' to quit): ").upper()
            if emotion.lower() == 'q':
                print("Quitting interaction system...")
                break
            robot.express_emotion(emotion)
            
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    finally:
        # Stop any running eye animation
        robot.stop_current_eye_animation()
        # Clear displays and reset arms
        robot.eyes.display_left.fill(0)
        robot.eyes.display_left.show()
        robot.eyes.display_right.fill(0)
        robot.eyes.display_right.show()
        reset_to_neutral()
        print("System shutdown complete")

if __name__ == "__main__":
    main()

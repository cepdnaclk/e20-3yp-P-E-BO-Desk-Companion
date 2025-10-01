#!/usr/bin/env python3
"""
Hand detection using MediaPipe and OpenCV to detect waving hands (left, right, or multiple).
Detects palm skeleton without tracking finger points. When waving is detected, runs the hi function and speaks a random greeting in parallel.
Runs on Raspberry Pi with picamera2.
"""

import cv2
import mediapipe as mp
from picamera2 import Picamera2
import time
from collections import deque
import numpy as np
import threading
import busio
import board
import sys
import os
import random
import asyncio
import edge_tts
import pygame

# Adjust sys.path to import from sibling folders
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from arms.arms_pwm import say_hi
from display.eyes_qr import RoboEyesDual

# Constants for eye addresses
LEFT_EYE_ADDRESS = 0x3C
RIGHT_EYE_ADDRESS = 0x3D

# Greetings list
GREETINGS = [
    "Hello there!",
    "Hi, nice to see you!",
    "Hey, what's up?",
    "Yo, hi hi!",
    "Nice to meet you!",
    "Hey, hello!"
]

# Globals for eyes and threading
i2c = None
eyes = None
current_eye_thread = None
stop_event = None

def initialize_hardware():
    """Initialize I2C and eyes globally."""
    global i2c, eyes
    i2c = busio.I2C(board.SCL, board.SDA)
    eyes = RoboEyesDual(LEFT_EYE_ADDRESS, RIGHT_EYE_ADDRESS)
    eyes.begin(128, 64, 40)

def normal():
    """Set eyes to default mode."""
    global current_eye_thread, stop_event
    if stop_event:
        stop_event.set()
    if current_eye_thread:
        current_eye_thread.join(timeout=1.0)
    stop_event = threading.Event()
    current_eye_thread = threading.Thread(target=eyes.Default, args=(stop_event,))
    current_eye_thread.daemon = True
    current_eye_thread.start()

def run_emotion(arm_func, eye_func, duration=1):
    """Run arm movement and eye expression simultaneously, then return to normal mode."""
    global current_eye_thread, stop_event
    if stop_event:
        stop_event.set()
    if current_eye_thread:
        current_eye_thread.join(timeout=1.0)
    
    stop_event = threading.Event()
    current_eye_thread = threading.Thread(target=eye_func, args=(stop_event,))
    current_eye_thread.daemon = True
    current_eye_thread.start()
    
    if arm_func:
        arm_func()
    
    time.sleep(duration)
    
    stop_event.set()
    if current_eye_thread:
        current_eye_thread.join(timeout=1.0)
        current_eye_thread = None
    stop_event = None
    
    normal()

async def speak_greeting_async(text):
    """Asynchronous function to generate speech with edge_tts and play it."""
    communicate = edge_tts.Communicate(text, voice="en-US-AnaNeural")
    await communicate.save("greeting.mp3")
    
    # Play the generated MP3 using pygame
    pygame.mixer.init()
    pygame.mixer.music.load("greeting.mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
    pygame.mixer.quit()
    
    # Clean up the MP3 file
    os.remove("greeting.mp3")

def speak_greeting(text):
    """Synchronous wrapper for speaking greeting."""
    loop = asyncio.new_event_loop()
    loop.run_until_complete(speak_greeting_async(text))
    loop.close()

def hi():
    greeting = random.choice(GREETINGS)
    # Run speaking in parallel thread
    speech_thread = threading.Thread(target=speak_greeting, args=(greeting,))
    speech_thread.daemon = True
    speech_thread.start()
    
    run_emotion(say_hi, eyes.Happy)

# Initialize hardware at start
initialize_hardware()

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    model_complexity=1,  # Use full model for higher accuracy
    max_num_hands=2,  # Detect up to 2 hands
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# Initialize camera
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
picam2.start()

# Variables for waving detection
waving_cooldown = 5.0  # Seconds between waving detections
last_waving_time = 0
position_history_length = 10  # Number of frames to track for waving
direction_changes_threshold = 4  # Minimum direction changes to detect waving
amplitude_threshold = 20  # Minimum x-movement amplitude (pixels)

# Track wrist positions for each hand (left and right)
wrist_positions = {'Left': deque(maxlen=position_history_length), 'Right': deque(maxlen=position_history_length)}

try:
    print("\n🤖 Waving Hand Detection System 🤖")

    while True:
        # Capture frame
        frame = picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)  # Convert to 3-channel BGR
        frame = cv2.resize(frame, (640, 480))
        frame = cv2.rotate(frame, cv2.ROTATE_180)  # Rotate if needed
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process frame for hand detection
        results = hands.process(frame_rgb)

        # Check for detected hands
        hands_detected = []
        waving_detected = False
        if results.multi_hand_landmarks and results.multi_handedness:
            for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                # Get handedness (Left or Right)
                handedness = results.multi_handedness[idx].classification[0].label

                # Draw hand landmarks and connections (skeleton), focusing on palm
                mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=3, circle_radius=5),
                    mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=3)
                )

                # Get wrist position (landmark 0)
                wrist = hand_landmarks.landmark[0]
                wrist_x = int(wrist.x * frame.shape[1])
                wrist_y = int(wrist.y * frame.shape[0])

                # Update position history for this hand
                wrist_positions[handedness].append(wrist_x)

                # Detect waving: Check for oscillatory movement in x-direction
                positions = list(wrist_positions[handedness])
                if len(positions) == position_history_length:
                    # Compute direction changes
                    directions = np.diff(positions)  # Differences between consecutive positions
                    direction_changes = np.sum(np.diff(np.sign(directions)) != 0)
                    amplitude = max(positions) - min(positions)

                    if direction_changes >= direction_changes_threshold and amplitude >= amplitude_threshold:
                        waving_detected = True
                        print(f"Waving detected on {handedness} hand!")

                # Collect detected hands info
                hands_detected.append(handedness)

        # If waving detected on any hand, trigger hi() with cooldown
        if waving_detected:
            current_time = time.time()
            if current_time - last_waving_time >= waving_cooldown:
                hi()  # Run the hi function
                last_waving_time = current_time

        # Display detection status
        if hands_detected:
            status_text = f"Hands Detected: {', '.join(hands_detected)}"
            status_color = (0, 255, 0)
        else:
            status_text = "No Hands Detected"
            status_color = (0, 0, 255)
        cv2.putText(frame, status_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

        # Show frame
        cv2.imshow("Hand Detection", frame)

        # Handle keypress (keep waitKey for window refresh)
        cv2.waitKey(1)

except KeyboardInterrupt:
    print("\nProgram interrupted by user")
except Exception as e:
    print(f"\nError: {e}")
finally:
    # Cleanup
    hands.close()
    picam2.stop()
    cv2.destroyAllWindows()
    if eyes:
        eyes.display_left.fill(0)
        eyes.display_left.show()
        eyes.display_right.fill(0)
        eyes.display_right.show()
    if i2c:
        i2c.deinit()
    print("Program terminated")

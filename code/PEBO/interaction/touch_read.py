#!/usr/bin/env python3
"""
Simple script to count touches on a sensor connected to GPIO 17 (BCM).
Counts touches lasting at least 0.5 seconds, notes long touches (>= 2.5s).
Runs continuously, showing touch count and duration, until interrupted.
"""

import RPi.GPIO as GPIO
import time

# GPIO pin for touch sensor (BCM)
TOUCH_PIN = 17

# Minimum touch duration (seconds)
MIN_TOUCH_DURATION = 0.01

# Long touch threshold (seconds)
LONG_TOUCH_THRESHOLD = 2.5

def setup_gpio():
    """Configure GPIO pin for touch sensor."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TOUCH_PIN, GPIO.IN)

def count_touches():
    """Count valid touches and report duration."""
    touch_count = 0
    print("Monitoring touch sensor on GPIO 17. Press Ctrl+C to stop.")
    try:
        while True:
            # Detect touch (HIGH signal)
            if GPIO.input(TOUCH_PIN) == GPIO.HIGH:
                start_time = time.time()
                # Wait for touch to end
                while GPIO.input(TOUCH_PIN) == GPIO.HIGH:
                    time.sleep(0.01)
                duration = time.time() - start_time
                # Count touches >= 0.5s
                if duration >= MIN_TOUCH_DURATION:
                    touch_count += 1
                    if duration >= LONG_TOUCH_THRESHOLD:
                        print(f"Touch detected: {duration:.1f}s (Long touch)")
                    else:
                        print(f"Touch detected: {duration:.1f}s")
                    print(f"Total touches: {touch_count}")
                # Debounce
                time.sleep(0.1)
            time.sleep(0.01)

    except KeyboardInterrupt:
        print(f"\nStopped. Total touches: {touch_count}")
    finally:
        GPIO.cleanup()
        print("GPIO cleaned up.")

if __name__ == "__main__":
    setup_gpio()
    count_touches()

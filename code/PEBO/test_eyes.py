#!/usr/bin/env python3
"""
Test script for RoboEyesDual emotions
Cycles through different emotional states of the RoboEyes display
"""

import time
from display.eyes import RoboEyesDual

def main():
    # Initialize RoboEyesDual instance
    eyes = RoboEyesDual(left_address=0x3D, right_address=0x3C)
    eyes.begin(128, 64, 50)  # Initialize with screen size and frame rate

    # List of emotions to cycle through
    emotions = [
        (eyes.Default, "Default"),
        (eyes.Happy, "Happy"),
        (eyes.Tired, "Tired"),
        (eyes.Angry, "Angry")
    ]
    try:
        eyes.Happy()

    except KeyboardInterrupt:
        # Clean up on exit
        eyes.display_left.fill(0)
        eyes.display_left.show()
        eyes.display_right.fill(0)
        eyes.display_right.show()
        print("\nTest script stopped")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Integrated Robot Control System
Imports arms_pwm.py and robo_eyes.py to control arms and eyes with unified emotion functions
Runs eyes and arms simultaneously and returns to normal mode after 10 seconds
"""

import time
import board
import busio
import smbus
import threading
from arms.arms_pwm import (say_hi, express_tired, express_happy, express_sad, express_angry,
                           reset_to_neutral, scan_i2c_devices, angle_to_pulse_value, set_servos, smooth_move)
from display.eyes import RoboEyesDual

# Constants for I2C addresses
PCA9685_ADDR = 0x40
LEFT_EYE_ADDRESS = 0x3D
RIGHT_EYE_ADDRESS = 0x3C

class RobotController:
    def __init__(self):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.eyes = RoboEyesDual(LEFT_EYE_ADDRESS, RIGHT_EYE_ADDRESS)
        self.eyes.begin(128, 64, 40)
        self.current_eye_thread = None
        self.stop_event = None

    def run_emotion(self, arm_func, eye_func):
        """Run arm movement and eye expression simultaneously, then return to normal mode"""
        # Create a new stop event for this expression
        self.stop_event = threading.Event()
        
        # Start eye expression in a separate thread
        self.current_eye_thread = threading.Thread(target=eye_func, args=(self.stop_event,))
        self.current_eye_thread.daemon = True  # Ensure thread exits when main program does
        self.current_eye_thread.start()
        
        # Run arm movement in the main thread
        arm_func()
        
        # Wait for 10 seconds total (including arm movement time)
        time.sleep(1)
        
        # Stop the current eye expression
        self.stop_event.set()
        if self.current_eye_thread:
            self.current_eye_thread.join(timeout=1.0)  # Wait for thread to terminate
            self.current_eye_thread = None
        self.stop_event = None
        
        # Return to normal mode
        self.normal()

    def hi(self):
        print("Expressing Hi")
        self.run_emotion(say_hi, self.eyes.Happy)

    def normal(self):
        print("Expressing Normal")
        # Run both arms and eyes for normal mode
        self.stop_event = threading.Event()
        self.current_eye_thread = threading.Thread(target=self.eyes.Default, args=(self.stop_event,))
        self.current_eye_thread.daemon = True
        self.current_eye_thread.start()
        # Normal mode persists until next command, so don't stop the eye thread
        # Clear stop event but keep thread running
        self.stop_event = None

    def happy(self):
        print("Expressing Happy")
        self.run_emotion(express_happy, self.eyes.Happy)

    def sad(self):
        print("Expressing Sad")
        self.run_emotion(express_sad, self.eyes.Tired)

    def angry(self):
        print("Expressing Angry")
        self.run_emotion(express_angry, self.eyes.Angry)

    def love(self):
        print("Expressing Love")
        self.run_emotion(express_happy, self.eyes.Love)

    def cleanup(self):
        """Clean up resources, clear displays, and deinitialize I2C bus to clear SCL and SDA."""
        print("🖥️ Cleaning up RobotController resources...")
        # Stop any running eye thread
        if self.stop_event:
            self.stop_event.set()
        if self.current_eye_thread:
            self.current_eye_thread.join(timeout=1.0)
            self.current_eye_thread = None
        # Reset arms and clear displays
        try:
            reset_to_neutral()
            self.eyes.display_left.fill(0)
            self.eyes.display_left.show()
            self.eyes.display_right.fill(0)
            self.eyes.display_right.show()
            print("🖥️ Displays cleared")
        except Exception as e:
            print(f"🖥️ Error clearing displays: {e}")
        # Deinitialize I2C bus to clear SCL and SDA
        try:
            self.i2c.deinit()
            print("🖥️ I2C bus deinitialized, SCL and SDA cleared")
        except Exception as e:
            print(f"🖥️ Error deinitializing I2C bus: {e}")
        print("🖥️ RobotController cleanup complete")

def main():
    try:
        print("\n🤖 Integrated Robot Control System 🤖")
        print("=" * 45)
        print("I2C Configuration:")
        print(f"  PWM Controller: 0x{PCA9685_ADDR:02X}")
        print(f"  Left Eye OLED: 0x{LEFT_EYE_ADDRESS:02X}")
        print(f"  Right Eye OLED: 0x{RIGHT_EYE_ADDRESS:02X}")
        print("=" * 45)
        print("Scanning for I2C devices...")
        devices = scan_i2c_devices()
        print(f"Found I2C devices: {', '.join(devices)}")
        
        controller = RobotController()
        # Start in normal mode

        while True:
            print("\nAvailable Emotions:")
            print("  1: Hi (Happy eyes, Say Hi arms)")
            print("  2: Normal (Default eyes, Tired arms)")
            print("  3: Happy (Happy eyes, Happy arms)")
            print("  4: Sad (Tired eyes, Sad arms)")
            print("  5: Angry (Angry eyes, Angry arms)")
            print("  6: Love (Love eyes, Happy arms)")
            print("  q: Quit Program")

            input_val = input("\nEnter command: ").lower()

            if input_val == 'q':
                print("Quitting program...")
                break
            elif input_val == '1':
                controller.hi()
            elif input_val == '2':
                controller.normal()
            elif input_val == '3':
                controller.happy()
            elif input_val == '4':
                controller.sad()
            elif input_val == '5':
                controller.angry()
            elif input_val == '6':
                controller.love()
            else:
                print("Invalid command! Please use 1-6 or q.")

    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        controller.cleanup()
        print("Program terminated")

if __name__ == "__main__":
    main()

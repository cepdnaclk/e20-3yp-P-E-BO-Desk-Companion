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
from display.eyes_qr import RoboEyesDual

# Constants for I2C addresses
PCA9685_ADDR = 0x40
LEFT_EYE_ADDRESS = 0x3C
RIGHT_EYE_ADDRESS = 0x3D

class RobotController:
    def __init__(self):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.eyes = RoboEyesDual(LEFT_EYE_ADDRESS, RIGHT_EYE_ADDRESS)
        self.eyes.begin(128, 64, 40)
        self.current_eye_thread = None
        self.stop_event = None

    # Eye loop lifecycle
    current_eye_thread: threading.Thread | None = None
    stop_event: threading.Event | None = None

    def _start_eye_loop(loop_fn):
        global current_eye_thread, stop_event
        _stop_eye_loop()
        stop_event = threading.Event()
        current_eye_thread = threading.Thread(target=loop_fn, args=(stop_event,))
        current_eye_thread.daemon = True
        current_eye_thread.start()

    def _stop_eye_loop(timeout: float = 1.0):
        global current_eye_thread, stop_event
        if stop_event is not None:
            stop_event.set()
        if current_eye_thread is not None:
            current_eye_thread.join(timeout=timeout)
        current_eye_thread = None
        stop_event = None

    def run_emotion(arm_func=None, eye_func=None, duration: float = 1.0):
        if eye_func is not None:
            _start_eye_loop(eye_func)
        if arm_func is not None:
            try:
                arm_func()
            except Exception as e:
                print(f"[arms] arm_func error: {e}")
        time.sleep(duration)
        _stop_eye_loop()
        normal()

    def normal():
        _start_eye_loop(eyes.Default)

    def cleanup():
        global i2c, eyes
        print("Cleaning up resources...")
        _stop_eye_loop()
        try:
            resettoneutral()
        except Exception:
            pass
        try:
            eyes.displayleft.fill(0); eyes.displayleft.show()
            eyes.displayright.fill(0); eyes.displayright.show()
        except Exception as e:
            print(f"[cleanup] display clear error: {e}")
        try:
            i2c.deinit()
            print("I2C bus deinitialized, SCL and SDA cleared")
        except Exception as e:
            print(f"[cleanup] I2C deinit error: {e}")
        print("Cleanup complete")


    def hi(self):
        print("Expressing Hi")
        self.run_emotion(say_hi, self.eyes.Happy)



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
        
        
    def qr(self, device_id):
        """Express QR code with the specified device ID"""
        print(f"Expressing QR with device ID: {device_id}")
        self.run_emotion(None, self.eyes.QR(device_id))
        
    
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
            print("  7: QR (QR eyes, none)")
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
            elif input_val == '7':
                controller.qr(123456)
            else:
                print("Invalid command! Please use 1-7 or q.")

    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        controller.cleanup()
        print("Program terminated")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Integrated Robot Control System
Controls arms and eyes with unified emotion functions.
Runs eyes and arms simultaneously and returns to normal mode afterwards.
"""

import time
import board
import busio
import smbus
import threading
from arms.arms_pwm import (
    say_hi, express_tired, express_happy, express_sad, express_angry,
    reset_to_neutral, scan_i2c_devices, angle_to_pulse_value, set_servos, smooth_move
)
from display.eyes_qr import RoboEyesDual

# I2C addresses
PCA9685_ADDR = 0x40
LEFT_EYE_ADDRESS = 0x3C
RIGHT_EYE_ADDRESS = 0x3D


class RobotController:
    def __init__(self):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.eyes = RoboEyesDual(LEFT_EYE_ADDRESS, RIGHT_EYE_ADDRESS)
        self.eyes.begin(128, 64, 40)
        self.current_eye_thread: threading.Thread | None = None
        self.stop_event: threading.Event | None = None
        self.lock = threading.Lock()

    # Eye loop lifecycle (instance-safe)
    def _start_eye_loop(self, loop_fn):
        self._stop_eye_loop()
        self.stop_event = threading.Event()
        self.current_eye_thread = threading.Thread(target=loop_fn, args=(self.stop_event,))
        self.current_eye_thread.daemon = True
        self.current_eye_thread.start()

    def _stop_eye_loop(self, timeout: float = 1.0):
        if self.stop_event is not None:
            self.stop_event.set()
        if self.current_eye_thread is not None:
            self.current_eye_thread.join(timeout=timeout)
        self.current_eye_thread = None
        self.stop_event = None

    def run_emotion(self, arm_func=None, eye_func=None, duration: float = 1.0):
        # Start eyes (loop) then run arms
        if eye_func is not None:
            self._start_eye_loop(eye_func)
        if arm_func is not None:
            try:
                arm_func()
            except Exception as e:
                print(f"[arms] arm_func error: {e}")
        # Hold expression
        time.sleep(duration)
        # Stop and return to default eyes
        self._stop_eye_loop()
        self.normal()

    # Emotions
    def normal(self):
        # eyes.Default must be a callable(stop_event); this matches the assistant module usage
        self._start_eye_loop(self.eyes.Default)

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

    def qr(self, device_id, duration: float = 15.0):
        print(f"Expressing QR with device ID: {device_id}")
        # Pass a loop that accepts stop_event, consistent with assistant_combined1.py
        self.run_emotion(
            None,
            lambda stop_event: self.eyes.QR(device_id, stop_event=stop_event),
            duration=duration
        )

    def cleanup(self):
        print("Cleaning up resources...")
        # Stop eye loop
        self._stop_eye_loop()
        # Neutral arms and clear displays (attribute names follow RoboEyesDual used in assistant module)
        try:
            reset_to_neutral()
        except Exception:
            pass
        try:
            self.eyes.display_left.fill(0); self.eyes.display_left.show()
            self.eyes.display_right.fill(0); self.eyes.display_right.show()
            print("Displays cleared")
        except Exception as e:
            print(f"[cleanup] display clear error: {e}")
        # Deinit I2C
        try:
            self.i2c.deinit()
            print("I2C bus deinitialized, SCL and SDA cleared")
        except Exception as e:
            print(f"[cleanup] I2C deinit error: {e}")
        print("Cleanup complete")


def main():
    controller = None
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
        # Render addresses safely
        try:
            devs_str = ", ".join(f"0x{int(d):02X}" for d in devices)
        except Exception:
            devs_str = ", ".join(str(d) for d in devices)
        print(f"Found I2C devices: {devs_str}")

        controller = RobotController()
        # Start default eye loop at boot
        controller.normal()

        while True:
            print("\nAvailable Emotions:")
            print("  1: Hi (Happy eyes, Say Hi arms)")
            print("  2: Normal (Default eyes)")
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
        if controller is not None:
            controller.cleanup()
        print("Program terminated")


if __name__ == "__main__":
    main()

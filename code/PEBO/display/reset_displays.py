#!/usr/bin/env python3
import subprocess
import RPi.GPIO as GPIO
import time
import os

def reset_i2c_bus():
    print("🔄 Resetting I2C bus...")
    try:
        # Toggle SDA/SCL
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(2, GPIO.OUT)  # SDA
        GPIO.setup(3, GPIO.OUT)  # SCL
        for _ in range(10):
            GPIO.output(2, GPIO.HIGH)
            GPIO.output(3, GPIO.HIGH)
            time.sleep(0.001)
            GPIO.output(2, GPIO.LOW)
            GPIO.output(3, GPIO.LOW)
            time.sleep(0.001)
        GPIO.cleanup([2, 3])
        # Reload I2C module
        subprocess.run(["sudo", "rmmod", "i2c_bcm2835"], check=True)
        time.sleep(0.1)
        subprocess.run(["sudo", "modprobe", "i2c_bcm2835"], check=True)
        # Check I2C devices
        result = subprocess.run(["i2cdetect", "-y", "1"], capture_output=True, text=True)
        print(f"I2C bus state:\n{result.stdout}")
        if "3c" in result.stdout and "3d" in result.stdout:
            print("✅ Displays detected.")
        else:
            print("⚠️ Displays not detected.")
    except Exception as e:
        print(f"⚠️ Error resetting I2C: {e}")

if __name__ == "__main__":
    try:
        reset_i2c_bus()
    except KeyboardInterrupt:
        print("🛑 Interrupted.")
    finally:
        GPIO.cleanup()

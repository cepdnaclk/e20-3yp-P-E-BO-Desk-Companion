import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

def test_servo():
    # Setup I2C and PWM controller
    print("Initializing PCA9685 PWM controller...")
    i2c = busio.I2C(board.SCL, board.SDA)
    pwm = PCA9685(i2c)
    pwm.frequency = 50  # Standard servo frequency of 50Hz
    
    # Create servo objects
    servo_channel = 4 # Test with channel 0 - change as needed
    test_servo = servo.Servo(pwm.channels[servo_channel])
    
    try:
        print(f"Starting servo test on channel {servo_channel}")
        print("Moving servo to 0 degrees")
        test_servo.angle = 0
        time.sleep(1)
        
        print("Moving servo to 90 degrees")
        test_servo.angle = 90
        time.sleep(1)
        
        print("Moving servo to 180 degrees")
        test_servo.angle = 180
        time.sleep(1)
        
        print("Sweeping servo from 0 to 180 degrees")
        for angle in range(0, 181, 10):  # Step by 10 degrees
            test_servo.angle = angle
            print(f"Angle: {angle}°")
            time.sleep(0.5)
            
        print("Sweeping servo from 180 to 0 degrees")
        for angle in range(180, -1, -10):  # Step by 10 degrees
            test_servo.angle = angle
            print(f"Angle: {angle}°")
            time.sleep(0.5)
            
        print("Testing complete! Returning to center position (90°)")
        test_servo.angle = 90
        time.sleep(1)
    
    finally:
        # Release the servo
        print("Releasing servo (removing holding torque)")
        pwm.channels[servo_channel].duty_cycle = 0
        time.sleep(0.5)
        pwm.deinit()
        print("Test complete - PWM controller shut down")

def test_multiple_servos():
    # Setup I2C and PWM controller
    print("Initializing PCA9685 PWM controller...")
    i2c = busio.I2C(board.SCL, board.SDA)
    pwm = PCA9685(i2c)
    pwm.frequency = 50  # Standard servo frequency of 50Hz
    
    # Test parameters
    num_servos = 2  # Number of servos to test
    channels = [0, 1]  # Channels for each servo
    servo_objects = []
    
    # Create servo objects
    for channel in channels:
        servo_objects.append(servo.Servo(pwm.channels[channel]))
    
    try:
        print(f"Starting test of {num_servos} servos on channels {channels}")
        
        # Center all servos
        print("Centering all servos (90°)")
        for s in servo_objects:
            s.angle = 90
        time.sleep(2)
        
        # Move each servo individually
        for i, s in enumerate(servo_objects):
            print(f"Testing servo on channel {channels[i]}")
            print("  Moving to 0°")
            s.angle = 0
            time.sleep(1)
            
            print("  Moving to 180°")
            s.angle = 180
            time.sleep(1)
            
            print("  Moving back to 90°")
            s.angle = 90
            time.sleep(1)
        
        # Move all servos together
        print("Moving all servos together to 45°")
        for s in servo_objects:
            s.angle = 45
        time.sleep(2)
        
        print("Moving all servos together to 135°")
        for s in servo_objects:
            s.angle = 135
        time.sleep(2)
        
        print("Returning all servos to center (90°)")
        for s in servo_objects:
            s.angle = 90
        time.sleep(2)
    
    finally:
        # Release all servos
        print("Releasing all servos (removing holding torque)")
        for channel in channels:
            pwm.channels[channel].duty_cycle = 0
        time.sleep(0.5)
        pwm.deinit()
        print("Test complete - PWM controller shut down")

if __name__ == "__main__":
    print("Servo Test Program")
    print("------------------")
    print("1. Test single servo (channel 0)")
    print("2. Test multiple servos (channels 0 and 1)")
    
    choice = input("Enter your choice (1 or 2): ")
    
    if choice == "1":
        test_servo()
    elif choice == "2":
        test_multiple_servos()
    else:
        print("Invalid choice. Exiting.")

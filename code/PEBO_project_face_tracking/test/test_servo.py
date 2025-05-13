import RPi.GPIO as GPIO
import time

# Set GPIO mode
GPIO.setmode(GPIO.BCM)

# Define GPIO pin
SERVO_PIN = 24 # pin 18
GPIO.setup(SERVO_PIN, GPIO.OUT)

# Set PWM frequency (50Hz for standard servos)
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(10)  # Neutral position (7.5% duty cycle)

def set_angle_smooth(current_angle, target_angle, step=1):
    """Smoothly move the servo from current angle to target angle."""
    # Move from current angle to target angle in small steps
    for angle in range(current_angle, target_angle, step if target_angle > current_angle else -step):
        duty = (angle / 18.0) + 2.5  # Convert angle to duty cycle
        pwm.ChangeDutyCycle(duty)
        time.sleep(0.02)  # Small delay to allow the servo to move

# Move servo to different angles smoothly
set_angle_smooth(0, 40)    # Move from 0 to 90 degrees smoothly
# set_angle_smooth(90, 180)  # Move from 90 to 180 degrees smoothly
# set_angle_smooth(180, 90)  # Move from 180 to 90 degrees smoothly
# set_angle_smooth(90, 0)    # Move from 90 to 0 degrees smoothly

# Cleanup
pwm.stop()
GPIO.cleanup()

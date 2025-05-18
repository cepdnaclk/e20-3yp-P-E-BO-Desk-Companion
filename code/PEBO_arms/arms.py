import time
import RPi.GPIO as GPIO

# Define pin numbers (BCM pin numbering)
RIGHT_SERVO_PIN = 18  # GPIO18 (physical pin 12)
LEFT_SERVO_PIN = 17   # GPIO17 (physical pin 11)

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Setup servo pins
GPIO.setup(RIGHT_SERVO_PIN, GPIO.OUT)
GPIO.setup(LEFT_SERVO_PIN, GPIO.OUT)

# Create PWM objects for servo control
# Frequency is 50Hz (standard for servos)
right_servo = GPIO.PWM(RIGHT_SERVO_PIN, 50)
left_servo = GPIO.PWM(LEFT_SERVO_PIN, 50)

# Start PWM with neutral position (duty cycle 7.5 is usually ~90 degrees)
right_servo.start(7.5)
left_servo.start(7.5)
time.sleep(0.5)  # Give servos time to reach position

# Store current position
current_right_angle = 90
current_left_angle = 90

def angle_to_duty_cycle(angle):
    """Convert angle (0-180) to duty cycle (2-12)"""
    return (angle / 18) + 2

def set_servos(right_angle, left_angle):
    """Set both servos at once to avoid timing issues"""
    global current_right_angle, current_left_angle
    
    # Update stored angles
    current_right_angle = right_angle
    current_left_angle = left_angle
    
    # Convert angles to duty cycles
    right_duty = angle_to_duty_cycle(right_angle)
    left_duty = angle_to_duty_cycle(left_angle)
    
    # Set servo positions
    right_servo.ChangeDutyCycle(right_duty)
    left_servo.ChangeDutyCycle(left_duty)
    time.sleep(0.05)  # Small delay for servo response

def smooth_move(start_right, start_left, end_right, end_left, steps=15, step_delay=0.03):
    """Move servos smoothly from start position to end position"""
    for i in range(steps + 1):
        ratio = i / steps
        right_angle = start_right + (end_right - start_right) * ratio
        left_angle = start_left + (end_left - start_left) * ratio
        set_servos(right_angle, left_angle)
        time.sleep(step_delay)

def reset_to_neutral():
    """Return to neutral position with smooth motion"""
    global current_right_angle, current_left_angle
    smooth_move(current_right_angle, current_left_angle, 90, 90)
    time.sleep(0.2)  # Short stabilization delay

def express_angry():
    print("ANGRY")
    # Quick aggressive jerky movements
    
    # Starting position
    smooth_move(90, 90, 150, 30, steps=5, step_delay=0.02)
    
    # Rapid oscillation
    for _ in range(3):
        # Sharp movement to one extreme
        smooth_move(150, 30, 170, 10, steps=3, step_delay=0.02)
        time.sleep(0.05)
        
        # Sharp movement to other position
        smooth_move(170, 10, 130, 50, steps=3, step_delay=0.02)
        time.sleep(0.05)
    
    # One final dramatic movement
    smooth_move(130, 50, 180, 0, steps=4, step_delay=0.03)
    time.sleep(0.1)
    
    # Return to neutral
    reset_to_neutral()

def express_happy():
    print("HAPPY")
    # Bouncy, rhythmic movements
    
    # Initial excited movement
    smooth_move(90, 90, 140, 40, steps=8, step_delay=0.02)
    
    # Happy bouncing pattern
    for _ in range(2):
        # Outward movement (wide open)
        smooth_move(140, 40, 180, 0, steps=10, step_delay=0.03)
        time.sleep(0.1)
        
        # Return partially inward (like a bounce)
        smooth_move(180, 0, 150, 30, steps=6, step_delay=0.02)
        time.sleep(0.05)
        
        # Out again but less extreme
        smooth_move(150, 30, 170, 10, steps=6, step_delay=0.02)
        time.sleep(0.1)
    
    # Final happy flourish
    smooth_move(170, 10, 130, 50, steps=8, step_delay=0.03)
    time.sleep(0.1)
    
    # Return to neutral
    reset_to_neutral()

def express_sad():
    print("SAD")
    # Slow, drooping movements
    
    # Initial slow droop
    smooth_move(90, 90, 70, 70, steps=15, step_delay=0.05)
    time.sleep(0.3)
    
    # Continue drooping down
    smooth_move(70, 70, 50, 50, steps=15, step_delay=0.06)
    time.sleep(0.4)
    
    # Small "sigh" movement
    smooth_move(50, 50, 45, 45, steps=8, step_delay=0.07)
    time.sleep(0.5)
    
    # Very slow recovery
    smooth_move(45, 45, 60, 60, steps=12, step_delay=0.08)
    time.sleep(0.3)
    
    # Final return to neutral (slower than normal reset)
    smooth_move(60, 60, 90, 90, steps=20, step_delay=0.05)

def handle_emotion(emotion):
    if emotion == -1:
        express_sad()
    elif emotion == 0:
        express_happy()
    elif emotion == 1:
        express_angry()
    else:
        print("Unknown emotion code:", emotion)

def cleanup():
    """Clean up GPIO resources"""
    right_servo.stop()
    left_servo.stop()
    GPIO.cleanup()
    print("GPIO cleaned up")

def main():
    try:
        print("Raspberry Pi Robot Emotion Simulator")
        print("------------------------------------")
        while True:
            input_val = input("Enter emotion (-1 for SAD, 0 for HAPPY, 1 for ANGRY, q to quit): ")
            if input_val.lower() == 'q':
                break
            try:
                emotion_code = int(input_val)
                handle_emotion(emotion_code)
            except ValueError:
                print("Please enter a valid integer (-1, 0, or 1)")
    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        # Ensure servos are in neutral position before exit
        try:
            reset_to_neutral()
            time.sleep(0.5)
        except:
            pass
        cleanup()
        print("Program terminated")

if __name__ == "__main__":
    main()
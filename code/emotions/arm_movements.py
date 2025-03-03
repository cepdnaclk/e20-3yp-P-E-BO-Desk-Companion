import time
import RPi.GPIO as GPIO

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Pin definitions
RIGHT_SERVO_PIN = 18  # GPIO pin for right hand servo
LEFT_SERVO_PIN = 19   # GPIO pin for left hand servo

# Servo setup
GPIO.setup(RIGHT_SERVO_PIN, GPIO.OUT)
GPIO.setup(LEFT_SERVO_PIN, GPIO.OUT)

# Create PWM instances
# Frequency = 50Hz for standard servos
right_servo = GPIO.PWM(RIGHT_SERVO_PIN, 50)
left_servo = GPIO.PWM(LEFT_SERVO_PIN, 50)

# Start PWM with neutral position
right_servo.start(0)
left_servo.start(0)

def set_servo_angle(servo, angle):
    """
    Convert angle to duty cycle and set the servo position
    For standard servos: 2.5% duty cycle = 0°, 12.5% duty cycle = 180°
    """
    duty_cycle = 2.5 + (angle / 18.0)
    servo.ChangeDutyCycle(duty_cycle)
    time.sleep(0.1)  # Allow servo time to move

def reset_to_neutral():
    """Reset both servos to neutral position"""
    set_servo_angle(right_servo, 90)
    set_servo_angle(left_servo, 90)
    time.sleep(0.5)

def express_angry():
    """
    Angry motion: Rapid up and down movements with both arms
    """
    print("Expressing: ANGRY")
    for _ in range(3):  # Repeat motion 3 times
        # Both arms up
        set_servo_angle(right_servo, 180)
        set_servo_angle(left_servo, 0)
        time.sleep(0.2)
        
        # Both arms middle
        set_servo_angle(right_servo, 120)
        set_servo_angle(left_servo, 60)
        time.sleep(0.2)
    
    reset_to_neutral()

def express_surprised():
    """
    Surprised motion: Quick raise of both arms and hold
    """
    print("Expressing: SURPRISED")
    # Quick raise
    set_servo_angle(right_servo, 180)
    set_servo_angle(left_servo, 0)
    time.sleep(1)
    
    # Slight lower and hold
    set_servo_angle(right_servo, 150)
    set_servo_angle(left_servo, 30)
    time.sleep(0.5)
    
    reset_to_neutral()

def express_happy():
    """
    Happy motion: Waving both arms up and down in a celebratory motion
    """
    print("Expressing: HAPPY")
    for _ in range(2):
        # Arms up
        set_servo_angle(right_servo, 180)
        set_servo_angle(left_servo, 0)
        time.sleep(0.3)
        
        # Arms middle
        set_servo_angle(right_servo, 90)
        set_servo_angle(left_servo, 90)
        time.sleep(0.3)
        
        # Arms up again
        set_servo_angle(right_servo, 180)
        set_servo_angle(left_servo, 0)
        time.sleep(0.3)
    
    reset_to_neutral()

def express_calm():
    """
    Calm motion: Slow, gentle movements from middle to slightly down
    """
    print("Expressing: CALM")
    # Slow movement to down position
    for angle in range(90, 45, -5):
        set_servo_angle(right_servo, angle)
        set_servo_angle(left_servo, 180 - angle)
        time.sleep(0.2)
    
    # Hold calm position
    time.sleep(1)
    
    # Slow return
    for angle in range(45, 91, 5):
        set_servo_angle(right_servo, angle)
        set_servo_angle(left_servo, 180 - angle)
        time.sleep(0.2)
    
    reset_to_neutral()

def express_fear():
    """
    Fear motion: Defensive, trembling movement with arms down
    """
    print("Expressing: FEAR")
    # Arms down
    set_servo_angle(right_servo, 0)
    set_servo_angle(left_servo, 180)
    time.sleep(0.5)
    
    # Trembling effect
    for _ in range(4):
        set_servo_angle(right_servo, 10)
        set_servo_angle(left_servo, 170)
        time.sleep(0.1)
        set_servo_angle(right_servo, 0)
        set_servo_angle(left_servo, 180)
        time.sleep(0.1)
    
    reset_to_neutral()

def express_disgusted():
    """
    Disgust motion: One arm up, one down, then pushing away motion
    """
    print("Expressing: DISGUSTED")
    # Initial position
    set_servo_angle(right_servo, 180)  # Right arm up
    set_servo_angle(left_servo, 180)   # Left arm down
    time.sleep(0.5)
    
    # Pushing away motion
    for _ in range(2):
        set_servo_angle(right_servo, 120)
        time.sleep(0.2)
        set_servo_angle(right_servo, 180)
        time.sleep(0.2)
    
    reset_to_neutral()

def express_confused():
    """
    Confused motion: Alternating arm movements to simulate uncertainty
    """
    print("Expressing: CONFUSED")
    # Alternating arms
    for _ in range(2):
        # Right up, left down
        set_servo_angle(right_servo, 180)
        set_servo_angle(left_servo, 180)
        time.sleep(0.4)
        
        # Right down, left up
        set_servo_angle(right_servo, 0)
        set_servo_angle(left_servo, 0)
        time.sleep(0.4)
    
    reset_to_neutral()

def express_sad():
    """
    Sad motion: Slow drooping of both arms
    """
    print("Expressing: SAD")
    # Start at middle
    set_servo_angle(right_servo, 90)
    set_servo_angle(left_servo, 90)
    time.sleep(0.5)
    
    # Slowly droop down
    for angle in range(90, 30, -10):
        set_servo_angle(right_servo, angle)
        set_servo_angle(left_servo, angle)
        time.sleep(0.3)
    
    # Hold sad position
    time.sleep(1)
    
    reset_to_neutral()

def express_emotion(emotion):
    """
    Express the given emotion through servo movements
    """
    emotion_functions = {
        "ANGRY": express_angry,
        "SURPRISED": express_surprised,
        "HAPPY": express_happy,
        "CALM": express_calm,
        "FEAR": express_fear,
        "DISGUSTED": express_disgusted,
        "CONFUSED": express_confused,
        "SAD": express_sad
    }
    
    # Call the appropriate function for the emotion
    emotion_function = emotion_functions.get(emotion.upper())
    if emotion_function:
        emotion_function()
    else:
        print(f"Unknown emotion: {emotion}")
        reset_to_neutral()

def main():
    try:
        # Example usage
        emotions = ["ANGRY", "SURPRISED", "HAPPY", "CALM", "FEAR", "DISGUSTED", "CONFUSED", "SAD"]
        
        print("Starting emotion expression sequence...")
        for emotion in emotions:
            express_emotion(emotion)
            time.sleep(1)  # Pause between emotions
            
        print("Emotion sequence completed")
            
    except KeyboardInterrupt:
        print("Program stopped by user")
    finally:
        # Clean up
        right_servo.stop()
        left_servo.stop()
        GPIO.cleanup()
        print("GPIO cleanup completed")

if __name__ == "__main__":
    main()
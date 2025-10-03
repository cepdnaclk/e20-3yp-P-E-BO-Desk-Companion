import RPi.GPIO as GPIO
import time

# Pin configuration
TOUCH_PIN = 17  # GPIO pin number (Pin 11)

# Setup GPIO
GPIO.setmode(GPIO.BCM)  # Use BCM numbering
GPIO.setup(TOUCH_PIN, GPIO.IN)  # Set pin as input

def detect_continuous_touch(duration=3):
    """
    Detects if the touch sensor is continuously activated for the given duration (in seconds).
    Returns True if touch is detected continuously for the specified time.
    """
    start_time = None  # To record the start time of the touch

    while True:
        if GPIO.input(TOUCH_PIN) == GPIO.HIGH:  # Touch detected
            if start_time is None:
                start_time = time.time()  # Start timing
                print("Touch started")
            
            # Check the duration
            if time.time() - start_time >= duration:
                print(f"Touch detected continuously for {duration} seconds!")
                return True
        else:
            # Reset start time if touch is not continuous
            if start_time is not None:
                print("Touch interrupted")
            start_time = None
        
        time.sleep(0.1)  # Debounce delay

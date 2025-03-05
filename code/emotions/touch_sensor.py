import RPi.GPIO as GPIO
import time

# Set up GPIO mode
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Define pin numbers for the two TTP222 capacitive touch sensors
TOUCH_SENSOR_1 = 17  # GPIO17 - Left sensor
TOUCH_SENSOR_2 = 27  # GPIO27 - Right sensor

# Define the servo pin
SERVO_PIN = 18  # GPIO18 (PWM pin)

# Set up the pins
GPIO.setup(TOUCH_SENSOR_1, GPIO.IN)  # Left sensor as input
GPIO.setup(TOUCH_SENSOR_2, GPIO.IN)  # Right sensor as input
GPIO.setup(SERVO_PIN, GPIO.OUT)      # Servo pin as output

# Initialize PWM for servo control
servo_pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz frequency (standard for servos)
servo_pwm.start(7.5)  # Start with center position (90 degrees)

# Current servo position (in degrees, 0-180)
current_position = 90
target_position = 90
MIN_POSITION = 0
MAX_POSITION = 180
STEP_SIZE = 5       # Normal step size
QUICK_STEP_SIZE = 15  # Faster step size for double taps

# Variables for tracking touch states and timing
sensor1_state = False
sensor2_state = False
last_sensor1_state = False
last_sensor2_state = False

# Variables for gesture detection
touch_start_time1 = 0
touch_start_time2 = 0
last_touch_time1 = 0
last_touch_time2 = 0
tap_count1 = 0
tap_count2 = 0

# Timing constants (in seconds)
DOUBLE_TAP_TIMEOUT = 0.5  # Max time between taps to count as double tap
LONG_TOUCH_THRESHOLD = 1.0  # Min time for a touch to be considered "long"
TAP_RESET_TIMEOUT = 0.7  # Time to reset tap counter

# Convert angle to servo duty cycle
def angle_to_duty_cycle(angle):
    # Map angle 0-180 to duty cycle 2-12
    return ((angle / 180) * 10) + 2

# Set servo to a specific angle
def set_servo_angle(angle):
    global current_position
    # Constrain the angle to be between MIN_POSITION and MAX_POSITION
    if angle < MIN_POSITION:
        angle = MIN_POSITION
    elif angle > MAX_POSITION:
        angle = MAX_POSITION
    
    duty_cycle = angle_to_duty_cycle(angle)
    servo_pwm.ChangeDutyCycle(duty_cycle)
    current_position = angle
    print(f"Head position: {angle} degrees")
    
    # Small delay to allow servo to reach position
    time.sleep(0.1)
    # Disable PWM to prevent jitter
    servo_pwm.ChangeDutyCycle(0)

# Functions to handle different touch gestures
def handle_single_tap1():
    global current_position, target_position
    # Left sensor tapped - move head right
    target_position = current_position + STEP_SIZE
    print(f"ACTION: Moving head right to {target_position} degrees")
    set_servo_angle(target_position)

def handle_double_tap1():
    global current_position, target_position
    # Left sensor double tapped - move head right quicker
    target_position = current_position + QUICK_STEP_SIZE
    print(f"ACTION: Quick head right movement to {target_position} degrees")
    set_servo_angle(target_position)

def handle_multiple_taps1(count):
    global current_position, target_position
    # Multiple taps on left sensor - move right proportionally
    target_position = current_position + (count * STEP_SIZE)
    print(f"ACTION: Multiple right movements: {count} taps, moving to {target_position} degrees")
    set_servo_angle(target_position)

def handle_long_touch1():
    global current_position, target_position
    # Long touch on left sensor - move all the way right
    target_position = MAX_POSITION
    print(f"ACTION: Moving all the way right to {target_position} degrees")
    set_servo_angle(target_position)

def handle_single_tap2():
    global current_position, target_position
    # Right sensor tapped - move head left
    target_position = current_position - STEP_SIZE
    print(f"ACTION: Moving head left to {target_position} degrees")
    set_servo_angle(target_position)

def handle_double_tap2():
    global current_position, target_position
    # Right sensor double tapped - move head left quicker
    target_position = current_position - QUICK_STEP_SIZE
    print(f"ACTION: Quick head left movement to {target_position} degrees")
    set_servo_angle(target_position)

def handle_multiple_taps2(count):
    global current_position, target_position
    # Multiple taps on right sensor - move left proportionally
    target_position = current_position - (count * STEP_SIZE)
    print(f"ACTION: Multiple left movements: {count} taps, moving to {target_position} degrees")
    set_servo_angle(target_position)

def handle_long_touch2():
    global current_position, target_position
    # Long touch on right sensor - move all the way left
    target_position = MIN_POSITION
    print(f"ACTION: Moving all the way left to {target_position} degrees")
    set_servo_angle(target_position)

def handle_both_touched():
    global current_position, target_position
    # Both sensors touched - center head position
    target_position = 90  # Center position
    print(f"ACTION: Centering head position to {target_position} degrees")
    set_servo_angle(target_position)

try:
    print("Touch Gesture Robot Head Control System Ready")
    print("Left sensor = move right, Right sensor = move left")
    
    # Set initial center position
    set_servo_angle(90)
    
    both_touched_reported = False
    
    while True:
        # Read the current state of both sensors
        sensor1_state = GPIO.input(TOUCH_SENSOR_1)
        sensor2_state = GPIO.input(TOUCH_SENSOR_2)
        
        # Current time for timing calculations
        current_time = time.time()
        
        # ===== SENSOR 1 PROCESSING (LEFT SENSOR) =====
        # Detect rising edge (touch began)
        if sensor1_state and not last_sensor1_state:
            touch_start_time1 = current_time
            tap_count1 += 1
            print(f"Left sensor touched. Tap count: {tap_count1}")
            last_touch_time1 = current_time
        
        # Detect falling edge (touch ended)
        if not sensor1_state and last_sensor1_state:
            touch_duration = current_time - touch_start_time1
            
            if touch_duration < LONG_TOUCH_THRESHOLD:
                print("Left sensor: Short touch detected")
            else:
                print("Left sensor: Long touch detected")
                # Handle long touch on sensor 1
                handle_long_touch1()
        
        # Check for multi-tap gestures on sensor 1
        if tap_count1 > 0 and (current_time - last_touch_time1 > TAP_RESET_TIMEOUT):
            if tap_count1 == 1:
                print("Left sensor: Single tap confirmed")
                handle_single_tap1()
            elif tap_count1 == 2:
                print("Left sensor: Double tap confirmed")
                handle_double_tap1()
            elif tap_count1 >= 3:
                print("Left sensor: Multiple taps confirmed")
                handle_multiple_taps1(tap_count1)
            
            # Reset tap counter
            tap_count1 = 0
        
        # ===== SENSOR 2 PROCESSING (RIGHT SENSOR) =====
        # Detect rising edge (touch began)
        if sensor2_state and not last_sensor2_state:
            touch_start_time2 = current_time
            tap_count2 += 1
            print(f"Right sensor touched. Tap count: {tap_count2}")
            last_touch_time2 = current_time
        
        # Detect falling edge (touch ended)
        if not sensor2_state and last_sensor2_state:
            touch_duration = current_time - touch_start_time2
            
            if touch_duration < LONG_TOUCH_THRESHOLD:
                print("Right sensor: Short touch detected")
            else:
                print("Right sensor: Long touch detected")
                handle_long_touch2()
        
        # Check for multi-tap gestures on sensor 2
        if tap_count2 > 0 and (current_time - last_touch_time2 > TAP_RESET_TIMEOUT):
            if tap_count2 == 1:
                print("Right sensor: Single tap confirmed")
                handle_single_tap2()
            elif tap_count2 == 2:
                print("Right sensor: Double tap confirmed")
                handle_double_tap2()
            elif tap_count2 >= 3:
                print("Right sensor: Multiple taps confirmed")
                handle_multiple_taps2(tap_count2)
            
            # Reset tap counter
            tap_count2 = 0
        
        # ===== BOTH SENSORS TOGETHER =====
        # Check if both sensors are touched simultaneously
        if sensor1_state and sensor2_state:
            if not both_touched_reported:
                print("Both sensors touched simultaneously")
                handle_both_touched()
                both_touched_reported = True
        else:
            both_touched_reported = False
        
        # Update the last known states
        last_sensor1_state = sensor1_state
        last_sensor2_state = sensor2_state
        
        # Small delay to avoid bouncing
        time.sleep(0.02)

except KeyboardInterrupt:
    print("Program stopped by user")
finally:
    # Clean up - center the servo before exiting
    set_servo_angle(90)
    time.sleep(0.5)
    servo_pwm.stop()
    GPIO.cleanup()  # Clean up GPIO on exit
    print("GPIO cleaned up")
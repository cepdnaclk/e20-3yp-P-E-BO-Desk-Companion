import time
from pyfirmata import Arduino, util

# Set your Arduino port
board = Arduino('COM7')  # Replace with your port
time.sleep(2)

# Define pin numbers
RIGHT_SERVO_PIN = 9
LEFT_SERVO_PIN = 11

# Enable servo mode
board.digital[RIGHT_SERVO_PIN].mode = 4  # SERVO
board.digital[LEFT_SERVO_PIN].mode = 4

def set_servos(right_angle, left_angle):
    """Set both servos at once to avoid timing issues"""
    board.digital[RIGHT_SERVO_PIN].write(right_angle)
    board.digital[LEFT_SERVO_PIN].write(left_angle)
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
    current_right = board.digital[RIGHT_SERVO_PIN].read() or 90
    current_left = board.digital[LEFT_SERVO_PIN].read() or 90
    smooth_move(current_right, current_left, 90, 90)
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

def main():
    try:
        print("Robot Emotion Simulator")
        print("------------------------")
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
        board.exit()
        print("Connection closed")

if __name__ == "__main__":
    main()
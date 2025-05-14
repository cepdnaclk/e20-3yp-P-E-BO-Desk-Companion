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

def set_servo(pin, angle):
    board.digital[pin].write(angle)
    time.sleep(0.1)

def reset_to_neutral():
    set_servo(RIGHT_SERVO_PIN, 90)
    set_servo(LEFT_SERVO_PIN, 90)
    time.sleep(0.5)

def express_angry():
    print("ANGRY")
    for _ in range(3):
        set_servo(RIGHT_SERVO_PIN, 180)
        set_servo(LEFT_SERVO_PIN, 0)
        time.sleep(0.2)
        set_servo(RIGHT_SERVO_PIN, 120)
        set_servo(LEFT_SERVO_PIN, 60)
        time.sleep(0.2)
    reset_to_neutral()

def express_happy():
    print("HAPPY")
    for _ in range(2):
        set_servo(RIGHT_SERVO_PIN, 180)
        set_servo(LEFT_SERVO_PIN, 0)
        time.sleep(0.3)
        set_servo(RIGHT_SERVO_PIN, 90)
        set_servo(LEFT_SERVO_PIN, 90)
        time.sleep(0.3)
    reset_to_neutral()

def express_sad():
    print("SAD")
    set_servo(RIGHT_SERVO_PIN, 90)
    set_servo(LEFT_SERVO_PIN, 90)
    time.sleep(0.5)
    for angle in range(90, 30, -10):
        set_servo(RIGHT_SERVO_PIN, angle)
        set_servo(LEFT_SERVO_PIN, angle)
        time.sleep(0.3)
    time.sleep(1)
    reset_to_neutral()

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
        print("Stopped by user")
    finally:
        board.exit()

if __name__ == "__main__":
    main()

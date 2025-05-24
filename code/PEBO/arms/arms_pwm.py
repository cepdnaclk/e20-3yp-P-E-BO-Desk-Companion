import time
import random
import smbus
from adafruit_pca9685 import PCA9685
import board
import busio

# Define constants
# I2C address
PCA9685_ADDR = 0x40    # Default address for PCA9685 PWM controller

# Servo channels on PCA9685
RIGHT_SERVO_CHANNEL = 0  # Channel 0 on PCA9685
LEFT_SERVO_CHANNEL = 1   # Channel 1 on PCA9685

# Initialize I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize PCA9685 PWM controller
pwm = PCA9685(i2c, address=PCA9685_ADDR)
pwm.frequency = 50  # Set frequency to 50Hz (standard for servos)

# Store current position
current_right_angle = 90
current_left_angle = 90

def angle_to_pulse_value(angle):
    """
    Convert angle (0-180) to pulse value for PCA9685
    For most servos, pulse width between 1ms (0°) and 2ms (180°) 
    maps to approximately 100-500 in PCA9685 values (12-bit, 4096 steps)
    """
    pulse_min = 150  # Minimum pulse length (adjust for your servos)
    pulse_max = 600  # Maximum pulse length (adjust for your servos)
    return int(pulse_min + (pulse_max - pulse_min) * angle / 180)

def set_servos(right_angle, left_angle):
    """Set both servos at once to avoid timing issues"""
    global current_right_angle, current_left_angle
    
    # Ensure angles are within valid range
    right_angle = max(0, min(180, right_angle))
    left_angle = max(0, min(180, left_angle))
    
    # Update stored angles
    current_right_angle = right_angle
    current_left_angle = left_angle
    
    # Convert angles to pulse values
    right_pulse = angle_to_pulse_value(right_angle)
    left_pulse = angle_to_pulse_value(left_angle)
    
    # Set servo positions
    pwm.channels[RIGHT_SERVO_CHANNEL].duty_cycle = right_pulse << 4  # Scale 12-bit to 16-bit
    pwm.channels[LEFT_SERVO_CHANNEL].duty_cycle = left_pulse << 4    # Scale 12-bit to 16-bit
    time.sleep(0.05)  # Small delay for servo response

def smooth_move(start_right, start_left, end_right, end_left, steps=1, step_delay=0.03):
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
    smooth_move(current_right_angle, current_left_angle, 90, 90, steps=18, step_delay=0.04)
    time.sleep(0.2)  # Short stabilization delay

# New Start Function - Say Hi with right hand
def say_hi():
    """Robot says hi by waving right hand"""
    print("👋 Saying Hello!")
    
    # Initial position - raise right arm
    smooth_move(90, 90, 150, 90, steps=12, step_delay=0.04)
    time.sleep(0.2)
    
    # Wave movement
    for _ in range(3):
        smooth_move(150, 90, 130, 90, steps=8, step_delay=0.03)
        time.sleep(0.1)
        smooth_move(130, 90, 150, 90, steps=8, step_delay=0.03)
        time.sleep(0.1)
    
    # Special flourish at the end - excited hello
    smooth_move(150, 90, 170, 70, steps=10, step_delay=0.03)
    time.sleep(0.2)
    
    # Return to neutral
    reset_to_neutral()

# New Search Function - Looking around movement
def search_movement():
    """Robot performs a searching or looking around movement"""
    print("🔍 Searching...")
    
    # Start with both arms slightly up
    smooth_move(90, 90, 110, 70, steps=10, step_delay=0.04)
    time.sleep(0.2)
    
    # Look left (left arm up higher, right arm down)
    smooth_move(110, 70, 60, 130, steps=15, step_delay=0.03)
    time.sleep(0.3)
    
    # Look right (right arm up higher, left arm down)
    smooth_move(60, 130, 130, 60, steps=20, step_delay=0.04)
    time.sleep(0.3)
    
    # Look around more frantically
    for _ in range(2):
        # Quick look left
        smooth_move(130, 60, 50, 120, steps=12, step_delay=0.02)
        time.sleep(0.1)
        
        # Quick look right
        smooth_move(50, 120, 140, 50, steps=12, step_delay=0.02)
        time.sleep(0.1)
    
    # Final search motion - look up
    smooth_move(140, 50, 120, 120, steps=10, step_delay=0.03)
    time.sleep(0.2)
    
    # Return to neutral
    reset_to_neutral()

# New End Function - Shutdown sequence
def end_robot():
    """Robot performs a shutdown/goodbye sequence"""
    print("💤 Shutting down...")
    
    # Start with hands up like "wait"
    smooth_move(90, 90, 140, 40, steps=15, step_delay=0.04)
    time.sleep(0.3)
    
    # Hands come together in front (like praying or sleeping)
    smooth_move(140, 40, 90, 90, steps=20, step_delay=0.05)
    time.sleep(0.2)
    
    # Slowly droop down (powering down)
    smooth_move(90, 90, 60, 60, steps=18, step_delay=0.06)
    time.sleep(0.3)
    
    # Final slight droop
    smooth_move(60, 60, 45, 45, steps=12, step_delay=0.07)
    time.sleep(0.5)
    
    # Return to neutral very slowly
    smooth_move(45, 45, 90, 90, steps=25, step_delay=0.08)

# Enhanced Emotion Functions with more expressive movements
def express_angry():
    print("😡 ANGRY")
    
    # Quick tense up movement
    smooth_move(90, 90, 120, 60, steps=7, step_delay=0.02)
    
    # Pounding fists - more aggressive movement
    for _ in range(3):
        # Arms up position
        smooth_move(120, 60, 160, 20, steps=5, step_delay=0.02)
        time.sleep(0.1)
        
        # Pounding down
        smooth_move(160, 20, 120, 60, steps=3, step_delay=0.01)
        time.sleep(0.05)
    
    # Shaking with rage - rapid small oscillations
    for _ in range(5):
        # Small shake left
        smooth_move(120, 60, 115, 65, steps=3, step_delay=0.01)
        
        # Small shake right
        smooth_move(115, 65, 125, 55, steps=3, step_delay=0.01)
    
    # Final outburst
    smooth_move(125, 55, 180, 0, steps=6, step_delay=0.02)
    time.sleep(0.2)
    
    # Tense hold
    set_servos(180, 0)
    time.sleep(0.5)
    
    # Sudden drop (like giving up)
    smooth_move(180, 0, 60, 60, steps=10, step_delay=0.05)
    time.sleep(0.3)
    
    # Return to neutral slowly (cooling down)
    smooth_move(60, 60, 90, 90, steps=15, step_delay=0.04)

def express_happy():
    print("😄 HAPPY")
    
    # Initial excited jump
    smooth_move(90, 90, 150, 30, steps=7, step_delay=0.02)
    time.sleep(0.1)
    
    # Happy dance movements
    for _ in range(2):
        # Arms wide open (joy)
        smooth_move(150, 30, 180, 0, steps=8, step_delay=0.03)
        time.sleep(0.15)
        
        # Arms in celebratory position
        smooth_move(180, 0, 130, 130, steps=12, step_delay=0.02)
        time.sleep(0.15)
        
        # Victory arms up
        smooth_move(130, 130, 170, 170, steps=8, step_delay=0.02)
        time.sleep(0.2)
        
        # Back to wide open
        smooth_move(170, 170, 180, 0, steps=10, step_delay=0.03)
        time.sleep(0.1)
    
    # Happy clapping motion
    for _ in range(3):
        # Arms apart
        smooth_move(180, 0, 100, 80, steps=6, step_delay=0.02)
        time.sleep(0.1)
        
        # Arms together (clap)
        smooth_move(100, 80, 90, 90, steps=4, step_delay=0.02)
        time.sleep(0.1)
    
    # Final flourish - happy wiggle
    for _ in range(2):
        smooth_move(90, 90, 120, 60, steps=5, step_delay=0.02)
        smooth_move(120, 60, 60, 120, steps=10, step_delay=0.02)
    
    # Return to neutral
    reset_to_neutral()

def express_sad():
    print("😢 SAD")
    
    # Initial slow droop
    smooth_move(90, 90, 70, 70, steps=20, step_delay=0.06)
    time.sleep(0.4)
    
    # Continue drooping down with slight asymmetry (one side droops more)
    smooth_move(70, 70, 50, 55, steps=15, step_delay=0.07)
    time.sleep(0.5)
    
    # Subtle sobbing motion - small trembles
    for _ in range(4):
        # Small trembling movement up
        smooth_move(50, 55, 53, 58, steps=5, step_delay=0.05)
        time.sleep(0.1)
        
        # Small trembling movement down
        smooth_move(53, 58, 48, 52, steps=5, step_delay=0.05)
        time.sleep(0.2)
    
    # Brief attempt to rise (hope) but failing
    smooth_move(48, 52, 65, 65, steps=12, step_delay=0.05)
    time.sleep(0.3)
    
    # Giving up and drooping again
    smooth_move(65, 65, 40, 40, steps=15, step_delay=0.07)
    time.sleep(0.6)
    
    # Final very slow recovery
    smooth_move(40, 40, 90, 90, steps=25, step_delay=0.08)

def express_surprise():
    print("😲 SURPRISED")
    
    # Quick startled movement
    smooth_move(90, 90, 170, 10, steps=5, step_delay=0.01)
    time.sleep(0.3)
    
    # Gasping motion (hands to "face")
    smooth_move(170, 10, 70, 110, steps=8, step_delay=0.03)
    time.sleep(0.4)
    
    # Hands away (realization)
    smooth_move(70, 110, 150, 30, steps=7, step_delay=0.04)
    time.sleep(0.2)
    
    # Double-take movement
    smooth_move(150, 30, 100, 80, steps=10, step_delay=0.02)
    time.sleep(0.1)
    smooth_move(100, 80, 160, 20, steps=6, step_delay=0.02)
    time.sleep(0.3)
    
    # Return to neutral with slight lingering surprise
    smooth_move(160, 20, 100, 80, steps=10, step_delay=0.04)
    time.sleep(0.2)
    reset_to_neutral()

def express_confused():
    print("🤔 CONFUSED")
    
    # Initial uncertain movement
    smooth_move(90, 90, 110, 70, steps=10, step_delay=0.04)
    time.sleep(0.3)
    
    # Head scratching motion (right arm up to "head")
    smooth_move(110, 70, 140, 70, steps=12, step_delay=0.05)
    time.sleep(0.4)
    
    # Oscillating indecisive movement
    for _ in range(3):
        # Lean left side
        smooth_move(140, 70, 120, 100, steps=8, step_delay=0.04)
        time.sleep(0.2)
        
        # Lean right side
        smooth_move(120, 100, 140, 60, steps=8, step_delay=0.04)
        time.sleep(0.2)
    
    # More scratching
    for _ in range(2):
        smooth_move(140, 60, 130, 60, steps=5, step_delay=0.03)
        time.sleep(0.1)
        smooth_move(130, 60, 140, 60, steps=5, step_delay=0.03)
        time.sleep(0.1)
    
    # Final shrug
    smooth_move(140, 60, 170, 170, steps=12, step_delay=0.04)
    time.sleep(0.5)
    
    # Return to neutral
    reset_to_neutral()

def express_excited():
    print("🤩 EXCITED")
    
    # Quick, bouncy start
    smooth_move(90, 90, 150, 30, steps=6, step_delay=0.02)
    time.sleep(0.1)
    
    # Enthusiastic arm waving
    for _ in range(3):
        # Arms up high
        smooth_move(150, 30, 170, 170, steps=7, step_delay=0.02)
        time.sleep(0.1)
        
        # Arms wide
        smooth_move(170, 170, 180, 0, steps=7, step_delay=0.02)
        time.sleep(0.1)
    
    # Excited bouncing
    for _ in range(4):
        # Quick up movement
        smooth_move(180, 0, 160, 20, steps=5, step_delay=0.01)
        
        # Quick down movement
        smooth_move(160, 20, 140, 40, steps=5, step_delay=0.01)
    
    # Rapid clapping
    for _ in range(5):
        # Arms apart
        smooth_move(140, 40, 110, 70, steps=4, step_delay=0.01)
        
        # Arms together (clap)
        smooth_move(110, 70, 90, 90, steps=4, step_delay=0.01)
    
    # Final excited flourish
    smooth_move(90, 90, 180, 0, steps=8, step_delay=0.02)
    time.sleep(0.2)
    smooth_move(180, 0, 170, 170, steps=8, step_delay=0.02)
    time.sleep(0.2)
    
    # Return to neutral
    reset_to_neutral()

def express_tired():
    print("😴 TIRED")
    
    # Slow initial movement
    smooth_move(90, 90, 80, 80, steps=20, step_delay=0.07)
    time.sleep(0.4)
    
    # Stretching/yawning motion
    smooth_move(80, 80, 150, 30, steps=25, step_delay=0.08)
    time.sleep(0.6)
    
    # Arms drooping unevenly
    smooth_move(150, 30, 60, 50, steps=22, step_delay=0.07)
    time.sleep(0.5)
    
    # Attempt to stay up but failing
    for _ in range(2):
        # Try to lift up
        smooth_move(60, 50, 70, 60, steps=12, step_delay=0.06)
        time.sleep(0.3)
        
        # Droop back down
        smooth_move(70, 60, 55, 45, steps=10, step_delay=0.07)
        time.sleep(0.4)
    
    # Final drowsy movement
    smooth_move(55, 45, 40, 40, steps=15, step_delay=0.08)
    time.sleep(0.7)
    
    # Very slow return to neutral
    smooth_move(40, 40, 90, 90, steps=30, step_delay=0.09)

def handle_emotion(emotion):
    """Map emotion code to function"""
    emotions = {
        -3: express_tired,
        -2: express_sad,
        -1: express_confused,
        0: express_happy,
        1: express_angry,
        2: express_surprise,
        3: express_excited
    }
    
    if emotion in emotions:
        emotions[emotion]()
    else:
        print("Unknown emotion code:", emotion)
        print("Available emotion codes: -3 (Tired), -2 (Sad), -1 (Confused), 0 (Happy), 1 (Angry), 2 (Surprise), 3 (Excited)")

def random_movement():
    """Perform a random movement sequence"""
    print("🎲 Random movement sequence")
    
    # Choose random angles
    random_right_1 = random.randint(30, 150)
    random_left_1 = random.randint(30, 150)
    random_right_2 = random.randint(30, 150)
    random_left_2 = random.randint(30, 150)
    
    # Random movement pattern
    smooth_move(90, 90, random_right_1, random_left_1, 
                steps=random.randint(8, 15), 
                step_delay=random.uniform(0.02, 0.05))
    time.sleep(random.uniform(0.1, 0.3))
    
    smooth_move(random_right_1, random_left_1, random_right_2, random_left_2,
                steps=random.randint(8, 15),
                step_delay=random.uniform(0.02, 0.05))
    time.sleep(random.uniform(0.1, 0.3))
    
    # Return to neutral
    reset_to_neutral()

def cleanup():
    """Clean up resources"""
    try:
        # No need to call GPIO cleanup - using I2C now
        print("Resources cleaned up")
    except:
        print("Error during cleanup")

def startup_sequence():
    """Run a start-up initialization sequence"""
    print("⚡ Starting robot arm system...")
    
    # Initial wake-up
    smooth_move(90, 90, 60, 60, steps=15, step_delay=0.05)
    time.sleep(0.3)
    
    # Test full range of motion
    smooth_move(60, 60, 150, 30, steps=18, step_delay=0.03)
    time.sleep(0.2)
    smooth_move(150, 30, 30, 150, steps=25, step_delay=0.03)
    time.sleep(0.2)
    
    # Return to neutral
    reset_to_neutral()
    
    # Say hi to complete startup
    say_hi()
    
    print("✅ Robot arm system initialized and ready!")

# Function to detect I2C devices
def scan_i2c_devices():
    """Scan for I2C devices and return their addresses"""
    bus = smbus.SMBus(1)  # 1 indicates /dev/i2c-1
    devices = []
    
    for address in range(0x03, 0x78):
        try:
            bus.read_byte(address)
            devices.append(f"0x{address:02X}")
        except:
            pass
    
    return devices

def main():
    """Main function to control the robot"""
    try:
        print("\n🤖 Raspberry Pi Robot Arm Control System 🤖")
        print("=" * 45)
        print("I2C Configuration:")
        print(f"  PWM Controller: 0x{PCA9685_ADDR:02X}")
        print("=" * 45)
        
        # Scan for I2C devices
        print("Scanning for I2C devices...")
        devices = scan_i2c_devices()
        print(f"Found I2C devices: {', '.join(devices)}")
        
        # Set PWM frequency (default is already 50Hz)
        print(f"Setting PWM frequency to 50Hz")
        pwm.frequency = 50
        
        # Run startup sequence
        startup_sequence()
        
        # Main control loop
        while True:
            print("\nAvailable Commands:")
            print("  1-7: Emotions")
            print("    1: Tired (-3)")
            print("    2: Sad (-2)")
            print("    3: Confused (-1)")
            print("    4: Happy (0)")
            print("    5: Angry (1)")
            print("    6: Surprise (2)")
            print("    7: Excited (3)")
            print("  Special Functions:")
            print("    h: Say Hi")
            print("    s: Search Movement")
            print("    r: Random Movement")
            print("    e: End Robot")
            print("    q: Quit Program")
            
            input_val = input("\nEnter command: ")
            
            if input_val.lower() == 'q':
                print("Quitting program...")
                break
            elif input_val.lower() == 'h':
                say_hi()
            elif input_val.lower() == 's':
                search_movement()
            elif input_val.lower() == 'r':
                random_movement()
            elif input_val.lower() == 'e':
                end_robot()
                time.sleep(1)  # Wait a moment after end sequence
            elif input_val in ['1', '2', '3', '4', '5', '6', '7']:
                # Convert menu option to emotion code
                emotion_map = {'1': -3, '2': -2, '3': -1, '4': 0, '5': 1, '6': 2, '7': 3}
                handle_emotion(emotion_map[input_val])
            else:
                try:
                    # Try to parse as direct emotion code
                    emotion_code = int(input_val)
                    handle_emotion(emotion_code)
                except ValueError:
                    print("Invalid command! Please use the menu options shown.")
    
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user")
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
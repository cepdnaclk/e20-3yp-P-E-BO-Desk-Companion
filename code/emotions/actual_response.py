import time
import random
from enum import Enum
import pygame  # For audio playback
import pyttsx3  # For text-to-speech

# Mock GPIO class for Windows development
class GPIO:
    BCM = 1
    OUT = 1
    
    @staticmethod
    def setmode(mode):
        print(f"GPIO.setmode({mode})")
    
    @staticmethod
    def setup(pin, mode):
        print(f"GPIO.setup(pin={pin}, mode={mode})")
    
    @staticmethod
    def cleanup():
        print("GPIO.cleanup()")
    
    class PWM:
        def __init__(self, pin, frequency):
            self.pin = pin
            self.frequency = frequency
            print(f"PWM initialized on pin {pin} with frequency {frequency}Hz")
        
        def start(self, duty_cycle):
            print(f"PWM started on pin {self.pin} with duty cycle {duty_cycle}%")
        
        def ChangeDutyCycle(self, duty_cycle):
            print(f"Changed duty cycle on pin {self.pin} to {duty_cycle}%")
        
        def stop(self):
            print(f"PWM stopped on pin {self.pin}")

class Emotion(Enum):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    NEUTRAL = "neutral"

class RobotController:
    def __init__(self):
        # Initialize GPIO
        GPIO.setmode(GPIO.BCM)
        
        # Servo motor pins setup for arm
        self.servo_pins = {
            "arm_base": 17,
            "arm_joint1": 18,
            "arm_joint2": 27
        }
        
        # Setup servo pins
        for pin in self.servo_pins.values():
            GPIO.setup(pin, GPIO.OUT)
            
        # Initialize PWM for servos
        self.servo_pwm = {}
        for name, pin in self.servo_pins.items():
            self.servo_pwm[name] = GPIO.PWM(pin, 50)  # 50Hz frequency
            self.servo_pwm[name].start(7.5)  # Initialize to middle position
        
        # Initialize audio
        pygame.mixer.init()
        
        # Initialize Text-to-Speech Engine
        self.engine = pyttsx3.init()
        
        # Define responses for each emotion
        self.responses = {
            Emotion.HAPPY: "You look so happy! What made your day so great?",
            Emotion.SAD: "I'm here to listen. Do you want to talk about what's making you sad?",
            Emotion.ANGRY: "Don't let anger take over. I'm here for you. Want to talk about it?",
            Emotion.SURPRISED: "Wow! You look surprised! What happened?",
            Emotion.NEUTRAL: "I notice you're feeling neutral. How's your day going?"
        }
        
        # Define emoji displays for each emotion
        self.emoji_displays = {
            Emotion.HAPPY: "💖 Stay happy! 😊",
            Emotion.SAD: "💙 I'm here for you ❤️",
            Emotion.ANGRY: "❤️ Take a deep breath! 🤗",
            Emotion.SURPRISED: "😲 What a surprise! ✨",
            Emotion.NEUTRAL: "😐 Just another day 🌤️"
        }
        
        # Define sound files - optional background sounds
        self.sound_files = {
            Emotion.HAPPY: "sounds/happy.mp3",
            Emotion.SAD: "sounds/sad.mp3",
            Emotion.ANGRY: "sounds/angry.mp3",
            Emotion.SURPRISED: "sounds/surprised.mp3",
            Emotion.NEUTRAL: "sounds/neutral.mp3"
        }
        
        # Mock display information
        self.display_width = 128
        self.display_height = 64
        
        print("Robot controller initialized")
    
    def speak(self, text):
        """Speak the given text using text-to-speech."""
        print(f"🔊 Speaking: \"{text}\"")
        self.engine.say(text)
        self.engine.runAndWait()
    
    def set_servo_angle(self, servo_name, angle):
        """Set servo to specified angle (0-180 degrees)"""
        if servo_name not in self.servo_pwm:
            print(f"Servo {servo_name} not found")
            return
            
        # Convert angle to duty cycle (2.5% - 12.5%)
        duty_cycle = 2.5 + (angle / 180) * 10
        self.servo_pwm[servo_name].ChangeDutyCycle(duty_cycle)
        print(f"Setting {servo_name} to {angle} degrees")
        time.sleep(0.3)  # Give time for servo to move
    
    def play_sound(self, emotion):
        """Play background sound based on emotion"""
        if emotion in self.sound_files:
            try:
                sound_file = self.sound_files[emotion]
                print(f"Playing background sound: {sound_file}")
                
                # Try to play the sound file if it exists
                try:
                    pygame.mixer.music.load(sound_file)
                    pygame.mixer.music.play()
                except pygame.error:
                    print(f"Note: Background sound file '{sound_file}' not found. This is optional.")
                    
            except Exception as e:
                print(f"Error playing sound: {e}")
    
    def update_display(self, emotion):
        """Update the display with emotion-specific content"""
        # In a real implementation, this would update an actual display
        # For now, we'll simulate with console output
        
        # Print emoji display for the emotion
        print(f"\n{self.emoji_displays[emotion]}")
        
        # Show text-based visualization of what would appear on the display
        displays = {
            Emotion.HAPPY: """
            Display:
            ┌──────────┐
            │  ┌─┐ ┌─┐  │
            │  │*│ │*│  │
            │   ───────  │
            │    \___/   │
            │ HAPPY :)  │
            └──────────┘
            """,
            Emotion.SAD: """
            Display:
            ┌──────────┐
            │  ┌─┐ ┌─┐  │
            │  │*│ │*│  │
            │           │
            │    /‾‾‾\   │
            │  SAD :(   │
            └──────────┘
            """,
            Emotion.ANGRY: """
            Display:
            ┌──────────┐
            │  ┌─┐ ┌─┐  │
            │  │*│ │*│  │
            │   ‾‾‾‾‾‾‾  │
            │    /‾‾‾\   │
            │ ANGRY >:( │
            └──────────┘
            """,
            Emotion.SURPRISED: """
            Display:
            ┌──────────┐
            │  ┌─┐ ┌─┐  │
            │  │O│ │O│  │
            │           │
            │     O     │
            │SURPRISED! │
            └──────────┘
            """,
            Emotion.NEUTRAL: """
            Display:
            ┌──────────┐
            │  ┌─┐ ┌─┐  │
            │  │*│ │*│  │
            │           │
            │    ────   │
            │ NEUTRAL   │
            └──────────┘
            """
        }
        
        print(displays[emotion])
    
    def respond_to_emotion(self, emotion_str):
        """Main function to respond to an emotion input"""
        try:
            # Convert string to Emotion enum
            try:
                emotion = Emotion(emotion_str.lower())
            except ValueError:
                print(f"\nSorry, I don't recognize the emotion: {emotion_str}")
                self.speak("I didn't understand what you're feeling. I can respond to happy, sad, angry, surprised, or neutral.")
                return f"Unknown emotion: {emotion_str}. Valid emotions are: {', '.join([e.value for e in Emotion])}"
                
            print(f"\n===============================")
            print(f"Processing emotion: {emotion.value}")
            print(f"===============================")
            
            # Update the display
            self.update_display(emotion)
            
            # Speak the appropriate response
            self.speak(self.responses[emotion])
            
            # Optionally play background sound
            self.play_sound(emotion)
            
            # Simulate arm movement patterns based on emotion
            print("\n🤖 ARM MOVEMENTS:")
            if emotion == Emotion.HAPPY:
                self.set_servo_angle("arm_base", 90)
                self.set_servo_angle("arm_joint1", 45)
                self.set_servo_angle("arm_joint2", 90)
                # Happy wave motion
                print("  Performing happy wave motion!")
                for _ in range(3):
                    self.set_servo_angle("arm_joint2", 60)
                    self.set_servo_angle("arm_joint2", 120)
            
            elif emotion == Emotion.SAD:
                self.set_servo_angle("arm_base", 90)
                self.set_servo_angle("arm_joint1", 120)
                self.set_servo_angle("arm_joint2", 30)
                print("  Arm drooping down in sadness")
            
            elif emotion == Emotion.ANGRY:
                # Quick, sharp movements
                print("  Making sharp, agitated movements")
                self.set_servo_angle("arm_base", 45)
                self.set_servo_angle("arm_joint1", 90)
                self.set_servo_angle("arm_joint2", 45)
                self.set_servo_angle("arm_base", 135)
                self.set_servo_angle("arm_base", 90)
            
            elif emotion == Emotion.SURPRISED:
                # Sudden upward movement
                print("  Quick upward surprised motion")
                self.set_servo_angle("arm_base", 90)
                self.set_servo_angle("arm_joint1", 30)
                self.set_servo_angle("arm_joint2", 150)
            
            elif emotion == Emotion.NEUTRAL:
                # Return to resting position
                print("  Returning to neutral position")
                self.set_servo_angle("arm_base", 90)
                self.set_servo_angle("arm_joint1", 90)
                self.set_servo_angle("arm_joint2", 90)
                
            return f"Successfully responded to {emotion.value} emotion"
            
        except Exception as e:
            print(f"Error processing emotion: {e}")
            return f"Error: {str(e)}"
    
    def cleanup(self):
        """Clean up GPIO and other resources"""
        for pwm in self.servo_pwm.values():
            pwm.stop()
        GPIO.cleanup()
        pygame.mixer.quit()
        print("Robot resources cleaned up")

# Example usage
if __name__ == "__main__":
    robot = RobotController()
    
    try:
        print("\n=================================")
        print("🤖 P-E-BO Desk Companion")
        print("Emotion Response System")
        print("=================================")
        
        # Interactive mode
        while True:
            emotion = input("\nEnter an emotion (happy, sad, angry, surprised, neutral) or 'exit' to quit: ").strip()
            
            if emotion.lower() == "exit":
                print("\n👋 Goodbye! Take care!")
                robot.speak("Goodbye! Take care!")
                break
            
            result = robot.respond_to_emotion(emotion)
            time.sleep(1)  # Small delay before next input
    
    finally:
        robot.cleanup()
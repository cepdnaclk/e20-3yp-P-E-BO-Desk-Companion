import pyttsx3
import re
import random
import time
import platform

class CuteRobotVoice:
    def __init__(self):
        """Initialize the text-to-speech engine with cute robot voice settings"""
        # Initialize the TTS engine
        self.engine = pyttsx3.init()
        
        # Configure voice properties for a cute robot sound
        # Use faster rate for a cuter robotic voice
        self.engine.setProperty('rate', 170)  # Speaking rate - slightly faster than default for robot effect
        self.engine.setProperty('volume', 0.9)  # Volume level
        
        # Get available voices and set to a female voice if available
        voices = self.engine.getProperty('voices')
        female_voices = [voice for voice in voices if hasattr(voice, 'name') and 'female' in voice.name.lower()]
        
        # If we couldn't find female voices by name, try to find by ID (common on Windows)
        if not female_voices:
            # On Windows, voice IDs with "Zira" or similar are typically female
            female_voices = [voice for voice in voices if hasattr(voice, 'id') and 
                            ('zira' in voice.id.lower() or 
                             'hazel' in voice.id.lower() or 
                             'helena' in voice.id.lower())]
        
        if female_voices:
            self.engine.setProperty('voice', female_voices[0].id)
        elif voices:
            self.engine.setProperty('voice', voices[0].id)
        
        # Don't attempt to adjust pitch on Windows SAPI5
        # We'll use other methods to create cute robot effect
        
        # Robot speech patterns
        self.robot_interjections = [
            "Beep! ", "Boop! ", "Whirr~ ", "Click! ", "Bzzt~ ", "*digital hum* ",
            "Processing~ ", "Computing~ ", "Analyzing~ "
        ]
        
        self.robot_endings = [
            " *beep*", " *boop*", " ~end of transmission~", " ~does not compute~", 
            " ~processing complete~", " ~affirmative~", " ~executing~"
        ]
        
        self.cute_expressions = [
            " *happy chirp*", " *excited whirr*", " *digital giggle*", 
            " *sparkly beep*", " *cheerful boop sequence*"
        ]

    def robotify_text(self, text):
        """Convert normal text to cute robot speech patterns"""
        result = text
        
        # Add robotic word replacements
        replacements = {
            r'\bI am\b': 'This unit is',
            r'\bI\b': 'this unit',
            r'\bmy\b': 'this unit\'s',
            r'\bme\b': 'this unit',
            r'\byou\b': 'user',
            r'\byour\b': 'user\'s',
            r'\byes\b': 'affirmative',
            r'\bno\b': 'negative',
            r'\bhello\b': 'greetings',
            r'\bgoodbye\b': 'terminating interaction',
            r'\bfriend\b': 'companion unit',
            r'\bhappy\b': 'operating at optimal satisfaction parameters',
            r'\bsad\b': 'experiencing lowered operational efficiency',
            r'\blove\b': 'maximum affinity protocol',
            r'\bsorry\b': 'error acknowledged'
        }
        
        for pattern, replacement in replacements.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # Split into sentences
        sentences = re.split(r'([.!?]+\s*)', result)
        processed_sentences = []
        
        for i in range(0, len(sentences), 2):
            if i < len(sentences) and sentences[i].strip():
                sentence = sentences[i]
                
                # Add random robot interjection at the beginning (30% chance)
                if random.random() < 0.3:
                    sentence = random.choice(self.robot_interjections) + sentence
                
                # Add stutter to random words (20% chance per word)
                words = sentence.split()
                for j in range(len(words)):
                    if random.random() < 0.2 and len(words[j]) > 2:
                        first_letter = words[j][0]
                        words[j] = f"{first_letter}-{words[j]}"
                
                sentence = ' '.join(words)
                
                # Add cute expression for positive sentences (25% chance)
                if any(word in sentence.lower() for word in ['good', 'nice', 'happy', 'love', 'like', 'affirmative']):
                    if random.random() < 0.25:
                        sentence += random.choice(self.cute_expressions)
                
                processed_sentences.append(sentence)
                
                # Add ending punctuation if it exists
                if i + 1 < len(sentences):
                    # Add robot ending to some sentences (20% chance)
                    if random.random() < 0.2:
                        processed_sentences.append(random.choice(self.robot_endings))
                    else:
                        processed_sentences.append(sentences[i+1])
        
        result = ''.join(processed_sentences)
        
        # Simulate digital processing by occasionally inserting pauses in speech
        result = result.replace('. ', '. <pause> ')
        result = result.replace('! ', '! <pause> ')
        result = result.replace('? ', '? <pause> ')
        
        return result

    def speak(self, text):
        """Speak the text with cute robot voice effects"""
        robot_text = self.robotify_text(text)
        
        # Process special pause markers
        speech_segments = robot_text.split('<pause>')
        
        # Handle the speech segments
        for segment in speech_segments:
            if segment.strip():
                # Create robotic effect with alternating rates for Windows
                # Since we can't modify pitch on Windows SAPI5, we'll use rate changes instead
                current_rate = self.engine.getProperty('rate')
                
                # Alternate between slightly faster and slower for robotic effect
                if random.random() < 0.5:
                    self.engine.setProperty('rate', current_rate + random.randint(10, 30))
                else:
                    self.engine.setProperty('rate', current_rate - random.randint(5, 15))
                    
                # Speak the segment
                self.engine.say(segment)
                self.engine.runAndWait()
                
                # Reset rate to default
                self.engine.setProperty('rate', 170)
                
                # Small pause between segments
                time.sleep(0.2)

def main():
    """Main function to run the cute robot voice assistant"""
    print("🤖✨ Cute Robot Voice Assistant ✨🤖")
    print("Type text for your robot to speak (or 'exit' to quit):")
    
    try:
        robot = CuteRobotVoice()
        
        while True:
            user_input = input("\nText for robot to speak: ")
            if user_input.lower() in ['exit', 'quit']:
                print("Shutting down robot voice system... Goodbye!")
                break
                
            print("🤖 Speaking with cute robot voice...")
            robot.speak(user_input)
    except Exception as e:
        print(f"An error occurred: {e}")
        print("\nTrying alternative approach...")
        
        # Simplified fallback approach for systems with limited TTS capabilities
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        
        if voices:
            # Try to set a female voice if available
            for voice in voices:
                if hasattr(voice, 'id'):
                    print(f"Available voice: {voice.id}")
            
            # Set the first available voice
            engine.setProperty('voice', voices[0].id)
        
        # Set a faster rate for a cuter effect
        engine.setProperty('rate', 180)
        engine.setProperty('volume', 0.9)
        
        print("Using simplified robot voice. Type text (or 'exit' to quit):")
        while True:
            text = input("\nText: ")
            if text.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
                
            # Simple text transformation
            text = text.replace("I ", "This unit ").replace("my ", "this unit's ")
            text = f"Beep boop! {text} *whirr*"
            
            engine.say(text)
            engine.runAndWait()

if __name__ == "__main__":
    main()
import pyttsx3
import time

def cute_female_voice(text):
    """
    Function to speak text with a cute female voice effect
    """
    # Initialize the engine
    engine = pyttsx3.init()
    
    # Find a female voice
    voices = engine.getProperty('voices')
    female_voice_id = None
    for voice in voices:
        if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
            female_voice_id = voice.id
            break
    
    # Set voice properties
    if female_voice_id:
        engine.setProperty('voice', female_voice_id)
        print(f"Using female voice: {female_voice_id}")
    else:
        print("Using default voice as no female voice was found.")
    
    # Adjust speed and pitch for a cuter voice
    engine.setProperty('rate', 150)    # Slightly slower speech rate
    engine.setProperty('volume', 1.0)  # Max volume
    
    # Speak the text
    engine.say(text)
    engine.runAndWait()
    
def echo_effect(text, echo_count=2, delay=0.3):
    """
    Creates an echo effect by repeating the text with decreasing volume
    """
    engine = pyttsx3.init()
    
    # Find a female voice
    voices = engine.getProperty('voices')
    female_voice_id = None
    for voice in voices:
        if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
            female_voice_id = voice.id
            break
    
    # Set voice properties
    if female_voice_id:
        engine.setProperty('voice', female_voice_id)
    
    # Speak the original text
    engine.setProperty('volume', 1.0)
    engine.setProperty('rate', 150)
    engine.say(text)
    engine.runAndWait()
    
    # Create echo effect with decreasing volume
    volume = 0.7
    for _ in range(echo_count):
        time.sleep(delay)
        engine.setProperty('volume', volume)
        engine.say(text)
        engine.runAndWait()
        volume *= 0.6  # Decrease volume for each echo

# Example usage
message = "Hi there! I'm your cute and bubbly assistant!"
print("Speaking with cute female voice...")
cute_female_voice(message)

print("\nSpeaking with echo effect...")
echo_effect(message, echo_count=2, delay=0.4)
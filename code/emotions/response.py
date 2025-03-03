import pyttsx3
import time

# Initialize Text-to-Speech Engine
engine = pyttsx3.init()

def speak(text):
    """Speak the given text."""
    engine.say(text)
    engine.runAndWait()

def respond_to_emotion(emotion):
    """Respond based on the detected emotion."""
    if emotion.lower() == "happy":
        print("\n💖Stay happy!😊")
        speak("You look so happy! What made your day so great?")
    
    elif emotion.lower() == "sad":
        print("\n💙I'm here for you❤️")
        speak("I’m here to listen. Do you want to talk about what’s making you sad?")
    
    elif emotion.lower() == "angry":
        print("\n❤️Take a deep breath!🤗")
        speak("Don't let anger take over. I'm here for you. Want to talk about it?")
    
    else:
        print("\n sorry")
        speak("I didn't understand whats your feeling.")

# Main Loop
while True:
    emotion = input("\nEnter an emotion (happy, sad, angry) or 'exit' to quit: ").strip()
    
    if emotion.lower() == "exit":
        print("\n👋 Goodbye! Take care!")
        speak("Goodbye! Take care!")
        break
    
    respond_to_emotion(emotion)
    time.sleep(1)  # Small delay before next input

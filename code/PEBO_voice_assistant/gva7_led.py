import google.generativeai as genai
import pygame
import time
import os
import asyncio
import edge_tts
import speech_recognition as sr

# Initialize pygame for audio playback
pygame.mixer.init()

# Set up Google Gemini API key
GOOGLE_API_KEY = "AIzaSyDjx04eYTq-09j7kzd24NeZfwYZ7eu3w9Q"
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize the Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")

# Conversation history for context
conversation_history = []

# Initialize speech recognizer
recognizer = sr.Recognizer()
mic = sr.Microphone()

async def speak_text(text):
    """Convert text to speech using Edge TTS and play it."""
    voice = "en-US-AriaNeural"  # Change voice if needed
    filename = "response.mp3"
    
    tts = edge_tts.Communicate(text, voice)
    await tts.save(filename)
    
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
    
    while pygame.mixer.music.get_busy():
        time.sleep(0.5)
    
    pygame.mixer.music.stop()
    pygame.mixer.music.unload()
    os.remove(filename)

def listen():
    """Continuously listen for speech and convert it to text."""
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Listening... Speak now.")
        
        try:
            audio = recognizer.listen(source, timeout=20)
            text = recognizer.recognize_google(audio)
            print(f"You: {text}")
            return text
        except sr.UnknownValueError:
            print("Couldn't understand. Try again.")
            return None
        except sr.RequestError:
            print("Speech Recognition API unavailable.")
            return None

async def main():
    print("Chat with Gemini! Say 'exit' to stop.")
    
    while True:
        user_input = listen()
        
        if user_input is None:
            continue  # Retry if STT failed
        
        if user_input.lower() == "exit":
            print("Goodbye!")
            await speak_text("Goodbye!")
            break  # Exit the loop
        
        # Append user message to conversation history
        conversation_history.append({"role": "user", "parts": ["Answer briefly with max two sentences: " + user_input]})
        
        # Generate response from Gemini
        response = model.generate_content(conversation_history, generation_config={"max_output_tokens": 100})
        
        ai_response = response.text
        
        # Print and speak Gemini's response
        print(f"Gemini: {ai_response}")
        await speak_text(ai_response)
        
        # Append AI response to conversation history
        conversation_history.append({"role": "model", "parts": [ai_response]})

if __name__ == "__main__":
    asyncio.run(main())
    
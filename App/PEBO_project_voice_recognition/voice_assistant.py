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
GOOGLE_API_KEY = "AIzaSyDjx04eYTq-09j7kzd24NeZfwYZ7eu3w9Q"  # Replace with your actual API key
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize the Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")

# Conversation history for context
conversation_history = []

print("?? Speak to Gemini! Say 'exit' to stop.")

async def speak_text(text):
    """Convert text to speech using Edge TTS and play it."""
    voice = "en-US-AriaNeural"  # Change voice if needed (e.g., "en-GB-RyanNeural")
    filename = "response.mp3"

    tts = edge_tts.Communicate(text, voice)
    await tts.save(filename)

    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        time.sleep(0.25)

    pygame.mixer.music.stop()
    pygame.mixer.music.unload()  # Unload before deleting
    os.remove(filename)  # Safe to delete now

def get_voice_input():
    """Capture and process speech input using the microphone."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("?? Listening... Speak clearly.")
        recognizer.adjust_for_ambient_noise(source, duration=1)  # Reduce noise
        try:
            audio = recognizer.listen(source, timeout=8)  # Listen for up to 8 sec
            text = recognizer.recognize_google(audio)
            return text.lower()
        except sr.UnknownValueError:
            print("?? Couldn't understand. Try again.")
            return None
        except sr.RequestError:
            print("? Speech Recognition service is unavailable.")
            return None

while True:
    print("?? Say something...")
    user_input = get_voice_input()

    if not user_input:
        continue  # Skip if input is not understood

    if user_input.lower() == "exit":
        print("?? Goodbye!")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(speak_text("Goodbye!"))
        break  # Exit the loop

    # Append user message to conversation history
    conversation_history.append({"role": "user", "parts": ["Answer briefly with max two sentences: " + user_input]})

    # Generate response from Gemini
    response = model.generate_content(conversation_history, generation_config={"max_output_tokens": 30})

    ai_response = response.text

    # Print and speak Gemini's response
    print(f"?? Gemini: {ai_response}")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(speak_text(ai_response))

    # Append AI response to conversation history
    conversation_history.append({"role": "model", "parts": [ai_response]})
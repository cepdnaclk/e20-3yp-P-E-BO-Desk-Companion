import google.generativeai as genai
import pygame
import time
import os
import asyncio
import edge_tts
import speech_recognition as sr

# Initialize pygame
pygame.mixer.init()

# Gemini API setup
GOOGLE_API_KEY = "AIzaSyDjx04eYTq-09j7kzd24NeZfwYZ7eu3w9Q"
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Gemini memory
conversation_history = []

# Speech recognizer
recognizer = sr.Recognizer()
mic = sr.Microphone()

async def speak_text(text):
    """Speak using Edge TTS."""
    voice = "en-US-AriaNeural"
    filename = "response.mp3"

    tts = edge_tts.Communicate(text, voice)
    await tts.save(filename)

    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.25)

    pygame.mixer.music.stop()
    pygame.mixer.music.unload()
    os.remove(filename)

def listen():
    """Listen for one voice input."""
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        print("?? Listening...")
        try:
            audio = recognizer.listen(source, timeout=10)
            text = recognizer.recognize_google(audio)
            print(f"You: {text}")
            return text
        except sr.UnknownValueError:
            print("? Didn't understand.")
            return None
        except sr.RequestError:
            print("? Speech recognition failed.")
            return None

def start_assistant_from_text(prompt_text):
    """Starts Gemini assistant with initial text prompt."""
    print(f"?? Initial Prompt: {prompt_text}")
    conversation_history.clear()
    conversation_history.append({"role": "user", "parts": [prompt_text]})

    response = model.generate_content(conversation_history, generation_config={"max_output_tokens": 60})
    reply = response.text
    print(f"Gemini: {reply}")
    asyncio.run(speak_text(reply))

    conversation_history.append({"role": "model", "parts": [reply]})

    # Continue with voice input/output loop
    while True:
        user_input = listen()
        if user_input is None:
            continue
        if user_input.lower() == "exit":
            print("?? Exiting assistant.")
            asyncio.run(speak_text("Goodbye!"))
            break

        conversation_history.append({"role": "user", "parts": [user_input]})
        response = model.generate_content(conversation_history, generation_config={"max_output_tokens": 60})
        reply = response.text
        print(f"Gemini: {reply}")
        asyncio.run(speak_text(reply))
        conversation_history.append({"role": "model", "parts": [reply]})
        
if __name__ == "__main__":
    start_assistant_from_text("I am Nimal. I look tired. Ask why.")


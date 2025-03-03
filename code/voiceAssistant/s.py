import google.generativeai as genai
import pygame
import time
import os
import asyncio
import edge_tts

# Initialize pygame for audio playback
pygame.mixer.init()

# Set up Google Gemini API key
GOOGLE_API_KEY = "api"  
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize the Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")

# Conversation history for context
conversation_history = []

print("Chat with Gemini! Type 'exit' to stop.")

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

while True:
    user_input = input("You: ")

    if user_input.lower() == "exit":
        print("Goodbye!")
        asyncio.run(speak_text("Goodbye!"))
        break  # Exit the loop

    # Append user message to conversation history
    conversation_history.append({"role": "user", "parts": ["Answer briefly with max two sentence: " + user_input]})



    # Generate response from Gemini
    response = model.generate_content(conversation_history, generation_config={"max_output_tokens": 50}) 

    ai_response = response.text

    # Print and speak Gemini's response
    print(f"Gemini: {ai_response}")
    asyncio.run(speak_text(ai_response))

    # Append AI response to conversation history
    conversation_history.append({"role": "model", "parts": [ai_response]})

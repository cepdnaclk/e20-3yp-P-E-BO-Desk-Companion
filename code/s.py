import google.generativeai as genai
import speech_recognition as sr
import pyttsx3
import os
import pygame
import time
from gtts import gTTS
from datetime import date

# Initialize pygame for audio playback
pygame.mixer.init()

# Set the Google Gemini API key (replace with your actual API key)
genai.configure(api_key="AIzaSyDjx04eYTq-09j7kzd24NeZfwYZ7eu3w9Q")

today = str(date.today())

# Initialize Google Gemini API model
model = genai.GenerativeModel('gemini-1.5-flash')

def speak_text(text):
    """Convert text to speech using gTTS and play it."""
    tts = gTTS(text=text, lang='en')
    tts.save("response.mp3")
    
    pygame.mixer.music.load("response.mp3")
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        time.sleep(0.25)

    pygame.mixer.music.stop()
    os.remove("response.mp3")  # Clean up the file

talk = []

def append2log(text):
    """Save conversation logs to a file."""
    global today
    fname = 'chatlog-' + today + '.txt'
    with open(fname, "a") as f:
        f.write(text + "\n")

def main():
    global talk, today, model  
    
    rec = sr.Recognizer()
    mic = sr.Microphone()
    rec.dynamic_energy_threshold = False
    rec.energy_threshold = 400  # Adjust based on background noise
    
    sleeping = True  # AI starts in sleep mode
    
    while True:     
        with mic as source1:            
            rec.adjust_for_ambient_noise(source1, duration=0.5)
            print("Listening ...")
            
            try: 
                audio = rec.listen(source1, timeout=10, phrase_time_limit=15)
                text = rec.recognize_google(audio)
                
                if sleeping:
                    if "pebo" in text.lower(): 
                        request = text.lower().split("pebo")[1]
                        sleeping = False
                        append2log("_" * 40)
                        talk = []
                        today = str(date.today()) 
                        
                        if len(request) < 5:
                            speak_text("Hi, there, how can I help?")
                            append2log("AI: Hi, there, how can I help?\n")
                            continue
                    else:
                        continue
                else: 
                    request = text.lower()
                    
                    if "that's all" in request:  # User wants to end the chat
                        append2log(f"You: {request}\n")
                        speak_text("Bye now")
                        append2log("AI: Bye now.\n")
                        print('Bye now')
                        sleeping = True  # Go back to sleep mode
                        continue
                    
                    if "pebo" in request:
                        request = request.split("pebo")[1]                        
                
                # Process user's request
                append2log(f"You: {request}\n")
                print(f"You: {request}\n AI: ")
                talk.append({'role': 'user', 'parts': [request]})

                response = model.generate_content(talk, stream=True)

                ai_response = ""
                for chunk in response:
                    print(chunk.text, end='') 
                    ai_response += chunk.text.replace("*", "")

                print('\n')
                speak_text(ai_response)
                talk.append({'role': 'model', 'parts': [ai_response]})
                append2log(f"AI: {ai_response}\n")
 
            except Exception:
                continue
 
if __name__ == "__main__":
    main()
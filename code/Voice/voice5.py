# import pyttsx3

# def text_to_robo_voice(text, save_to_file=False, filename="robo_voice.mp3"):
#     # Initialize the text-to-speech engine
#     engine = pyttsx3.init()
    
#     # Set properties for the cute robo voice
#     engine.setProperty('rate', 150)  # Speed of speech
#     engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
    
#     # Try to set a higher pitch for cuteness (works better on some systems)
#     try:
#         engine.setProperty('pitch', 1.5)  # Higher pitch for cuteness
#     except:
#         print("Pitch adjustment not supported on this system")
    
#     # Get available voices and try to find a robotic one
#     voices = engine.getProperty('voices')
    
#     # Try to find a robotic voice (varies by system)
#     for voice in voices:
#         if "robot" in voice.name.lower() or "zira" in voice.name.lower():
#             engine.setProperty('voice', voice.id)
#             break
#     else:
#         print("No specific robotic voice found - using default")
    
#     # Convert text to speech
#     if save_to_file:
#         # Save to file (requires pydub and ffmpeg for mp3)
#         try:
#             engine.save_to_file(text, filename)
#             engine.runAndWait()
#             print(f"Saved cute robo voice to {filename}")
#         except Exception as e:
#             print(f"Couldn't save to file: {e}. Playing instead.")
#             engine.say(text)
#             engine.runAndWait()
#     else:
#         engine.say(text)
#         engine.runAndWait()

# if __name__ == "__main__":
#     print("Cute Robo Voice Converter")
#     text = input("Enter text to convert to cute robo voice: ")
#     save_option = input("Save to file? (y/n): ").lower().strip() == 'y'
    
#     if save_option:
#         filename = input("Enter filename (default: robo_voice.mp3): ") or "robo_voice.mp3"
#         text_to_robo_voice(text, save_to_file=True, filename=filename)
#     else:
#         text_to_robo_voice(text)


from gtts import gTTS
import os
import pygame
import numpy as np
from pydub import AudioSegment, effects
import simpleaudio as sa

def text_to_robo_voice(text, filename="robo_voice.mp3", play_immediately=True):
    try:
        # Create standard TTS
        print("Generating speech...")
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save("temp.mp3")
        
        # Load audio file
        sound = AudioSegment.from_mp3("temp.mp3")
        
        # Apply robotic effects
        print("Applying effects...")
        # Speed up slightly
        sound = effects.speedup(sound, playback_speed=1.2)
        
        # Add bit reduction effect for robotic sound
        samples = np.array(sound.get_array_of_samples())
        reduced_samples = (samples // 64) * 64  # Simple bit reduction
        robotic_sound = sound._spawn(reduced_samples.tobytes())
        
        # Add some echo
        echo = robotic_sound - 6  # Quieter echo
        combined = robotic_sound.overlay(echo, position=150)  # 150ms delay
        
        # Save final version
        print("Saving output...")
        combined.export(filename, format="mp3")
        os.remove("temp.mp3")
        
        # Play the sound if requested
        if play_immediately:
            print("Playing...")
            pygame.mixer.init()
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if os.path.exists("temp.mp3"):
            os.remove("temp.mp3")

if __name__ == "__main__":
    # Initialize pygame mixer
    pygame.mixer.init()
    
    print("Robo Voice Converter")
    while True:
        text = input("Enter text to convert to robo voice (or 'quit' to exit): ")
        if text.lower() == 'quit':
            break
        text_to_robo_voice(text)
import pyttsx3

def cute_robo_voice(text):
    # Initialize the text-to-speech engine
    engine = pyttsx3.init()

    # Set properties for a cute robotic voice
    voices = engine.getProperty('voices')

    # Select a voice (try different ones if needed)
    engine.setProperty('voice', voices[1].id)  # Change index for different voices
    engine.setProperty('rate', 120)  # Increase speed for a lively tone
    engine.setProperty('volume', 1.0)  # Full volume
    engine.setProperty('pitch', 100)  # High pitch for a cute sound (if supported)

    # Speak the text
    engine.say(text)
    engine.runAndWait()

# Example usage
cute_robo_voice("Hello! I am your cute robot assistant!")

# import pyttsx3
# import random
# import time

# class CuteVoiceGenerator:
#     def __init__(self):
#         # Initialize the text-to-speech engine
#         self.engine = pyttsx3.init()
#         self.set_best_voice()
        
#     def set_best_voice(self):
#         """Find and set the best voice for a cute effect"""
#         voices = self.engine.getProperty('voices')
        
#         # Print available voices to help with selection
#         print("Available voices:")
#         for i, voice in enumerate(voices):
#             print(f"{i}: {voice.name} ({voice.id})")
        
#         # First try to find a female voice
#         female_voice = None
#         for voice in voices:
#             if "female" in voice.name.lower() or "f" in voice.id.lower():
#                 female_voice = voice
#                 break
        
#         # Use female voice if found, otherwise use the first voice
#         if female_voice:
#             print(f"Selected female voice: {female_voice.name}")
#             self.engine.setProperty('voice', female_voice.id)
#         else:
#             print(f"No female voice found, using: {voices[1].name}")
#             self.engine.setProperty('voice', voices[1].id)
    
#     def cute_voice_standard(self, text):
#         """Standard cute voice - higher rate, clear pronunciation"""
#         self.engine.setProperty('rate', 180)  # Slightly faster than normal
#         self.engine.setProperty('volume', 1.0)
        
#         self.engine.say(text)
#         self.engine.runAndWait()
    
#     def cute_voice_tiny(self, text):
#         """Tiny cute voice - very fast, higher pitched effect"""
#         self.engine.setProperty('rate', 220)  # Very fast for tiny effect
#         self.engine.setProperty('volume', 0.9)
        
#         # Split text into shorter segments to create a "tiny" effect
#         words = text.split()
#         for i in range(0, len(words), 3):
#             segment = " ".join(words[i:i+3])
#             self.engine.say(segment)
#             self.engine.runAndWait()
#             time.sleep(0.15)  # Brief pause between segments
    
#     def cute_voice_bubbly(self, text):
#         """Bubbly cute voice - varied speed with pauses"""
#         self.engine.setProperty('volume', 1.0)
        
#         # Break text into sentences or phrases
#         phrases = text.replace("!", ".").replace("?", ".").split(".")
#         phrases = [p.strip() for p in phrases if p.strip()]
        
#         for phrase in phrases:
#             if not phrase:
#                 continue
                
#             # Random rate for each phrase for a bubbly effect
#             self.engine.setProperty('rate', random.randint(170, 210))
#             self.engine.say(phrase)
#             self.engine.runAndWait()
            
#             # Add a small pause between phrases
#             time.sleep(0.2)
    
#     def cute_voice_sing_song(self, text):
#         """Sing-song cute voice - alternating speeds"""
#         words = text.split()
        
#         for i, word in enumerate(words):
#             # Alternate between fast and slow to create sing-song effect
#             if i % 2 == 0:
#                 self.engine.setProperty('rate', 200)  # Faster
#                 self.engine.setProperty('volume', 1.0)
#             else:
#                 self.engine.setProperty('rate', 150)  # Slower
#                 self.engine.setProperty('volume', 0.9)
                
#             self.engine.say(word)
#             self.engine.runAndWait()
            
#             # Tiny pause between words
#             time.sleep(0.05)

# def speak_with_all_voices(text):
#     """Demonstrate all available cute voices"""
#     generator = CuteVoiceGenerator()
    
#     print("\n1. Standard Cute Voice:")
#     generator.cute_voice_standard(text)
    
#     print("\n2. Tiny Cute Voice:")
#     generator.cute_voice_tiny(text)
    
#     print("\n3. Bubbly Cute Voice:")
#     generator.cute_voice_bubbly(text)
    
#     print("\n4. Sing-Song Cute Voice:")
#     generator.cute_voice_sing_song(text)

# # Example usage
# if __name__ == "__main__":
#     sample_text = "Hello! I am your cute robot assistant! I'm here to help you with anything you need!"
    
#     print("=== CUTE VOICE DEMONSTRATION ===")
#     speak_with_all_voices(sample_text)
    
#     # Interactive mode
#     print("\n\n=== INTERACTIVE MODE ===")
#     print("Enter text for cute voice conversion (or 'exit' to quit):")
    
#     generator = CuteVoiceGenerator()
#     voices = {
#         "1": ("Standard", generator.cute_voice_standard),
#         "2": ("Tiny", generator.cute_voice_tiny),
#         "3": ("Bubbly", generator.cute_voice_bubbly),
#         "4": ("Sing-Song", generator.cute_voice_sing_song)
#     }
    
#     while True:
#         user_text = input("\nText to speak: ")
#         if user_text.lower() == 'exit':
#             break
            
#         print("Select voice type:")
#         for key, (name, _) in voices.items():
#             print(f"{key}: {name}")
            
#         voice_choice = input("Choice (1-4): ")
#         if voice_choice in voices:
#             voices[voice_choice][2](user_text)
#         else:
#             print("Invalid choice, using standard voice")
#             generator.cute_voice_standard(user_text)
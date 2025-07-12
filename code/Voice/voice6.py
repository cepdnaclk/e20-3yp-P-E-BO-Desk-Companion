from gtts import gTTS
import pygame
import io
import os

def text_to_japanese_girl_voice(text, lang='de', slow=False, pitch_high=True):
    """
    Convert text to speech with Japanese girl-like voice characteristics
    
    Args:
        text (str): Text to convert to speech
        lang (str): Language code (default 'ja' for Japanese)
        slow (bool): Whether to speak slowly
        pitch_high (bool): Whether to use higher pitch (girl-like)
    """
    try:
        # Create gTTS object with Japanese language
        tts = gTTS(text=text, lang=lang)
        
        # Save to memory file
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        
        # Initialize pygame mixer
        pygame.mixer.init()
        pygame.mixer.music.load(mp3_fp)
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        pygame.mixer.quit()

if __name__ == "__main__":
    # Example usage
    text ="Enter text to convert to Japanese girl voice: "
    text_to_japanese_girl_voice(text)
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

def listen(
        recognizer: sr.Recognizer,
        mic: sr.Microphone,
        *,
        timeout: float = 8,
        phrase_time_limit: float = 6,
        retries: int = 2,
        language: str = "en-US",
        calibrate_duration: float = 0.5,
) -> str | None:
    """
    Capture a single utterance and return the recognized text.

    Returns
    -------
    str | None
        The recognized text, or None if nothing was captured/recognized.
    """
    for attempt in range(retries + 1):
        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=calibrate_duration)
                print("\U0001F3A4 Listeningâ€¦ (attempt", attempt + 1, ")")
                audio = recognizer.listen(source,
                                          timeout=timeout,
                                          phrase_time_limit=phrase_time_limit)

            try:
                text = recognizer.recognize_google(audio, language=language)
                text = text.strip()
                if text:
                    print(f"\U0001F5E3ï¸  You said: {text}")
                    return text
            except sr.UnknownValueError:
                print("\U0001F914  Sorryâ€”couldnâ€™t understand that.")
            except sr.RequestError as e:
                print(f"\u26A0\uFE0F  Google speech service error ({e}). Falling back to offline engineâ€¦")
                try:
                    text = recognizer.recognize_sphinx(audio, language=language)
                    text = text.strip()
                    if text:
                        print(f"\U0001F5E3ï¸  (Offline) You said: {text}")
                        return text
                except Exception as sphinx_err:
                    print(f"\u274C  Offline engine failed: {sphinx_err}")

        except sr.WaitTimeoutError:
            print("\u231B Timed out waiting for speech.")
        except Exception as mic_err:
            print(f"\U0001F3A4 Mic/Audio error: {mic_err}")

        if attempt < retries:
            time.sleep(0.5)

    print("\U0001F615  No intelligible speech captured.")
    return None


import whisper
import sounddevice as sd
import numpy as np
import tempfile
import scipy.io.wavfile

# Load the Whisper model once
whisper_model = whisper.load_model("base")  # Try "tiny" or "small" if Pi is slow

def listen_whisper(duration=1, sample_rate=16000) -> str | None:
    """Capture audio and transcribe using Whisper."""
    print("ðŸŽ¤ Listening with Whisperâ€¦")

    try:
        # Record from mic
        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
        sd.wait()

        # Save to a temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
            scipy.io.wavfile.write(tmpfile.name, sample_rate, recording)
            audio_path = tmpfile.name

        # Transcribe using Whisper
        result = whisper_model.transcribe(audio_path)
        text = result.get("text", "").strip()

        if text:
            print(f"ðŸ—£ï¸  You said (Whisper): {text}")
            return text
        else:
            print("ðŸ¤” No intelligible speech detected.")
            return None

    except Exception as e:
        print(f"âŒ Whisper error: {e}")
        return None


def start_assistant_from_text(prompt_text):
    """Starts Gemini assistant with initial text prompt."""
    print(f"\U0001F4AC Initial Prompt: {prompt_text}")
    conversation_history.clear()
    conversation_history.append({"role": "user", "parts": [prompt_text]})

    response = model.generate_content(conversation_history, generation_config={"max_output_tokens": 60})
    reply = response.text
    print(f"Gemini: {reply}")
    asyncio.run(speak_text(reply))

    conversation_history.append({"role": "model", "parts": [reply]})

    while True:
        user_input = listen(recognizer, mic)
        #user_input = listen_whisper()
        if user_input is None:
            continue
        if user_input.lower() == "exit":
            print("\U0001F44B Exiting assistant.")
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


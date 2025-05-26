import assemblyai as aai
import sounddevice as sd
import scipy.io.wavfile
import tempfile
import os
import pygame
import time
import asyncio
import edge_tts
import platform
import json
import urllib.request

import subprocess

# OpenRouter API setup
OPENROUTER_API_KEY = "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"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# AssemblyAI API key
aai.settings.api_key = "90407b46f50245528731a47a26dd01e6"

# Audio settings
SAMPLE_RATE = 44100
DURATION = 5

# Initialize pygame
pygame.mixer.init()

# Conversation history
conversation_history = [{"role": "system", "content": "You are an empathetic voice assistant."}]

def amplify_audio(input_file, output_file, gain_db=10):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", input_file,
        "-filter:a", f"volume={gain_db}dB",
        output_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

async def speak_text(text):
    """Speak using Edge TTS."""
    voice = "en-GB-SoniaNeural"
    filename = "response.mp3"
    boosted_file = "boosted_response.mp3"  # ✅ Define this before use

    tts = edge_tts.Communicate(text, voice)
    await tts.save(filename)

    amplify_audio(filename, boosted_file, gain_db=20)  # Now this line works

    pygame.mixer.music.load(boosted_file)
    pygame.mixer.music.set_volume(1.0)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.25)

    pygame.mixer.music.stop()
    pygame.mixer.music.unload()

    os.remove(filename)
    os.remove(boosted_file)

def listen_assemblyai():
    print("🎤 Listening...")
    try:
        audio_data = sd.rec(int(SAMPLE_RATE * DURATION), samplerate=SAMPLE_RATE, channels=1, dtype='int16')
        sd.wait()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
            scipy.io.wavfile.write(tmpfile.name, SAMPLE_RATE, audio_data)
            audio_file_path = tmpfile.name
        config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.best)
        transcript = aai.Transcriber(config=config).transcribe(audio_file_path)
        try:
            os.remove(audio_file_path)
        except:
            pass
        if transcript.status == "error":
            print(f"❌ Transcription failed: {transcript.error}")
            return None
        text = transcript.text.strip()
        if text:
            print(f"🗣️ You said: {text}")
            return text
        print("🤔 No speech detected.")
        return None
    except Exception as e:
        print(f"❌ AssemblyAI error: {e}")
        return None

def call_openrouter_api(prompt, retries=2, delay=1):
    conversation_history.append({"role": "user", "content": prompt})
    payload = {
        "messages": conversation_history,
        "model": "anthropic/claude-3.5-sonnet",
        "stream": False,
        "temperature": 0.7,
        "max_tokens": 50
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Voice Assistant"
    }
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                OPENROUTER_API_URL,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                reply = result['choices'][0]['message']['content'].strip()
            conversation_history.append({"role": "assistant", "content": reply})
            return reply
        except urllib.error.HTTPError as e:
            print(f"❌ API error: {e}")
            if attempt < retries:
                print(f"Retrying in {delay}s...")
                time.sleep(delay)
        except Exception as e:
            print(f"❌ Error: {e}")
            if attempt < retries:
                print(f"Retrying in {delay}s...")
                time.sleep(delay)
    return "Sorry, API connection failed."

async def start_assistant_from_text(prompt_text):
    print(f"💬 Prompt: {prompt_text}")
    conversation_history.clear()
    conversation_history.append({"role": "system", "content": "You are an empathetic voice assistant."})
    conversation_history.append({"role": "user", "content": prompt_text})
    reply = call_openrouter_api(prompt_text)
    print(f"Assistant: {reply}")
    await speak_text(reply)
    while True:
        user_input = listen_assemblyai()
        if user_input is None:
            continue
        if user_input.lower() in ["exit", "quit"]:
            print("👋 Exiting.")
            await speak_text("Goodbye!")
            break
        reply = call_openrouter_api(user_input)
        print(f"Assistant: {reply}")
        await speak_text(reply)

async def main():
    await start_assistant_from_text("I am Nimal. I look tired. Ask why.")

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())

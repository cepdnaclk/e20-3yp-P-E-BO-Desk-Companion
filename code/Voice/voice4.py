import numpy as np
import scipy.io.wavfile as wavfile
import sounddevice as sd
from gtts import gTTS
import io

# Diode constants
VB = 0.2
VL = 0.4
H = 4
LOOKUP_SAMPLES = 1024
MOD_F = 50
SAMPLE_RATE = 16000  # Sample rate for TTS

def generate_voice(text):
    tts = gTTS(text=text, lang='en')
    voice_data = io.BytesIO()
    tts.write_to_fp(voice_data)
    voice_data.seek(0)
    return voice_data

def load_wav_from_bytes(wav_bytes):
    rate, data = wavfile.read(wav_bytes)
    data = data[:, 1] if data.ndim > 1 else data
    scaler = np.max(np.abs(data))
    data = data.astype(np.float32) / scaler
    return rate, data, scaler

def diode_lookup(n_samples):
    result = np.zeros((n_samples,))
    for i in range(n_samples):
        v = float(i - float(n_samples) / 2) / (n_samples / 2)
        v = abs(v)
        if v < VB:
            result[i] = 0
        elif VB < v <= VL:
            result[i] = H * ((v - VB)**2) / (2 * VL - 2 * VB)
        else:
            result[i] = H * v - H * VL + (H * (VL - VB)**2) / (2 * VL - 2 * VB)
    return result

def waveshaper(signal):
    result = np.zeros(signal.shape)
    for i in range(signal.shape[0]):
        v = signal[i]
        v = abs(v)
        if v < VB:
            result[i] = 0
        elif VB < v <= VL:
            result[i] = H * ((v - VB)**2) / (2 * VL - 2 * VB)
        else:
            result[i] = H * v - H * VL + (H * (VL - VB)**2) / (2 * VL - 2 * VB)
    return result

def robot_voice(data, rate):
    n_samples = data.shape[0]

    # Create a sine wave for modulation
    tone = np.sin(2 * np.pi * np.arange(n_samples) * MOD_F / rate) * 0.5

    # Junctions
    tone2 = tone.copy()
    data2 = data.copy()

    # Invert tone and sum paths
    tone = -tone + data2
    data = data + tone2

    # Process both paths with the diode waveshaper
    data = waveshaper(data) + waveshaper(-data)
    tone = waveshaper(tone) + waveshaper(-tone)

    # Final result after junction difference
    result = data - tone

    # Normalize result
    result /= np.max(np.abs(result))
    return result

def play_audio(data, rate):
    sd.play(data, rate)
    sd.wait()

if __name__ == "__main__":
    text = input("Enter the text for the cute robotic voice: ")

    # Generate voice using gTTS and load it from memory
    voice_data = generate_voice(text)
    rate, data, scaler = load_wav_from_bytes(voice_data)

    # Process the voice to give it a robotic effect
    robotic_sound = robot_voice(data, rate)

    # Play the robotic sound directly
    play_audio(robotic_sound * scaler, rate)

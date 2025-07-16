import sounddevice as sd
import scipy.io.wavfile
import subprocess
import noisereduce as nr
import numpy as np
import os

def record_audio_to_file(filename="original.wav", duration=5, sample_rate=44100):
    print(f"🎙️ Recording for {duration} seconds...")
    try:
        audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
        sd.wait()
        scipy.io.wavfile.write(filename, sample_rate, audio_data)
        print(f"✅ Audio saved to: {filename}")
        return filename
    except Exception as e:
        print(f"❌ Recording error: {e}")
        return None

def reduce_noise(input_file, output_file, sample_rate=44100):
    print(f"🔇 Reducing noise in {input_file}...")
    try:
        rate, data = scipy.io.wavfile.read(input_file)
        if data.ndim > 1:
            data = data[:, 0]  # Use only one channel if stereo

        reduced = nr.reduce_noise(y=data, sr=rate)
        reduced = np.int16(reduced)  # Convert back to 16-bit PCM
        scipy.io.wavfile.write(output_file, rate, reduced)
        print(f"✅ Noise-reduced audio saved to: {output_file}")
        return output_file
    except Exception as e:
        print(f"❌ Noise reduction error: {e}")
        return None

def amplify_audio(input_file, output_file, gain_db=30):
    print(f"🔊 Amplifying {input_file} by {gain_db}dB...")
    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-i", input_file,
            "-filter:a", f"volume={gain_db}dB",
            output_file
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ Amplified audio saved to: {output_file}")
    except Exception as e:
        print(f"❌ Amplification error: {e}")

def record_reduce_amplify():
    raw_file = "original.wav"
    clean_file = "denoised.wav"
    amplified_file = "amplified.wav"

    recorded = record_audio_to_file(raw_file, duration=5)
    if recorded:
        denoised = reduce_noise(raw_file, clean_file)
        if denoised:
            amplify_audio(denoised, amplified_file, gain_db=30)

if __name__ == "__main__":
    record_reduce_amplify()

from pydub import AudioSegment
import simpleaudio as sa

# Load audio file
sound = AudioSegment.from_file("input.wav")  # or input.mp3

# Amplify by +10 dB
amplified = sound + 10  # Increase volume by 10 decibels

# Export to new file
amplified.export("amplified_output.wav", format="wav")

# Play the amplified audio
wave_obj = sa.WaveObject.from_wave_file("amplified_output.wav")
play_obj = wave_obj.play()
play_obj.wait_done()

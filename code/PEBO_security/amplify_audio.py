from pydub import AudioSegment
import simpleaudio as sa

# Load audio file
sound = AudioSegment.from_file("input.wav")  # Replace with your filename

# Amplify by +10 dB
amplified = sound + 10

# Export amplified file
amplified.export("amplified_output.wav", format="wav")

# Play the amplified file
wave_obj = sa.WaveObject.from_wave_file("amplified_output.wav")
play_obj = wave_obj.play()
play_obj.wait_done()

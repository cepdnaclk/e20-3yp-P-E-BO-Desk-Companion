import pyaudio
import time

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2         # Use 2 for stereo, try 1 for mono if this fails
RATE = 44100         # Use 44100 for better compatibility (try 48000 if needed)
RECORD_SECONDS = 5

# Optional: set device index manually
USE_DEFAULT_OUTPUT = True      # Set False to use specific device
OUTPUT_DEVICE_INDEX = 7        # Only used if USE_DEFAULT_OUTPUT = False

audio = pyaudio.PyAudio()

# --- Optional: Print all devices ---
print("\nAvailable Audio Devices:")
for i in range(audio.get_device_count()):
    info = audio.get_device_info_by_index(i)
    print(f"  Index {i}: {info['name']} | Input: {info['maxInputChannels']} | Output: {info['maxOutputChannels']}")

# --- Get Default Output Info ---
default_output = audio.get_default_output_device_info()
print(f"\nDefault Output Device: {default_output['name']} (Index {default_output['index']})\n")

# --- Step 1: Record Audio from Mic ---
print("Recording from mic for", RECORD_SECONDS, "seconds...")
stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
frames = []
for _ in range(int(RATE / CHUNK * RECORD_SECONDS)):
    data = stream.read(CHUNK)
    frames.append(data)
stream.stop_stream()
stream.close()
print("Recording complete!")

# --- Step 2: Playback ---
print("Playing back through speaker...")
try:
    if USE_DEFAULT_OUTPUT:
        play_stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True
        )
    else:
        play_stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            output_device_index=OUTPUT_DEVICE_INDEX
        )

    for frame in frames:
        play_stream.write(frame)
    play_stream.stop_stream()
    play_stream.close()
    print("Playback complete!")

except Exception as e:
    print("Error during playback:", e)

audio.terminate()

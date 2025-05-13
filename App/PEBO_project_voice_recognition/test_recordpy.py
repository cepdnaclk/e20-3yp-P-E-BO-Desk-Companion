import pyaudio
import wave
import time

def record_simple(output_filename="recording.wav", duration=5):
    # Audio parameters
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    
    # Initialize PyAudio
    p = pyaudio.PyAudio()
    
    print(f"Recording {duration} seconds...")
    
    # Open audio stream (uses the default/pre-selected input device)
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    # Record data
    frames = []
    for i in range(0, int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)
    
    # Stop recording
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    print("Recording stopped")
    
    # Save the recorded audio to a WAV file
    wf = wave.open(output_filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_width(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    print(f"Recording saved to {output_filename}")

# Run the recording function
if __name__ == "__main__":
    record_simple("my_recording.wav", 5)
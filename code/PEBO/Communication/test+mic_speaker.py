import pyaudio

def list_audio_devices():
    audio = pyaudio.PyAudio()
    print("Available audio devices:")
    for i in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(i)
        print(f"{i}: {info['name']} - Inputs: {info['maxInputChannels']}, Outputs: {info['maxOutputChannels']}")
    audio.terminate()

list_audio_devices()

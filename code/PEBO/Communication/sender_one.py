import socket
import pyaudio

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1  # Mono recommended
RATE = 44100
PORT = 5001
PEER_IP = 'Laptop_IP_here'

audio = pyaudio.PyAudio()

def send_audio():
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((PEER_IP, PORT))
    print("Sending audio...")
    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            s.sendall(data)
    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()
        s.close()
        audio.terminate()

send_audio()

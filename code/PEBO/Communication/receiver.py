import socket
import pyaudio

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
PORT = 5001

audio = pyaudio.PyAudio()

def receive_audio():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', PORT))
    server.listen(1)
    print("Waiting for audio connection...")
    conn, addr = server.accept()
    print(f"Connected by {addr}")

    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)
    try:
        while True:
            data = conn.recv(CHUNK)
            if not data:
                break
            stream.write(data)
    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()
        conn.close()
        server.close()
        audio.terminate()

receive_audio()

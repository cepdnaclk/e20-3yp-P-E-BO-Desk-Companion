import socket
import threading
import pyaudio

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

AUDIO_PORT = 5001
SIGNAL_PORT = 6001
PEER_IP = 'Laptop_IP_here'

audio = pyaudio.PyAudio()
is_call_active = False

def send_audio():
    global is_call_active
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((PEER_IP, AUDIO_PORT))
    print("Pi: Sending audio...")
    try:
        while is_call_active:
            data = stream.read(CHUNK, exception_on_overflow=False)
            s.sendall(data)
    except Exception as e:
        print("Send audio error:", e)
    finally:
        stream.stop_stream()
        stream.close()
        s.close()

def receive_audio():
    global is_call_active
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', AUDIO_PORT))
    server.listen(1)
    print("Pi: Waiting for audio connection...")
    conn, addr = server.accept()
    print(f"Pi: Audio connection from {addr}")
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)
    try:
        while is_call_active:
            data = conn.recv(CHUNK)
            if not data:
                break
            stream.write(data)
    except Exception as e:
        print("Receive audio error:", e)
    finally:
        stream.stop_stream()
        stream.close()
        conn.close()
        server.close()

def signaling_server():
    global is_call_active
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', SIGNAL_PORT))
    server.listen(1)
    print("Pi: Waiting for call...")
    conn, addr = server.accept()
    print(f"Pi: Incoming call from {addr}")
    signal = conn.recv(1024).decode()
    if signal == "CALL":
        print("Pi: Call received, answering...")
        conn.send(b"ANSWER")
        is_call_active = True
    else:
        conn.send(b"REJECT")
    conn.close()
    server.close()

def make_call():
    global is_call_active
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((PEER_IP, SIGNAL_PORT))
    s.send(b"CALL")
    response = s.recv(1024).decode()
    s.close()
    if response == "ANSWER":
        print("Pi: Call answered")
        is_call_active = True
    else:
        print("Pi: Call rejected")

if __name__ == "__main__":
    threading.Thread(target=signaling_server, daemon=True).start()

    input("Press Enter to call Laptop...")
    make_call()

    if is_call_active:
        t_send = threading.Thread(target=send_audio)
        t_recv = threading.Thread(target=receive_audio)
        t_send.start()
        t_recv.start()

        input("Press Enter to end call...")
        is_call_active = False

        t_send.join()
        t_recv.join()

    audio.terminate()
    print("Pi: Call ended")

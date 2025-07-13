import socket
import threading
import speech_recognition as sr
import pyaudio

# Audio configuration
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

# IP address of the laptop/peer device
PEER_IP = '192.168.1.5'  # change to your laptop's IP
PORT = 5001

is_communicating = False
audio = pyaudio.PyAudio()

def listen_for_command():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Pi: Listening for voice command...")
        audio_input = r.listen(source)
    try:
        command = r.recognize_google(audio_input).lower()
        print("Heard:", command)
        return command
    except:
        return ""

def send_audio():
    global is_communicating
    s = socket.socket()
    s.connect((PEER_IP, PORT))
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    print("Pi: Sending audio...")
    while is_communicating:
        try:
            data = stream.read(CHUNK)
            s.sendall(data)
        except:
            break
    stream.stop_stream()
    stream.close()
    s.close()

def receive_audio():
    global is_communicating
    server = socket.socket()
    server.bind(('0.0.0.0', PORT))
    server.listen(1)
    conn, _ = server.accept()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)
    print("Pi: Receiving audio...")
    while is_communicating:
        try:
            data = conn.recv(CHUNK)
            if not data:
                break
            stream.write(data)
        except:
            break
    stream.stop_stream()
    stream.close()
    conn.close()
    server.close()

# Main loop
while True:
    command = listen_for_command()
    if "seng message" in command:
        is_communicating = True
        print("Pi: Communication started.")
        t_send = threading.Thread(target=send_audio)
        t_recv = threading.Thread(target=receive_audio)
        t_send.start()
        t_recv.start()

        # Wait for end command
        while True:
            end_command = listen_for_command()
            if "message end" in end_command:
                is_communicating = False
                print("Pi: Communication ended.")
                break

        t_send.join()
        t_recv.join()

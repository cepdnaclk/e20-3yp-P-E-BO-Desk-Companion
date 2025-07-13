import socket
import threading
import speech_recognition as sr
import pyaudio

# Audio config
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
PORT = 5001
PEER_IP = '192.168.124.94'  # Raspberry Pi IP (no spaces!)

is_communicating = False
audio = pyaudio.PyAudio()

def listen_for_command():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Laptop: Listening for voice command...")
        audio_input = r.listen(source)
    try:
        command = r.recognize_google(audio_input).lower()
        print("Heard:", command)
        return command
    except:
        return ""

def send_audio():
    global is_communicating
    try:
        s = socket.socket()
        s.connect((PEER_IP, PORT))
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        print("Laptop: Sending audio...")
        while is_communicating:
            data = stream.read(CHUNK)
            s.sendall(data)
        stream.stop_stream()
        stream.close()
        s.close()
    except Exception as e:
        print("Send error:", e)

def receive_audio():
    global is_communicating
    try:
        server = socket.socket()
        server.bind(('0.0.0.0', PORT))
        server.listen(1)
        conn, _ = server.accept()
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)
        print("Laptop: Receiving audio...")
        while is_communicating:
            data = conn.recv(CHUNK)
            if not data:
                break
            stream.write(data)
        stream.stop_stream()
        stream.close()
        conn.close()
        server.close()
    except Exception as e:
        print("Receive error:", e)

# Main loop
while True:
    command = listen_for_command()
    if "start communication" in command:
        is_communicating = True
        print("Laptop: Communication started.")
        t_send = threading.Thread(target=send_audio)
        t_recv = threading.Thread(target=receive_audio)
        t_send.start()
        t_recv.start()

        while True:
            end_command = listen_for_command()
            if "end communication" in end_command:
                is_communicating = False
                print("Laptop: Communication ended.")
                break

        t_send.join()
        t_recv.join()

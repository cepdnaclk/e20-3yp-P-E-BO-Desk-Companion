import socket
import threading
import speech_recognition as sr
import pyaudio
import time

# Audio configuration
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
PORT = 5001
SIGNAL_PORT = 6001

PEER_IP = '192.168.124.94'  # ← Your Pi IP
audio = pyaudio.PyAudio()
is_communicating = False

def listen_for_command():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print(" Laptop: Listening for voice command...")
        try:
            audio_input = r.listen(source, timeout=5)
            command = r.recognize_google(audio_input).lower()
            print(" Heard:", command)
            return command
        except:
            return ""

def ring_loop():
    for _ in range(5):
        print(" Laptop: Ringing... (waiting for 'answer')")
        time.sleep(1)

def handle_signaling():
    server = socket.socket()
    server.bind(('0.0.0.0', SIGNAL_PORT))
    server.listen(1)
    conn, _ = server.accept()
    signal = conn.recv(1024).decode()
    if signal == "CALL":
        ring_loop()
        while True:
            cmd = listen_for_command()
            if "answer" in cmd:
                conn.send(b"ANSWER")
                print(" Laptop: Answered the call.")
                return True
    conn.close()
    return False

def send_call_signal():
    try:
        s = socket.socket()
        s.connect((PEER_IP, SIGNAL_PORT))
        s.send(b"CALL")
        print(" Laptop: Calling Pi...")
        response = s.recv(1024).decode()
        if response == "ANSWER":
            print(" Laptop: Call answered by Pi.")
            return True
    except:
        print(" Laptop: Failed to connect to Pi for call.")
    return False

def send_audio():
    global is_communicating
    try:
        s = socket.socket()
        s.connect((PEER_IP, PORT))
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        print(" Laptop: Sending audio...")
        while is_communicating:
            s.sendall(stream.read(CHUNK))
        stream.stop_stream()
        stream.close()
        s.close()
    except Exception as e:
        print(" Laptop Send error:", e)

def receive_audio():
    global is_communicating
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

# === MAIN LOOP ===
while True:
    command = listen_for_command()

    if command == "":
        if handle_signaling():
            is_communicating = True
        else:
            continue

    elif "start communication" in command:
        is_communicating = send_call_signal()

    if is_communicating:
        t_send = threading.Thread(target=send_audio)
        t_recv = threading.Thread(target=receive_audio)
        t_send.start()
        t_recv.start()
        while True:
            end_cmd = listen_for_command()
            if "end communication" in end_cmd or "message end" in end_cmd:
                is_communicating = False
                print(" Laptop: Call ended.")
                break
        t_send.join()
        t_recv.join()

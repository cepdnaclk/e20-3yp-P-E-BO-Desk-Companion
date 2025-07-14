import socket
import threading
import speech_recognition as sr
import pyaudio
import time
import sys
import os
import ctypes

CHUNK = 2048
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
PORT = 5001
SIGNAL_PORT = 6001

PEER_IP = '192.168.124.94'

audio = pyaudio.PyAudio()
is_communicating = False
stop_threads = False

def get_best_audio_device(input_device=True):
    best_device = None
    for i in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(i)
        if input_device:
            if info['maxInputChannels'] > 0:
                if 'microphone' in info['name'].lower():
                    return i
                if best_device is None:
                    best_device = i
        else:
            if info['maxOutputChannels'] > 0:
                if 'speaker' in info['name'].lower() or 'headphone' in info['name'].lower():
                    return i
                if best_device is None:
                    best_device = i
    return best_device

def listen_for_command():
    r = sr.Recognizer()
    try:
        input_device = get_best_audio_device(input_device=True)
        with sr.Microphone(device_index=input_device) as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            r.energy_threshold = 300
            r.dynamic_energy_threshold = True
            audio_input = r.listen(source, timeout=5, phrase_time_limit=10)
           
            try:
                command = r.recognize_google(audio_input).lower()
                print("Heard:", command)
                return command
            except sr.RequestError:
                try:
                    command = r.recognize_sphinx(audio_input).lower()
                    print("Heard (offline):", command)
                    return command
                except:
                    return ""
    except:
        return ""

def ring_loop():
    for i in range(5):
        print(f"Ringing... {i+1}/5")
        time.sleep(1)

def handle_signaling():
    server = None
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
       
        for attempt in range(3):
            try:
                server.bind(('0.0.0.0', SIGNAL_PORT))
                break
            except OSError:
                if attempt < 2:
                    time.sleep(2)
                else:
                    return False
       
        server.listen(1)
        server.settimeout(1)
       
        try:
            conn, addr = server.accept()
            conn.settimeout(5)
            signal = conn.recv(1024).decode()
           
            if signal == "CALL":
                ring_loop()
                start_time = time.time()
                while time.time() - start_time < 30:
                    cmd = listen_for_command()
                    if "answer" in cmd:
                        conn.send(b"ANSWER")
                        return True
                    elif "reject" in cmd or "decline" in cmd:
                        conn.send(b"REJECT")
                        return False
               
                conn.send(b"TIMEOUT")
                return False
        except:
            return False
    except:
        return False
    finally:
        if server:
            server.close()

def send_call_signal():
    for attempt in range(3):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((PEER_IP, SIGNAL_PORT))
            s.send(b"CALL")
           
            response = s.recv(1024).decode()
            s.close()
           
            if response == "ANSWER":
                return True
            else:
                return False
        except:
            if attempt < 2:
                time.sleep(2)
    return False

def send_audio():
    global is_communicating, stop_threads
    stream = None
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((PEER_IP, PORT))
       
        input_device = get_best_audio_device(input_device=True)
        if input_device is None:
            return
            
        device_info = audio.get_device_info_by_index(input_device)
        
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            input_device_index=input_device
        )
       
        while is_communicating and not stop_threads:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                s.sendall(data)
            except:
                break
    except:
        pass
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        if s:
            s.close()

def receive_audio():
    global is_communicating, stop_threads
    server = None
    conn = None
    stream = None
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', PORT))
        server.listen(1)
        server.settimeout(5)
       
        conn, addr = server.accept()
        
        output_device = get_best_audio_device(input_device=False)
        if output_device is None:
            return
            
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            frames_per_buffer=CHUNK,
            output_device_index=output_device
        )
       
        while is_communicating and not stop_threads:
            try:
                data = conn.recv(CHUNK)
                if not data:
                    break
                stream.write(data)
            except:
                break
    except:
        pass
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        if conn:
            conn.close()
        if server:
            server.close()

print("Voice Communication System Started")
print("Commands: 'start communication', 'answer', 'end communication'")

while True:
    try:
        command = listen_for_command()
       
        if command == "":
            if not is_communicating:
                if handle_signaling():
                    is_communicating = True
                    stop_threads = False
            continue
       
        elif "start communication" in command:
            if not is_communicating:
                is_communicating = send_call_signal()
                stop_threads = False
       
        elif "quit" in command or "exit" in command:
            break
       
        if is_communicating:
            t_send = threading.Thread(target=send_audio)
            t_recv = threading.Thread(target=receive_audio)
            t_send.daemon = True
            t_recv.daemon = True
            t_send.start()
            t_recv.start()
           
            while is_communicating:
                end_cmd = listen_for_command()
                if "end communication" in end_cmd or "message end" in end_cmd:
                    is_communicating = False
                    stop_threads = True
                    break
           
            t_send.join(timeout=3)
            t_recv.join(timeout=3)
           
    except KeyboardInterrupt:
        is_communicating = False
        stop_threads = True
        break
    except:
        time.sleep(1)

audio.terminate()
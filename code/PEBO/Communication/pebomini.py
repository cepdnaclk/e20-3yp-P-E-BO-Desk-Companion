import socket
import threading
import speech_recognition as sr
import pyaudio
import time

# Audio configuration
CHUNK = 2048
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
PORT = 5001
SIGNAL_PORT = 6001

PEER_IP = '192.168.124.182'  # ← Your laptop IP
audio = pyaudio.PyAudio()
is_communicating = False
stop_threads = False

def listen_for_command():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print(" Pi: Listening for voice command...")
        try:
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio_input = r.listen(source, timeout=5)
            command = r.recognize_google(audio_input).lower()
            print(" Heard:", command)
            return command
        except sr.WaitTimeoutError:
            print(" Pi: No speech detected")
            return ""
        except sr.UnknownValueError:
            print(" Pi: Could not understand audio")
            return ""
        except Exception as e:
            print(f" Pi: Error in speech recognition: {e}")
            return ""

def ring_loop():
    for i in range(5):
        print(f" Pi: Ringing... {i+1}/5 (waiting for 'answer')")
        time.sleep(1)

def handle_signaling():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(('0.0.0.0', SIGNAL_PORT))
        server.listen(1)
        print(" Pi: Waiting for incoming call...")
        conn, addr = server.accept()
        print(f" Pi: Connection from {addr}")
        
        signal = conn.recv(1024).decode()
        if signal == "CALL":
            ring_loop()
            while True:
                cmd = listen_for_command()
                if "answer" in cmd:
                    conn.send(b"ANSWER")
                    print(" Pi: Answered the call.")
                    conn.close()
                    server.close()
                    return True
                elif "reject" in cmd or "decline" in cmd:
                    conn.send(b"REJECT")
                    print(" Pi: Rejected the call.")
                    conn.close()
                    server.close()
                    return False
        conn.close()
    except Exception as e:
        print(f" Pi: Signaling error: {e}")
    finally:
        server.close()
    return False

def send_call_signal():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((PEER_IP, SIGNAL_PORT))
        s.send(b"CALL")
        print(" Pi: Calling laptop...")
        s.settimeout(10)  # 10 second timeout
        response = s.recv(1024).decode()
        s.close()
        if response == "ANSWER":
            print(" Pi: Call answered by laptop.")
            return True
        else:
            print(" Pi: Call rejected by laptop.")
            return False
    except Exception as e:
        print(f" Pi: Failed to connect to laptop for call: {e}")
    return False

def send_audio():
    global is_communicating, stop_threads
    stream = None
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((PEER_IP, PORT))
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, 
                          input=True, frames_per_buffer=CHUNK)
        print(" Pi: Sending audio...")
        
        while is_communicating and not stop_threads:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                s.sendall(data)
            except Exception as e:
                print(f" Pi: Send audio error: {e}")
                break
                
    except Exception as e:
        print(f" Pi: Send audio connection error: {e}")
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
        print(" Pi: Waiting for audio connection...")
        
        conn, addr = server.accept()
        print(f" Pi: Audio connection from {addr}")
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, 
                          output=True, frames_per_buffer=CHUNK)
        print(" Pi: Receiving audio...")
        
        while is_communicating and not stop_threads:
            try:
                data = conn.recv(CHUNK)
                if not data:
                    break
                stream.write(data)
            except Exception as e:
                print(f" Pi: Receive audio error: {e}")
                break
                
    except Exception as e:
        print(f" Pi: Receive audio connection error: {e}")
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        if conn:
            conn.close()
        if server:
            server.close()

# === MAIN LOOP ===
print(" Pi: Voice Communication System Started")
print(" Commands: 'send message', 'answer', 'message end'")

while True:
    try:
        command = listen_for_command()
        
        if command == "":
            # Check for incoming calls
            if handle_signaling():
                is_communicating = True
                stop_threads = False
            else:
                continue
        
        elif "send message" in command:
            is_communicating = send_call_signal()
            stop_threads = False
        
        elif "quit" in command or "exit" in command:
            print(" Pi: Shutting down...")
            break
        
        if is_communicating:
            print(" Pi: Starting communication threads...")
            t_send = threading.Thread(target=send_audio)
            t_recv = threading.Thread(target=receive_audio)
            t_send.daemon = True
            t_recv.daemon = True
            t_send.start()
            t_recv.start()
            
            while is_communicating:
                end_cmd = listen_for_command()
                if "message end" in end_cmd or "end communication" in end_cmd:
                    is_communicating = False
                    stop_threads = True
                    print(" Pi: Call ended.")
                    break
            
            # Wait for threads to finish
            t_send.join(timeout=2)
            t_recv.join(timeout=2)
            
    except KeyboardInterrupt:
        print("\n Pi: Shutting down...")
        is_communicating = False
        stop_threads = True
        break
    except Exception as e:
        print(f" Pi: Unexpected error: {e}")

# Cleanup
audio.terminate()
print(" Pi: System shutdown complete.")
import socket
import threading
import speech_recognition as sr
import pyaudio
import time
import sys
import os

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
stop_threads = False

def check_audio_devices():
    """Check available audio devices"""
    print(" Laptop: Available audio devices:")
    for i in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(i)
        print(f"  {i}: {info['name']} - {info['maxInputChannels']} input, {info['maxOutputChannels']} output")

def listen_for_command():
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print(" Laptop: Listening for voice command...")
            r.adjust_for_ambient_noise(source, duration=0.5)
            r.energy_threshold = 300
            r.dynamic_energy_threshold = True
            audio_input = r.listen(source, timeout=5, phrase_time_limit=10)
            
            # Try Google first, then fall back to offline recognition
            try:
                command = r.recognize_google(audio_input).lower()
                print(" Heard:", command)
                return command
            except sr.RequestError:
                print(" Laptop: Google speech recognition unavailable, trying offline...")
                try:
                    command = r.recognize_sphinx(audio_input).lower()
                    print(" Heard (offline):", command)
                    return command
                except:
                    print(" Laptop: Offline recognition also failed")
                    return ""
                    
    except sr.WaitTimeoutError:
        return ""
    except sr.UnknownValueError:
        return ""
    except Exception as e:
        print(f" Laptop: Error in speech recognition: {e}")
        return ""

def ring_loop():
    for i in range(5):
        print(f" Laptop: Ringing... {i+1}/5 (waiting for 'answer')")
        time.sleep(1)

def handle_signaling():
    """Handle incoming call signaling with better error handling"""
    server = None
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Try multiple times to bind
        for attempt in range(3):
            try:
                server.bind(('0.0.0.0', SIGNAL_PORT))
                break
            except OSError as e:
                if attempt < 2:
                    print(f" Laptop: Port {SIGNAL_PORT} busy, waiting... (attempt {attempt+1})")
                    time.sleep(2)
                else:
                    print(f" Laptop: Cannot bind to port {SIGNAL_PORT}: {e}")
                    return False
        
        server.listen(1)
        server.settimeout(1)  # 1 second timeout for accept
        print(" Laptop: Waiting for incoming call...")
        
        try:
            conn, addr = server.accept()
            print(f" Laptop: Connection from {addr}")
            
            conn.settimeout(5)
            signal = conn.recv(1024).decode()
            
            if signal == "CALL":
                ring_loop()
                start_time = time.time()
                while time.time() - start_time < 30:  # 30 second timeout
                    cmd = listen_for_command()
                    if "answer" in cmd:
                        conn.send(b"ANSWER")
                        print(" Laptop: Answered the call.")
                        return True
                    elif "reject" in cmd or "decline" in cmd:
                        conn.send(b"REJECT")
                        print(" Laptop: Rejected the call.")
                        return False
                
                print(" Laptop: Call timed out")
                conn.send(b"TIMEOUT")
                return False
                
        except socket.timeout:
            return False
        except Exception as e:
            print(f" Laptop: Connection error: {e}")
            return False
            
    except Exception as e:
        print(f" Laptop: Signaling setup error: {e}")
        return False
    finally:
        if server:
            server.close()

def send_call_signal():
    """Send call signal with retry logic"""
    for attempt in range(3):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((PEER_IP, SIGNAL_PORT))
            s.send(b"CALL")
            print(f" Laptop: Calling Pi... (attempt {attempt+1})")
            
            response = s.recv(1024).decode()
            s.close()
            
            if response == "ANSWER":
                print(" Laptop: Call answered by Pi.")
                return True
            elif response == "REJECT":
                print(" Laptop: Call rejected by Pi.")
                return False
            else:
                print(f" Laptop: Unexpected response: {response}")
                return False
                
        except socket.timeout:
            print(f" Laptop: Connection timeout (attempt {attempt+1})")
        except Exception as e:
            print(f" Laptop: Connection error (attempt {attempt+1}): {e}")
        
        if attempt < 2:
            time.sleep(2)
    
    print(" Laptop: Failed to connect after 3 attempts")
    return False

def send_audio():
    global is_communicating, stop_threads
    stream = None
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((PEER_IP, PORT))
        
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            input_device_index=None  # Use default device
        )
        print(" Laptop: Sending audio...")
        
        while is_communicating and not stop_threads:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                s.sendall(data)
            except Exception as e:
                print(f" Laptop: Send audio error: {e}")
                break
                
    except Exception as e:
        print(f" Laptop: Send audio connection error: {e}")
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
        print(" Laptop: Waiting for audio connection...")
        
        conn, addr = server.accept()
        print(f" Laptop: Audio connection from {addr}")
        
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            frames_per_buffer=CHUNK,
            output_device_index=None  # Use default device
        )
        print(" Laptop: Receiving audio...")
        
        while is_communicating and not stop_threads:
            try:
                data = conn.recv(CHUNK)
                if not data:
                    break
                stream.write(data)
            except Exception as e:
                print(f" Laptop: Receive audio error: {e}")
                break
                
    except Exception as e:
        print(f" Laptop: Receive audio connection error: {e}")
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        if conn:
            conn.close()
        if server:
            server.close()

# Check if running as administrator on Windows
def is_admin():
    try:
        return os.getuid() == 0
    except AttributeError:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

# === MAIN LOOP ===
print(" Laptop: Voice Communication System Started")
print(" Commands: 'start communication', 'answer', 'end communication'")

if sys.platform == "win32" and not is_admin():
    print(" WARNING: Running as administrator might help with port binding issues")

check_audio_devices()

while True:
    try:
        command = listen_for_command()
        
        if command == "":
            # Only check for incoming calls if not already communicating
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
            print(" Laptop: Shutting down...")
            break
        
        if is_communicating:
            print(" Laptop: Starting communication threads...")
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
                    print(" Laptop: Call ended.")
                    break
            
            # Wait for threads to finish
            t_send.join(timeout=3)
            t_recv.join(timeout=3)
            
    except KeyboardInterrupt:
        print("\n Laptop: Shutting down...")
        is_communicating = False
        stop_threads = True
        break
    except Exception as e:
        print(f" Laptop: Unexpected error: {e}")
        time.sleep(1)

# Cleanup
audio.terminate()
print(" Laptop: System shutdown complete.")
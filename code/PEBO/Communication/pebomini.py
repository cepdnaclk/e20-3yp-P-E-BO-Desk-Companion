import socket
import threading
import speech_recognition as sr
import pyaudio
import time
import subprocess
import os

# Suppress ALSA warnings
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["ALSA_CARD"] = "default"

# Audio configuration
CHUNK = 2048
FORMAT = pyaudio.paInt16
CHANNELS = 1  # Changed to mono for better compatibility
RATE = 44100
PORT = 5001
SIGNAL_PORT = 6001

# CRITICAL: Make sure this is the correct IP address of your laptop
PEER_IP = '192.168.124.182'  # Your laptop IP - VERIFY THIS IS CORRECT

audio = pyaudio.PyAudio()
is_communicating = False
stop_threads = False

def check_audio_setup():
    """Check and fix audio setup on Pi"""
    print("Pi: Checking audio setup...")
   
    # Check if FLAC is installed
    try:
        result = subprocess.run(['flac', '--version'], capture_output=True, text=True)
        print("Pi: FLAC is installed")
    except FileNotFoundError:
        print("Pi: Installing FLAC...")
        os.system('sudo apt-get update && sudo apt-get install -y flac')
   
    # Check audio devices
    print("Pi: Available audio devices:")
    for i in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(i)
        print(f"  {i}: {info['name']} - {info['maxInputChannels']} input, {info['maxOutputChannels']} output")
   
    # Try to start pulseaudio if it's not running
    try:
        os.system('pulseaudio --start --verbose 2>/dev/null')
    except:
        pass

def get_best_audio_device(input_device=True):
    """Find the best audio device for input or output"""
    best_device = None
    for i in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(i)
        if input_device:
            if info['maxInputChannels'] > 0:
                # Prefer USB devices over built-in
                if 'usb' in info['name'].lower() or 'USB' in info['name']:
                    return i
                if best_device is None:
                    best_device = i
        else:
            if info['maxOutputChannels'] > 0:
                # Prefer headphones/speakers over default
                if 'headphone' in info['name'].lower() or 'speaker' in info['name'].lower():
                    return i
                if best_device is None:
                    best_device = i
    return best_device

def listen_for_command():
    r = sr.Recognizer()
    try:
        # Get the best input device
        input_device = get_best_audio_device(input_device=True)
        
        with sr.Microphone(device_index=input_device) as source:
            print("Pi: Listening for voice command...")
            r.adjust_for_ambient_noise(source, duration=0.5)
            r.energy_threshold = 300
            r.dynamic_energy_threshold = True
            r.pause_threshold = 0.8
           
            audio_input = r.listen(source, timeout=5, phrase_time_limit=10)
           
            # Try Google first, then fall back to offline recognition
            try:
                command = r.recognize_google(audio_input, language="en-US").lower()
                print("Heard:", command)
                return command
            except sr.RequestError:
                print("Pi: Google speech recognition unavailable, trying offline...")
                try:
                    command = r.recognize_sphinx(audio_input).lower()
                    print("Heard (offline):", command)
                    return command
                except:
                    print("Pi: Offline recognition also failed")
                    return ""
                   
    except sr.WaitTimeoutError:
        return ""
    except sr.UnknownValueError:
        return ""
    except Exception as e:
        print(f"Pi: Error in speech recognition: {e}")
        return ""

def ring_loop():
    for i in range(5):
        print(f"Pi: Ringing... {i+1}/5 (waiting for 'answer')")
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
                    print(f"Pi: Port {SIGNAL_PORT} busy, waiting... (attempt {attempt+1})")
                    time.sleep(2)
                else:
                    print(f"Pi: Cannot bind to port {SIGNAL_PORT}: {e}")
                    return False
       
        server.listen(1)
        server.settimeout(1)  # 1 second timeout for accept
        print("Pi: Waiting for incoming call...")
       
        try:
            conn, addr = server.accept()
            print(f"Pi: Connection from {addr}")
           
            conn.settimeout(5)
            signal = conn.recv(1024).decode()
           
            if signal == "CALL":
                ring_loop()
                start_time = time.time()
                while time.time() - start_time < 30:  # 30 second timeout
                    cmd = listen_for_command()
                    if "answer" in cmd:
                        conn.send(b"ANSWER")
                        print("Pi: Answered the call.")
                        return True
                    elif "reject" in cmd or "decline" in cmd:
                        conn.send(b"REJECT")
                        print("Pi: Rejected the call.")
                        return False
               
                print("Pi: Call timed out")
                conn.send(b"TIMEOUT")
                return False
               
        except socket.timeout:
            return False
        except Exception as e:
            print(f"Pi: Connection error: {e}")
            return False
           
    except Exception as e:
        print(f"Pi: Signaling setup error: {e}")
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
            
            print(f"Pi: Attempting to connect to {PEER_IP}:{SIGNAL_PORT}")
            s.connect((PEER_IP, SIGNAL_PORT))
            s.send(b"CALL")
            print(f"Pi: Calling laptop... (attempt {attempt+1})")
           
            response = s.recv(1024).decode()
            s.close()
           
            if response == "ANSWER":
                print("Pi: Call answered by laptop.")
                return True
            elif response == "REJECT":
                print("Pi: Call rejected by laptop.")
                return False
            else:
                print(f"Pi: Unexpected response: {response}")
                return False
               
        except socket.timeout:
            print(f"Pi: Connection timeout (attempt {attempt+1})")
        except socket.gaierror as e:
            print(f"Pi: DNS/IP resolution error (attempt {attempt+1}): {e}")
            print(f"Pi: Check that PEER_IP '{PEER_IP}' is correct")
        except ConnectionRefusedError:
            print(f"Pi: Connection refused (attempt {attempt+1}). Is laptop script running?")
        except Exception as e:
            print(f"Pi: Connection error (attempt {attempt+1}): {e}")
       
        if attempt < 2:
            time.sleep(2)
   
    print("Pi: Failed to connect after 3 attempts")
    return False

def send_audio():
    global is_communicating, stop_threads
    stream = None
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((PEER_IP, PORT))
       
        # Find a suitable input device
        input_device = get_best_audio_device(input_device=True)
        
        if input_device is None:
            print("Pi: No input device found!")
            return
            
        device_info = audio.get_device_info_by_index(input_device)
        print(f"Pi: Using input device: {device_info['name']}")
        
        stream = audio.open(
            format=FORMAT,
            channels=min(CHANNELS, device_info['maxInputChannels']),
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            input_device_index=input_device
        )
        print("Pi: Sending audio...")
       
        while is_communicating and not stop_threads:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                s.sendall(data)
            except Exception as e:
                print(f"Pi: Send audio error: {e}")
                break
               
    except Exception as e:
        print(f"Pi: Send audio connection error: {e}")
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
        print("Pi: Waiting for audio connection...")
       
        conn, addr = server.accept()
        print(f"Pi: Audio connection from {addr}")
       
        # Find a suitable output device
        output_device = get_best_audio_device(input_device=False)
        
        if output_device is None:
            print("Pi: No output device found!")
            return
            
        device_info = audio.get_device_info_by_index(output_device)
        print(f"Pi: Using output device: {device_info['name']}")
        
        stream = audio.open(
            format=FORMAT,
            channels=min(CHANNELS, device_info['maxOutputChannels']),
            rate=RATE,
            output=True,
            frames_per_buffer=CHUNK,
            output_device_index=output_device
        )
        print("Pi: Receiving audio...")
       
        while is_communicating and not stop_threads:
            try:
                data = conn.recv(CHUNK)
                if not data:
                    break
                stream.write(data)
            except Exception as e:
                print(f"Pi: Receive audio error: {e}")
                break
               
    except Exception as e:
        print(f"Pi: Receive audio connection error: {e}")
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        if conn:
            conn.close()
        if server:
            server.close()

def test_network_connectivity():
    """Test if we can reach the peer IP"""
    print(f"Pi: Testing connectivity to {PEER_IP}...")
    result = os.system(f"ping -c 1 {PEER_IP} > /dev/null 2>&1")
    if result == 0:
        print(f"Pi: Network connectivity to {PEER_IP} is working")
        return True
    else:
        print(f"Pi: Cannot reach {PEER_IP}. Check network connection and IP address.")
        return False

# === MAIN LOOP ===
print("Pi: Voice Communication System Started")
print("Commands: 'send message', 'answer', 'message end'")

# Check and setup audio
check_audio_setup()

# Test network connectivity
if not test_network_connectivity():
    print("Pi: Please check your network setup and PEER_IP configuration")
    print(f"Pi: Current PEER_IP is set to: {PEER_IP}")

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
       
        elif "send message" in command:
            if not is_communicating:
                is_communicating = send_call_signal()
                stop_threads = False
       
        elif "quit" in command or "exit" in command:
            print("Pi: Shutting down...")
            break
       
        if is_communicating:
            print("Pi: Starting communication threads...")
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
                    print("Pi: Call ended.")
                    break
           
            # Wait for threads to finish
            t_send.join(timeout=3)
            t_recv.join(timeout=3)
           
    except KeyboardInterrupt:
        print("\nPi: Shutting down...")
        is_communicating = False
        stop_threads = True
        break
    except Exception as e:
        print(f"Pi: Unexpected error: {e}")
        time.sleep(1)

# Cleanup
audio.terminate()
print("Pi: System shutdown complete.")
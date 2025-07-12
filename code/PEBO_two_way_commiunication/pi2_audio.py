import socket
import pyaudio
import threading
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def audio_call(target_ip, listen_port=8888, sample_rate=44100, chunk=1024):
    """
    Establishes a bidirectional audio call between two Raspberry Pis.
    
    Args:
        target_ip (str): IP address of the other Pi (e.g., '172.20.10.12').
        listen_port (int): Port to listen on (default: 8888).
        sample_rate (int): Audio sample rate (default: 44100 Hz).
        chunk (int): Audio chunk size (default: 1024).
    """
    # Audio settings
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = sample_rate
    CHUNK = chunk

    # Initialize PyAudio
    audio = pyaudio.PyAudio()

    # Setup streams
    mic_stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    speaker_stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        output=True,
        frames_per_buffer=CHUNK
    )

    running = [True]  # Use list to allow modification in threads

    def send_audio():
        """Send microphone audio to target Pi."""
        while running[0]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 32768)
                sock.connect((target_ip, listen_port))
                logging.info(f"Connected to {target_ip}:{listen_port} for sending")
                
                while running[0]:
                    try:
                        data = mic_stream.read(CHUNK, exception_on_overflow=False)
                        sock.sendall(data)
                    except Exception as e:
                        logging.error(f"Send error: {e}")
                        break
                sock.close()
            except Exception as e:
                logging.error(f"Connection error (send): {e}")
                time.sleep(1)  # Retry after delay
            finally:
                try:
                    sock.close()
                except:
                    pass

    def receive_audio():
        """Receive audio from target Pi and play it."""
        while running[0]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 32768)
                sock.bind(('0.0.0.0', listen_port))
                sock.listen(1)
                logging.info(f"Listening on port {listen_port}")
                
                conn, addr = sock.accept()
                logging.info(f"Received connection from {addr}")
                
                while running[0]:
                    try:
                        data = conn.recv(CHUNK * 2)  # *2 for int16
                        if not data:
                            break
                        speaker_stream.write(data)
                    except Exception as e:
                        logging.error(f"Receive error: {e}")
                        break
                conn.close()
                sock.close()
            except Exception as e:
                logging.error(f"Connection error (receive): {e}")
                time.sleep(1)  # Retry after delay
            finally:
                try:
                    conn.close()
                    sock.close()
                except:
                    pass

    # Start threads
    send_thread = threading.Thread(target=send_audio)
    receive_thread = threading.Thread(target=receive_audio)
    send_thread.daemon = True
    receive_thread.daemon = True
    send_thread.start()
    receive_thread.start()

    try:
        while running[0]:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping audio call...")
        running[0] = False

    # Cleanup
    mic_stream.stop_stream()
    speaker_stream.stop_stream()
    mic_stream.close()
    speaker_stream.close()
    audio.terminate()

if __name__ == "__main__":
    TARGET_IP = "172.20.10.12"  # Pi 1 IP
    audio_call(TARGET_IP)

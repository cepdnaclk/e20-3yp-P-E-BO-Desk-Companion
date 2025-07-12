import socket
import pyaudio
import wave
import os
import time
import subprocess
import netifaces as ni
import logging
import tempfile

# Configuration
SERVER_PORT = 12345
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 48000
CHUNK = 2048

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_ip_address():
    """Get the IP address of the device."""
    try:
        ip = ni.ifaddresses('wlan0')[ni.AF_INET][0]['addr']
        return ip
    except:
        try:
            ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
            return ip
        except:
            return "127.0.0.1"

def find_output_device():
    """Find a working output device index."""
    p = pyaudio.PyAudio()
    device_index = None
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        if dev_info['maxOutputChannels'] > 0:
            device_index = i
            logging.info(f"Using output device: {dev_info['name']}")
            break
    p.terminate()
    return device_index

def play_audio(file_path):
    """Play the audio file using PyAudio or aplay as fallback."""
    logging.info(f"Playing audio from {file_path}...")
    if not os.path.exists(file_path):
        logging.error(f"File {file_path} does not exist")
        return False

    # Redirect stderr to suppress ALSA errors
    orig_stderr = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 2)

    audio = pyaudio.PyAudio()
    device_index = find_output_device()

    try:
        wf = wave.open(file_path, 'rb')
        if device_index is not None:
            stream = audio.open(
                format=audio.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True,
                output_device_index=device_index
            )
        else:
            stream = audio.open(
                format=audio.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True
            )

        os.dup2(orig_stderr, 2)
        os.close(devnull)
        os.close(orig_stderr)

        data = wf.readframes(CHUNK)
        while data:
            stream.write(data)
            data = wf.readframes(CHUNK)

        stream.stop_stream()
        stream.close()
        audio.terminate()
        logging.info("Playback finished")
        return True

    except Exception as e:
        os.dup2(orig_stderr, 2)
        os.close(devnull)
        os.close(orig_stderr)
        logging.error(f"Error playing audio with PyAudio: {str(e)}")
        try:
            audio.terminate()
        except:
            pass

        try:
            logging.info("Trying alternative playback with aplay...")
            subprocess.call(['aplay', file_path])
            logging.info("Playback finished with aplay")
            return True
        except Exception as e2:
            logging.error(f"Error with aplay playback: {str(e2)}")
            return False

def setup_audio_config():
    """Set up ALSA configuration for audio playback."""
    try:
        home_dir = os.path.expanduser("~")
        asoundrc_path = os.path.join(home_dir, ".asoundrc")
        with open(asoundrc_path, 'w') as f:
            f.write("""
pcm.!default {
    type plug
    slave.pcm "softvol"
}

pcm.softvol {
    type softvol
    slave {
        pcm "hw:0,0"
    }
    control {
        name "Master"
        card 0
    }
    min_dB -5.0
    max_dB 20.0
    resolution 6
}

ctl.!default {
    type hw
    card 0
}
""")
        logging.info("Created ALSA configuration file at ~/.asoundrc")
        try:
            subprocess.call(['amixer', 'set', 'Master', '100%'])
            logging.info("Set playback volume to maximum")
        except:
            pass
    except Exception as e:
        logging.error(f"Could not create ALSA configuration: {str(e)}")

def receive_audio():
    """Receive and play audio files from the sender."""
    setup_audio_config()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_ip = get_ip_address()
    
    try:
        server_socket.bind((server_ip, SERVER_PORT))
        server_socket.listen(1)
        logging.info(f"Listening for audio messages on {server_ip}:{SERVER_PORT}")
        
        while True:
            try:
                client_socket, addr = server_socket.accept()
                logging.info(f"Connection from {addr}")
                
                # Receive hostname
                hostname = ""
                while True:
                    char = client_socket.recv(1).decode()
                    if char == '\n':
                        break
                    hostname += char
                logging.info(f"Received from hostname: {hostname}")
                
                # Receive file size
                file_size_str = ""
                while True:
                    char = client_socket.recv(1).decode()
                    if char == '\n':
                        break
                    file_size_str += char
                file_size = int(file_size_str)
                logging.info(f"Expecting file of size: {file_size} bytes")
                
                # Receive audio data
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
                    audio_file = tmpfile.name
                    received_size = 0
                    while received_size < file_size:
                        data = client_socket.recv(min(CHUNK, file_size - received_size))
                        if not data:
                            break
                        tmpfile.write(data)
                        received_size += len(data)
                
                client_socket.close()
                logging.info(f"Received audio file: {audio_file}")
                
                # Play the received audio
                if received_size == file_size:
                    if play_audio(audio_file):
                        logging.info("Audio played successfully")
                    else:
                        logging.error("Failed to play audio")
                else:
                    logging.error(f"Incomplete file received: {received_size}/{file_size} bytes")
                
                # Clean up temporary file
                try:
                    os.remove(audio_file)
                    logging.info(f"Deleted temporary file: {audio_file}")
                except Exception as e:
                    logging.error(f"Error deleting temporary file: {str(e)}")
                
            except Exception as e:
                logging.error(f"Error receiving audio: {str(e)}")
                client_socket.close()
                time.sleep(1)  # Brief pause before accepting next connection
                
    except Exception as e:
        logging.error(f"Server error: {str(e)}")
    finally:
        server_socket.close()
        logging.info("Server socket closed")

if __name__ == "__main__":
    try:
        receive_audio()
    except KeyboardInterrupt:
        logging.info("Program interrupted by user")
    finally:
        logging.info("Program terminated")

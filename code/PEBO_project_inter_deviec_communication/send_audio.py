import socket
import pyaudio
import wave
import os
import time
import subprocess
import netifaces as ni
import sounddevice as sd
import scipy.io.wavfile
import noisereduce as nr
import numpy as np
import logging

# Configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 48000
CHUNK = 2048
RECORD_SECONDS = 5
SERVER_PORT = 12345
HOSTNAME = subprocess.check_output(['hostname']).strip().decode('utf-8')

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

def list_audio_devices():
    """List all available audio devices."""
    p = pyaudio.PyAudio()
    info = "\nAvailable Audio Devices:\n"
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        info += f"Device {i}: {dev_info['name']}\n"
        info += f"  Input Channels: {dev_info['maxInputChannels']}\n"
        info += f"  Output Channels: {dev_info['maxOutputChannels']}\n"
        info += f"  Default Sample Rate: {dev_info['defaultSampleRate']}\n"
    p.terminate()
    return info

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

def record_audio_to_file(filename="original.wav", duration=5, sample_rate=48000):
    """Record audio using sounddevice."""
    logging.info(f"Recording for {duration} seconds...")
    try:
        audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
        sd.wait()
        scipy.io.wavfile.write(filename, sample_rate, audio_data)
        logging.info(f"Audio saved to: {filename}")
        return filename
    except Exception as e:
        logging.error(f"Recording error: {e}")
        return None

def reduce_noise(input_file, output_file, sample_rate=48000):
    """Reduce noise in the audio file."""
    logging.info(f"Reducing noise in {input_file}...")
    try:
        rate, data = scipy.io.wavfile.read(input_file)
        if data.ndim > 1:
            data = data[:, 0]
        reduced = nr.reduce_noise(y=data, sr=rate)
        reduced = np.int16(reduced)
        scipy.io.wavfile.write(output_file, rate, reduced)
        logging.info(f"Noise-reduced audio saved to: {output_file}")
        return output_file
    except Exception as e:
        logging.error(f"Noise reduction error: {e}")
        return None

def amplify_audio(input_file, output_file, gain_db=30):
    """Amplify audio using ffmpeg."""
    logging.info(f"Amplifying {input_file} by {gain_db}dB...")
    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-i", input_file,
            "-filter:a", f"volume={gain_db}dB",
            output_file
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logging.info(f"Amplified audio saved to: {output_file}")
        return output_file
    except Exception as e:
        logging.error(f"Amplification error: {e}")
        return None

def record_audio(output_file="amplified.wav"):
    """Record, denoise, and amplify audio."""
    raw_file = "original.wav"
    clean_file = "denoised.wav"

    recorded = record_audio_to_file(raw_file, duration=RECORD_SECONDS, sample_rate=RATE)
    if recorded:
        denoised = reduce_noise(raw_file, clean_file)
        if denoised:
            amplified = amplify_audio(denoised, output_file, gain_db=30)
            if amplified:
                # Clean up intermediate files
                try:
                    os.remove(raw_file)
                    os.remove(clean_file)
                    logging.info(f"Deleted temporary files: {raw_file}, {clean_file}")
                except Exception as e:
                    logging.error(f"Error deleting temporary files: {e}")
                return output_file
        # Clean up raw file if denoising fails
        try:
            os.remove(raw_file)
            logging.info(f"Deleted temporary file: {raw_file}")
        except:
            pass
    return None

def play_audio(file_path):
    """Play the recorded audio file."""
    logging.info(f"Playing back recording from {file_path}...")
    if not os.path.exists(file_path):
        logging.error(f"File {file_path} does not exist")
        return False

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
        logging.error(f"Error playing audio: {e}")
        try:
            audio.terminate()
        except:
            pass
        try:
            logging.info("Trying alternative playback with aplay...")
            subprocess.call(['aplay', file_path])
            logging.info("Playback finished")
            return True
        except Exception as e2:
            logging.error(f"Error with aplay playback: {e2}")
            return False

def send_file(file_path, receiver_ip):
    """Send audio file to the receiver."""
    if not os.path.exists(file_path):
        logging.error(f"File {file_path} does not exist")
        return False

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((receiver_ip, SERVER_PORT))
        s.send(f"{HOSTNAME}\n".encode())
        file_size = os.path.getsize(file_path)
        s.send(f"{file_size}\n".encode())
        with open(file_path, 'rb') as f:
            data = f.read()
            s.sendall(data)
        s.close()
        logging.info(f"File {file_path} sent successfully to {receiver_ip}")
        return True
    except Exception as e:
        logging.error(f"Error sending file: {e}")
        return False

def setup_audio_config():
    """Set up ALSA configuration."""
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
            subprocess.call(['amixer', 'set', 'Capture', '100%'])
            logging.info("Set capture volume to maximum")
        except:
            pass
    except Exception as e:
        logging.error(f"Could not create ALSA configuration: {e}")

def main():
    setup_audio_config()
    logging.info(list_audio_devices())
    receiver_ip = input("Enter the IP address of the receiver computer: ")

    while True:
        audio_file = "amplified.wav"
        if record_audio(audio_file):
            play_success = play_audio(audio_file)
            if play_success:
                send_file(audio_file, receiver_ip)
            else:
                send_file(audio_file, receiver_ip)

        choice = input("\nPress Enter to record again, or 'q' to quit: ")
        if choice.lower() == 'q':
            try:
                os.remove(audio_file)
                logging.info(f"Deleted file: {audio_file}")
            except:
                pass
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Program interrupted by user")
    finally:
        logging.info("Program terminated")

import socket
import pyaudio
import wave
import os
import time
import subprocess
import netifaces as ni
import array
import math

# Configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 48000
CHUNK = 2048
RECORD_SECONDS = 5  # Adjust as needed
SERVER_PORT = 12345
HOSTNAME = subprocess.check_output(['hostname']).strip().decode('utf-8')
VOLUME_MULTIPLIER = 5.0  # Adjust this value to increase/decrease volume

def get_ip_address():
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
    """List all available audio devices to help with troubleshooting"""
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

def find_input_device():
    """Find a working input device index"""
    p = pyaudio.PyAudio()
    device_index = None
    
    # Try to find a device with input channels
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        if dev_info['maxInputChannels'] > 0:
            device_index = i
            print(f"Using input device: {dev_info['name']}")
            break
    
    p.terminate()
    return device_index

def find_output_device():
    """Find a working output device index"""
    p = pyaudio.PyAudio()
    device_index = None
    
    # Try to find a device with output channels
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        if dev_info['maxOutputChannels'] > 0:
            device_index = i
            print(f"Using output device: {dev_info['name']}")
            break
    
    p.terminate()
    return device_index

def amplify_audio(audio_data, format, volume=VOLUME_MULTIPLIER):
    """Increase the volume of the audio data"""
    # Convert byte data to array based on format
    if format == pyaudio.paInt16:
        # Convert bytes to array of signed shorts
        a = array.array('h')
        a.frombytes(audio_data)
        
        # Apply volume multiplier with clipping protection
        for i in range(len(a)):
            # Apply volume multiplier
            val = int(a[i] * volume)
            
            # Clip to avoid distortion
            if val > 32767:
                val = 32767
            elif val < -32768:
                val = -32768
                
            a[i] = val
            
        return a.tobytes()
    else:
        # For other formats, just return the original data
        print("Warning: Volume amplification only supports 16-bit audio")
        return audio_data

def normalize_audio(all_audio_data, format, target_volume=0.8):
    """Normalize audio to a target volume level"""
    if format != pyaudio.paInt16:
        print("Warning: Normalization only supports 16-bit audio")
        return all_audio_data
        
    # Convert bytes to array of signed shorts
    a = array.array('h')
    a.frombytes(b''.join(all_audio_data))
    
    # Find the maximum absolute sample value
    max_sample = max(abs(sample) for sample in a)
    
    # If the audio is silent, just return it
    if max_sample == 0:
        return all_audio_data
    
    # Calculate the scaling factor to reach target volume
    # Max value for 16-bit audio is 32767
    scale_factor = (32767 * target_volume) / max_sample
    
    # Apply the scaling factor to each sample
    for i in range(len(a)):
        a[i] = int(a[i] * scale_factor)
    
    # Convert back to bytes
    normalized_data = a.tobytes()
    
    # Split back into chunks of the same size as the original
    chunk_size = len(all_audio_data[0])
    normalized_chunks = [normalized_data[i:i+chunk_size] for i in range(0, len(normalized_data), chunk_size)]
    
    # If there's any remainder, add it as the last chunk
    if len(normalized_data) % chunk_size != 0:
        normalized_chunks.append(normalized_data[-(len(normalized_data) % chunk_size):])
    
    return normalized_chunks

def record_audio(output_file):
    """Record audio from microphone with improved error handling and volume enhancement"""
    print(f"Recording audio for {RECORD_SECONDS} seconds...")
    
    # Redirect stderr to suppress ALSA errors
    orig_stderr = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 2)
    
    # Initialize PyAudio
    audio = pyaudio.PyAudio()
    
    # Find an input device that works
    device_index = find_input_device()
    
    try:
        # Open stream with explicit device index if found
        if device_index is not None:
            stream = audio.open(format=FORMAT, 
                               channels=CHANNELS,
                               rate=RATE, 
                               input=True,
                               input_device_index=device_index,
                               frames_per_buffer=CHUNK)
        else:
            stream = audio.open(format=FORMAT, 
                               channels=CHANNELS,
                               rate=RATE, 
                               input=True,
                               frames_per_buffer=CHUNK)
        
        # Restore stderr
        os.dup2(orig_stderr, 2)
        os.close(devnull)
        os.close(orig_stderr)
        
        frames = []
        
        # Record audio
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            # Option 1: Amplify each chunk as we record
            # amplified_data = amplify_audio(data, FORMAT)
            # frames.append(amplified_data)
            
            # Or just collect raw data to normalize later
            frames.append(data)
        
        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        
        # Option 2: Normalize the entire audio recording
        # This provides more consistent volume than simple amplification
        frames = normalize_audio(frames, FORMAT, 0.9)
        
    except Exception as e:
        # Restore stderr in case of error
        os.dup2(orig_stderr, 2)
        os.close(devnull)
        os.close(orig_stderr)
        print(f"Error recording audio: {str(e)}")
        audio.terminate()
        return None
        
    # Save the recorded audio to a WAV file
    try:
        wf = wave.open(output_file, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        print(f"Recording saved to {output_file}")
        
    except Exception as e:
        print(f"Error saving audio file: {str(e)}")
        audio.terminate()
        return None
        
    audio.terminate()
    return output_file

def play_audio(file_path):
    """Play the recorded audio file"""
    print(f"Playing back recording from {file_path}...")
    
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist")
        return False
    
    # Redirect stderr to suppress ALSA errors
    orig_stderr = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 2)
    
    # Initialize PyAudio
    audio = pyaudio.PyAudio()
    
    # Find an output device that works
    device_index = find_output_device()
    
    try:
        # Open the WAV file
        wf = wave.open(file_path, 'rb')
        
        # Open stream with explicit device index if found
        if device_index is not None:
            stream = audio.open(format=audio.get_format_from_width(wf.getsampwidth()),
                                channels=wf.getnchannels(),
                                rate=wf.getframerate(),
                                output=True,
                                output_device_index=device_index)
        else:
            stream = audio.open(format=audio.get_format_from_width(wf.getsampwidth()),
                                channels=wf.getnchannels(),
                                rate=wf.getframerate(),
                                output=True)
        
        # Restore stderr
        os.dup2(orig_stderr, 2)
        os.close(devnull)
        os.close(orig_stderr)
        
        # Read data from WAV file and play
        data = wf.readframes(CHUNK)
        
        while data:
            stream.write(data)
            data = wf.readframes(CHUNK)
            
        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        
        # Close PyAudio
        audio.terminate()
        
        print("Playback finished")
        return True
        
    except Exception as e:
        # Restore stderr in case of error
        os.dup2(orig_stderr, 2)
        os.close(devnull)
        os.close(orig_stderr)
        print(f"Error playing audio: {str(e)}")
        
        try:
            audio.terminate()
        except:
            pass
            
        # If PyAudio playback fails, try using aplay as a fallback
        try:
            print("Trying alternative playback method using aplay...")
            subprocess.call(['aplay', file_path])
            print("Playback finished")
            return True
        except Exception as e2:
            print(f"Error with alternative playback: {str(e2)}")
            return False

def send_file(file_path, receiver_ip):
    """Send audio file to the receiver"""
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist")
        return False
    
    try:
        # Create socket connection
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((receiver_ip, SERVER_PORT))
        
        # Send hostname first
        s.send(f"{HOSTNAME}\n".encode())
        
        # Send file size
        file_size = os.path.getsize(file_path)
        s.send(f"{file_size}\n".encode())
        
        # Send the file
        with open(file_path, 'rb') as f:
            data = f.read()
            s.sendall(data)
            
        s.close()
        print(f"File {file_path} sent successfully to {receiver_ip}")
        return True
        
    except Exception as e:
        print(f"Error sending file: {str(e)}")
        return False

def setup_audio_config():
    """Try to setup proper ALSA configuration with higher gain"""
    try:
        # Create a simple .asoundrc file in the user's home directory
        home_dir = os.path.expanduser("~")
        asoundrc_path = os.path.join(home_dir, ".asoundrc")
        
        with open(asoundrc_path, 'w') as f:
            f.write("""
# Enhanced .asoundrc configuration with higher gain
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
    max_dB 20.0    # Higher value for more gain
    resolution 6
}

ctl.!default {
    type hw
    card 0
}
""")
        print("Created enhanced ALSA configuration file at ~/.asoundrc")
        
        # Try to set the maximum capture volume
        try:
            subprocess.call(['amixer', 'set', 'Capture', '100%'])
            print("Set capture volume to maximum")
        except:
            pass
            
    except Exception as e:
        print(f"Could not create ALSA configuration: {str(e)}")

def main():
    # Try to setup ALSA configuration with higher gain
    setup_audio_config()
    
    # Display available audio devices
    print(list_audio_devices())
    
    # Get receiver's IP address from user
    receiver_ip = input("Enter the IP address of the Windows computer: ")
    
    while True:
        # Record audio
        audio_file = "recorded_audio.wav"
        if record_audio(audio_file):
            # Play the recording back for verification
            print("\nPlaying back your recording for verification...")
            play_success = play_audio(audio_file)
            '''
            if play_success:
                # Ask user if they want to send this recording
                choice = input("\nDo you want to send this recording? (y/n): ")
                if choice.lower() == 'y':
                    # Send the file if user approves
                    send_file(audio_file, receiver_ip)
            else:
                print("Playback failed. You might not be able to hear the audio.")
                # Still ask if they want to send
                choice = input("\nDo you still want to send this recording? (y/n): ")
                if choice.lower() == 'y':
                    send_file(audio_file, receiver_ip)
            '''
            if play_success:
                send_file(audio_file, receiver_ip)
            else:
                send_file(audio_file, receiver_ip)
        
        # Prompt user to continue or exit
        choice = input("\nPress Enter to record again, or 'q' to quit: ")
        if choice.lower() == 'q':
            break

if __name__ == "__main__":
    main()
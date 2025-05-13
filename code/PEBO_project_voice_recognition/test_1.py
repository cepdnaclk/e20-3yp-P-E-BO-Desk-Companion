import subprocess
import os
import time
import signal
import sys
import json

# Handle Ctrl+C
def signal_handler(sig, frame):
    print('\nExiting voice recognition program...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def list_audio_devices():
    """List available audio devices using arecord"""
    print("Available audio devices:")
    subprocess.run(["arecord", "-l"])

def record_audio(duration=5, filename="audio.wav", device="default"):
    """Record audio using arecord command"""
    print(f"Recording for {duration} seconds...")
    try:
        subprocess.run(["arecord", "-D", device, "-f", "S16_LE", "-c1", "-r", "16000", "-d", str(duration), filename], 
                      check=True)
        print("Recording complete.")
        return filename
    except subprocess.CalledProcessError as e:
        print(f"Error recording audio: {e}")
        print("Try using a different device.")
        return None

def transcribe_with_external_service(audio_file):
    """
    This function sends the audio file to an external service for transcription.
    In a real implementation, you'd use a speech recognition API.
    
    For this example, we'll simulate this by printing instructions.
    """
    print("\nTo transcribe this audio, you have a few options:")
    print("1. Install vosk in your virtual environment for offline recognition:")
    print("   pip install vosk")
    print("2. Use Google's Speech Recognition API through a virtual environment:")
    print("   pip install SpeechRecognition")
    print("3. Use Mozilla DeepSpeech which can be installed through apt:")
    print("   sudo apt install deepspeech")
    
    # For demo purposes, just return placeholder text
    sample_text = input("For testing purposes, please type what you said (this simulates transcription): ")
    return sample_text

def main():
    print("Voice-to-Text Conversion using Bluetooth Microphone")
    print("=================================================")
    
    # List available devices
    list_audio_devices()
    
    # Let user select device
    print("\nBased on the list above, specify your Bluetooth microphone device.")
    print("For example, 'plughw:1,0' or 'default' if you're not sure.")
    device = input("Enter device (default is 'default'): ") or "default"
    
    # Create a log file
    log_file = "speech_log.txt"
    
    while True:
        try:
            duration = int(input("\nEnter recording duration in seconds (default: 5): ") or "5")
            audio_file = record_audio(duration, device=device)
            
            if audio_file:
                print("Audio recorded successfully to", audio_file)
                
                # Ask if user wants to transcribe
                if input("\nTranscribe this recording? (y/n): ").lower() == 'y':
                    text = transcribe_with_external_service(audio_file)
                    print(f"Transcription: {text}")
                    
                    # Save to log file
                    with open(log_file, "a") as f:
                        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: {text}\n")
            
            # Ask to continue
            if input("\nContinue recording? (y/n): ").lower() != 'y':
                break
                
        except Exception as e:
            print(f"Error: {e}")
            if input("\nTry again? (y/n): ").lower() != 'y':
                break

if __name__ == "__main__":
    main()
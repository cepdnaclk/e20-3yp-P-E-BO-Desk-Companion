import subprocess
import tempfile
import os
import json
import time

def record_audio(duration=5, device="default"):
    """Record audio using the arecord command"""
    print(f"Recording for {duration} seconds...")
    
    # Create a temporary file for the audio
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
        temp_filename = temp_audio.name
    
    try:
        # Record audio using arecord
        subprocess.run([
            "arecord", 
            "-D", device,     # Audio device
            "-f", "S16_LE",   # Format
            "-c", "1",        # Mono
            "-r", "16000",    # Sample rate
            "-d", str(duration),  # Duration in seconds
            temp_filename     # Output file
        ], check=True)
        
        print("Recording complete.")
        return temp_filename
        
    except subprocess.CalledProcessError as e:
        print(f"Error recording audio: {e}")
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        return None

def transcribe_with_google(audio_file, api_key):
    """Transcribe audio file using Google Speech-to-Text API"""
    try:
        print("Transcribing audio...")
        
        # Use curl to send to Google Speech API
        curl_command = [
            "curl", "-s",
            "-X", "POST", 
            "-H", "Content-Type: audio/l16; rate=16000;", 
            "--data-binary", f"@{audio_file}",
            f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}"
        ]
        
        result = subprocess.run(curl_command, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return None
        
        response = json.loads(result.stdout)
        
        if "results" in response and len(response["results"]) > 0:
            text = response["results"][0]["alternatives"][0]["transcript"]
            return text
        else:
            print("No speech recognized.")
            return None
            
    except Exception as e:
        print(f"Error during transcription: {e}")
        return None
    finally:
        # Clean up the temporary file
        if os.path.exists(audio_file):
            os.remove(audio_file)

def main():
    # Replace with your Google API key
    API_KEY = "YOUR_GOOGLE_API_KEY"
    
    print("Simple Speech-to-Text Converter")
    print("===============================")
    
    # List audio devices to help user select the right one
    print("\nAvailable audio devices:")
    subprocess.run(["arecord", "-l"])
    
    # Get device from user
    device = input("\nEnter audio device (default is 'default'): ") or "default"
    
    while True:
        # Get recording duration
        try:
            duration = int(input("\nEnter recording duration in seconds (default 5): ") or "5")
        except ValueError:
            duration = 5
        
        # Record audio
        audio_file = record_audio(duration, device)
        
        if audio_file:
            # Transcribe audio
            text = transcribe_with_google(audio_file, API_KEY)
            
            if text:
                print(f"\nTranscription: {text}")
                
                # Save to transcript file
                with open("transcripts.txt", "a") as file:
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    file.write(f"[{timestamp}] {text}\n")
        
        # Ask if user wants to continue
        if input("\nContinue? (y/n): ").lower() != 'y':
            break

if __name__ == "__main__":
    main()
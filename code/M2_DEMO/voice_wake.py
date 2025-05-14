import google.generativeai as genai
import pygame
import time
import os
import asyncio
import edge_tts
import speech_recognition as sr
import threading
import subprocess
import json
import queue
import signal
import cv2
import mediapipe as mp
import RPi.GPIO as GPIO
from picamera2 import Picamera2
import boto3
import socket
import pyaudio
import wave
import netifaces as ni
import array

# Initialize pygame for audio playback
pygame.mixer.init()

# Set up Google Gemini API key
GOOGLE_API_KEY = "AIzaSyDjx04eYTq-09j7kzd24NeZfwYZ7eu3w9Q"
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
conversation_history = []

# Initialize speech recognizer
recognizer = sr.Recognizer()
mic = sr.Microphone()

# Queues for inter-thread communication
trigger_queue = queue.Queue()
command_queue = queue.Queue()

# Global flags
face_tracking_active = False
face_detected = False
stop_event = threading.Event()

# Face tracking variables (from face_tracking.py)
GPIO.setwarnings(False)
h_servo_pin = 23  # pin 16
v_servo_pin = 24  # pin 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(h_servo_pin, GPIO.OUT)
GPIO.setup(v_servo_pin, GPIO.OUT)
h_pwm = GPIO.PWM(h_servo_pin, 50)
v_pwm = GPIO.PWM(v_servo_pin, 50)
h_pwm.start(0)
v_pwm.start(0)

picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
picam2.start()

mp_face = mp.solutions.face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5)
width = 640
height = 480

h_partition_angles = {1: 70, 2: 75, 3: 80, 4: 90, 5: 100, 6: 105, 7: 110}
v_partition_angles = {1: 50, 2: 70, 3: 90}
h_partition_boundaries = [
    (0, 70, 1), (90, 160, 2), (180, 250, 3), (270, 370, 4),
    (390, 460, 5), (480, 550, 6), (570, 640, 7)
]
v_partition_boundaries = [(0, 120, 1), (170, 290, 2), (340, 480, 3)]

h_current_angle = 90
v_current_angle = 70
h_current_partition = 4
v_current_partition = 2
last_detection_time = time.time()
face_timeout = 1.0

# User identification variables (from user_identifier.py)
rekognition = boto3.client('rekognition')
bucket_name = "pebo-user-images"
captured_image = "captured.jpg"
ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
REGION = os.getenv("AWS_REGION")
LOCAL_IMAGE_PATH = f"/home/pi/Documents/PEBO_project_aws/{captured_image}"
camera = Picamera2()

# Audio communication variables (from inter_device_communication_send_audio.py)
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 48000
CHUNK = 2048
RECORD_SECONDS = 5
SERVER_PORT = 12345
HOSTNAME = subprocess.check_output(['hostname']).strip().decode('utf-8')
VOLUME_MULTIPLIER = 5.0

# Helper Functions

async def speak_text(text, voice="en-US-AriaNeural"):
    """Convert text to speech using Edge TTS and play it."""
    filename = "response.mp3"
    tts = edge_tts.Communicate(text, voice)
    await tts.save(filename)
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.25)
    pygame.mixer.music.stop()
    pygame.mixer.music.unload()
    os.remove(filename)

def set_angle_smooth(pwm_obj, current_angle, target_angle, step=2):
    """Smoothly move the servo from current angle to target angle."""
    if current_angle == target_angle:
        return current_angle
    direction = 1 if target_angle > current_angle else -1
    for angle in range(current_angle, target_angle + direction, direction):
        duty = (angle / 18.0) + 2.5
        pwm_obj.ChangeDutyCycle(duty)
        time.sleep(0.05)
    duty = (target_angle / 18.0) + 2.5
    pwm_obj.ChangeDutyCycle(duty)
    time.sleep(0.01)
    pwm_obj.ChangeDutyCycle(0)
    return target_angle

def get_partition(position, boundaries):
    """Determine which partition the position falls into, or if it's in a gap."""
    for start_pos, end_pos, partition in boundaries:
        if start_pos <= position <= end_pos:
            return partition, False
    return None, True

def capture_and_upload():
    """Capture an image and upload it to S3."""
    camera.start()
    time.sleep(2)
    camera.capture_file(LOCAL_IMAGE_PATH)
    camera.stop()
    print("Image Captured.")
    s3_client = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)
    s3_client.upload_file(LOCAL_IMAGE_PATH, bucket_name, captured_image)
    print(f"Image uploaded to S3 bucket: {bucket_name}/{captured_image}")

def get_first_emotion_from_response(response):
    """Extract the first emotion from Rekognition's response."""
    if 'FaceDetails' in response and len(response['FaceDetails']) > 0:
        for face in response['FaceDetails']:
            if 'Emotions' in face and len(face['Emotions']) > 0:
                emotions_sorted = sorted(face['Emotions'], key=lambda x: x['Confidence'], reverse=True)
                return emotions_sorted[0]['Type']
    return "No emotions detected"

def recognize_user():
    """Recognize the user by comparing faces in S3."""
    try:
        s3_client = boto3.client('s3')
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix='user_')
        best_match_image = None
        highest_similarity = 0
        for item in response.get('Contents', []):
            reference_image = item['Key']
            if reference_image == captured_image:
                continue
            compare_response = rekognition.compare_faces(
                SourceImage={'S3Object': {'Bucket': bucket_name, 'Name': reference_image}},
                TargetImage={'S3Object': {'Bucket': bucket_name, 'Name': captured_image}},
                SimilarityThreshold=80
            )
            if compare_response['FaceMatches']:
                match_confidence = compare_response['FaceMatches'][0]['Similarity']
                print(f"Match Found with {reference_image}: {match_confidence:.2f}%")
                if match_confidence > highest_similarity:
                    highest_similarity = match_confidence
                    best_match_image = reference_image
        if best_match_image:
            emotion_response = rekognition.detect_faces(
                Image={'S3Object': {'Bucket': bucket_name, 'Name': captured_image}},
                Attributes=['ALL']
            )
            first_emotion = get_first_emotion_from_response(emotion_response)
            user_name = best_match_image.replace('user_', '').replace('.jpg', '')
            print(f"Recognized: {user_name}, Emotion: {first_emotion}")
            return {"match": True, "name": user_name, "confidence": highest_similarity, "emotion": first_emotion}
        else:
            print("No match found. Registering new user.")
            return {"match": False}
    except Exception as e:
        print(f"Error in user recognition: {e}")
        return {"match": False, "error": str(e)}

def get_ip_address():
    """Get the device's IP address."""
    try:
        return ni.ifaddresses('wlan0')[ni.AF_INET][0]['addr']
    except:
        try:
            return ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
        except:
            return "127.0.0.1"

def find_input_device():
    """Find a working input device index."""
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        if dev_info['maxInputChannels'] > 0:
            p.terminate()
            return i
    p.terminate()
    return None

def normalize_audio(all_audio_data, format, target_volume=0.9):
    """Normalize audio to a target volume level."""
    if format != pyaudio.paInt16:
        print("Warning: Normalization only supports 16-bit audio")
        return all_audio_data
    a = array.array('h')
    a.frombytes(b''.join(all_audio_data))
    max_sample = max(abs(sample) for sample in a)
    if max_sample == 0:
        return all_audio_data
    scale_factor = (32767 * target_volume) / max_sample
    for i in range(len(a)):
        a[i] = int(a[i] * scale_factor)
    normalized_data = a.tobytes()
    chunk_size = len(all_audio_data[0])
    normalized_chunks = [normalized_data[i:i+chunk_size] for i in range(0, len(normalized_data), chunk_size)]
    if len(normalized_data) % chunk_size != 0:
        normalized_chunks.append(normalized_data[-(len(normalized_data) % chunk_size):])
    return normalized_chunks

def record_audio(output_file):
    """Record audio from microphone."""
    print(f"Recording audio for {RECORD_SECONDS} seconds...")
    audio = pyaudio.PyAudio()
    device_index = find_input_device()
    try:
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True,
                           input_device_index=device_index, frames_per_buffer=CHUNK)
        frames = []
        for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
        stream.stop_stream()
        stream.close()
        frames = normalize_audio(frames, FORMAT, 0.9)
        wf = wave.open(output_file, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        print(f"Recording saved to {output_file}")
        audio.terminate()
        return output_file
    except Exception as e:
        print(f"Error recording audio: {e}")
        audio.terminate()
        return None

def send_file(file_path, receiver_ip):
    """Send audio file to the receiver."""
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist")
        return False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((receiver_ip, SERVER_PORT))
        s.send(f"{HOSTNAME}\n".encode())
        file_size = os.path.getsize(file_path)
        s.send(f"{file_size}\n".encode())
        with open(file_path, 'rb') as f:
            s.sendall(f.read())
        s.close()
        print(f"File {file_path} sent successfully to {receiver_ip}")
        return True
    except Exception as e:
        print(f"Error sending file: {e}")
        return False

def listen_continuously():
    """Continuously listen for wake word and commands."""
    wake_words = ["hey pebo", "pebo"]
    print("Listening for wake word...")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
    while not stop_event.is_set():
        try:
            with mic as source:
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=5)
            try:
                text = recognizer.recognize_google(audio).lower()
                print(f"Heard: {text}")
                for wake_word in wake_words:
                    if wake_word in text:
                        command_queue.put(("WAKE", None))
                        with mic as source:
                            print("Wake word detected! Listening for command...")
                            command_audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                        try:
                            command = recognizer.recognize_google(command_audio).lower()
                            print(f"Command: {command}")
                            command_queue.put(("COMMAND", command))
                        except sr.UnknownValueError:
                            print("Couldn't understand command.")
                            command_queue.put(("ERROR", "command_not_understood"))
                        except sr.RequestError:
                            print("Google Speech Recognition service unavailable")
                        break
            except sr.UnknownValueError:
                pass
            except sr.RequestError:
                print("Google Speech Recognition service unavailable")
                time.sleep(2)
        except Exception as e:
            print(f"Error in listen_continuously: {e}")
            time.sleep(1)

def face_tracking_thread_function():
    """Run face tracking in a separate thread."""
    global face_tracking_active, face_detected, h_current_angle, v_current_angle, h_current_partition, v_current_partition, last_detection_time
    print("Starting face tracking thread...")
    face_tracking_active = True
    try:
        while not stop_event.is_set():
            frame = picam2.capture_array()
            frame = cv2.resize(frame, (width, height))
            frame = cv2.flip(frame, cv2.ROTATE_180)
            image_input = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = mp_face.process(image_input)
            current_time = time.time()
            face_detected = False
            if results.detections:
                detection = results.detections[0]
                bbox = detection.location_data.relative_bounding_box
                x = int(bbox.xmin * width)
                y = int(bbox.ymin * height)
                w = int(bbox.width * width)
                h = int(bbox.height * height)
                cx = x + w // 2
                cy = y + h // 2
                h_partition, h_in_gap = get_partition(cx, h_partition_boundaries)
                v_partition, v_in_gap = get_partition(cy, v_partition_boundaries)
                face_detected = True
                last_detection_time = current_time
                if not h_in_gap and h_partition != h_current_partition:
                    h_target_angle = h_partition_angles[h_partition]
                    h_current_angle = set_angle_smooth(h_pwm, h_current_angle, h_target_angle)
                    h_current_partition = h_partition
                if not v_in_gap and v_partition != v_current_partition:
                    v_target_angle = v_partition_angles[v_partition]
                    v_current_angle = set_angle_smooth(v_pwm, v_current_angle, v_target_angle)
                    v_current_partition = v_partition
                trigger_queue.put("FACE_DETECTED")
            elif current_time - last_detection_time > face_timeout:
                if h_current_angle != 90 or v_current_angle != 70:
                    h_current_angle = set_angle_smooth(h_pwm, h_current_angle, 90)
                    v_current_angle = set_angle_smooth(v_pwm, v_current_angle, 70)
                    h_current_partition = 4
                    v_current_partition = 2
            time.sleep(0.01)
    except Exception as e:
        print(f"Face tracking thread error: {e}")
    finally:
        face_tracking_active = False

def user_identifier_thread_function():
    """Capture and identify a user."""
    capture_and_upload()
    result = recognize_user()
    if result["match"]:
        greeting = f"Hello {result['name']}, you seem {result['emotion'].lower()} today!"
        asyncio.run(speak_text(greeting))
    else:
        asyncio.run(speak_text("I don't recognize you. Please tell me your name."))
        # Note: Manual name input is not implemented here due to voice-based interaction preference.

def send_audio_message(receiver_ip):
    """Record and send an audio message."""
    audio_file = "recorded_audio.wav"
    if record_audio(audio_file):
        send_file(audio_file, receiver_ip)
        asyncio.run(speak_text("Message sent successfully."))
    else:
        asyncio.run(speak_text("Failed to record message."))

# Graceful shutdown
def signal_handler(sig, frame):
    print("Shutting down...")
    stop_event.set()
    set_angle_smooth(h_pwm, h_current_angle, 90)
    set_angle_smooth(v_pwm, v_current_angle, 70)
    time.sleep(0.5)
    h_pwm.stop()
    v_pwm.stop()
    GPIO.cleanup()
    cv2.destroyAllWindows()
    picam2.stop()
    camera.stop()
    print("Cleanup complete")
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Main loop
def main():
    global face_tracking_active
    print("PEBO Assistant Ready")
    threading.Thread(target=listen_continuously, daemon=True).start()
    receiver_ip = None  # Will be set when sending a message
    while not stop_event.is_set():
        try:
            event_type, data = command_queue.get(timeout=1)
            if event_type == "WAKE":
                asyncio.run(speak_text("Hello, how can I help you?"))
                if not face_tracking_active:
                    threading.Thread(target=face_tracking_thread_function, daemon=True).start()
            elif event_type == "COMMAND":
                command = data
                if "send message" in command:
                    if not receiver_ip:
                        receiver_ip = input("Enter the IP address of the receiver: ")  # Only ask once
                    threading.Thread(target=send_audio_message, args=(receiver_ip,), daemon=True).start()
                elif "stop tracking" in command or "exit" in command:
                    asyncio.run(speak_text("Goodbye!"))
                    stop_event.set()
                else:
                    conversation_history.append({"role": "user", "parts": [command]})
                    response = model.generate_content(conversation_history[-5:], generation_config={"max_output_tokens": 50})
                    reply = response.text
                    print(f"Gemini: {reply}")
                    asyncio.run(speak_text(reply))
                    conversation_history.append({"role": "model", "parts": [reply]})
            elif event_type == "ERROR":
                asyncio.run(speak_text("I didn't understand that. Please try again."))
        except queue.Empty:
            if trigger_queue.qsize() > 0:
                trigger = trigger_queue.get()
                if trigger == "FACE_DETECTED" and face_detected:
                    threading.Thread(target=user_identifier_thread_function, daemon=True).start()
        time.sleep(0.1)

if __name__ == "__main__":
    main()
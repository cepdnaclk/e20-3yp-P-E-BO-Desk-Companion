import firebase_admin
from firebase_admin import credentials, db
import json
import socket
import fcntl
import struct
import subprocess
import logging
import speech_recognition as sr
import asyncio
import edge_tts
import pygame

# Firebase & config paths
SERVICE_ACCOUNT_PATH = '/home/pi/PEBO/ipconfig/firebase_config.json'
DATABASE_URL = 'https://pebo-task-manager-767f3-default-rtdb.asia-southeast1.firebasedatabase.app'
JSON_CONFIG_PATH = '/home/pi/pebo_config.json'

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Audio setup
pygame.mixer.init()
recognizer = sr.Recognizer()
mic = sr.Microphone()

# 🔊 Speak using Edge TTS
async def speak_text(text):
    voice = "en-GB-SoniaNeural"
    filename = "say.mp3"
    await edge_tts.Communicate(text, voice).save(filename)
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.2)
    pygame.mixer.music.unload()

# 🎤 Listen using Google STT
def listen(timeout=8, phrase_time_limit=5):
    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("🎤 Listening...")
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        return recognizer.recognize_google(audio).lower()
    except Exception as e:
        print(f"❌ Listening error: {e}")
        return None

# 📡 Get IP address
def get_ip_address(ifname='wlan0'):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', bytes(ifname[:15], 'utf-8')))[20:24])
    except:
        return None

# 📶 Get current SSID
def get_wifi_ssid():
    try:
        result = subprocess.run(['iwgetid', '-r'], capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return None

# 🔁 Main interaction loop
async def inter_device_communicator():
    # Load local config
    try:
        with open(JSON_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        current_ssid = config.get('ssid')
        current_device_id = config.get('deviceId')
        user_id = config.get('userId')
    except:
        await speak_text("Cannot load device configuration.")
        return

    # Get current IP
    ip = get_ip_address()
    if not ip:
        await speak_text("I am not connected to Wi-Fi.")
        return

    # 🔥 Init Firebase
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
            firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
    except Exception as e:
        await speak_text("Failed to connect to Firebase.")
        return

    users = db.reference('users').get()
    if not users:
        await speak_text("No users found in database.")
        return

    # Find other devices on same SSID
    candidates = []
    for uid, user in users.items():
        for dev_id, dev in user.get("peboDevices", {}).items():
            if dev.get('ssid') == current_ssid and dev_id != current_device_id:
                candidates.append({
                    'ip': dev['ipAddress'],
                    'location': dev.get('location', 'Unknown'),
                    'user_id': uid,
                    'device_id': dev_id
                })

    if not candidates:
        await speak_text(f"No other devices found on {current_ssid}")
        return

    # Ask user to select one
    locs = [c['location'] for c in candidates]
    await speak_text(f"Which device would you like to contact in: {', '.join(locs)}?")
    location_input = listen()

    if not location_input:
        await speak_text("I didn’t catch that.")
        return

    match = next((c for c in candidates if location_input.lower() in c['location'].lower()), None)
    if match:
        await speak_text(f"Selected device in {match['location']} at IP {match['ip']}")
        # 👉 You can now connect to match['ip'] via socket
    else:
        await speak_text("No matching device found.")

# 🚀 Run
if __name__ == "__main__":
    asyncio.run(inter_device_communicator()) 

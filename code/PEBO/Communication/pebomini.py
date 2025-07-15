#!/usr/bin/env python3
import firebase_admin
from firebase_admin import credentials, db
import json
import socket
import fcntl
import struct
import subprocess
import logging
import asyncio
import speech_recognition as sr
import time
import os

# Paths and constants
SERVICE_ACCOUNT_PATH = '/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/ipconfig/firebase_config.json'
DATABASE_URL = 'https://pebo-task-manager-767f3-default-rtdb.asia-southeast1.firebasedatabase.app'
JSON_CONFIG_PATH = "/home/pi/pebo_config.json" 

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Speech setup
recognizer = sr.Recognizer()
mic = sr.Microphone()

def listen(prompt="Listening...", timeout=8, phrase_time_limit=6):
    print(prompt)
    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        text = recognizer.recognize_google(audio).lower().strip()
        print(f"✅ Recognized: {text}")
        return text
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def get_ip_address(ifname='wlan0'):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', bytes(ifname[:15], 'utf-8')))[20:24])
    except:
        return None

def get_wifi_ssid():
    try:
        result = subprocess.run(['iwgetid', '-r'], capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return None

async def inter_device_communicator():
    try:
        with open(JSON_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        current_ssid = config.get('ssid')
        current_device_id = config.get('deviceId')
    except Exception as e:
        print("⚠️ Config load error:", e)
        return

    ip = get_ip_address()
    if not ip:
        print("⚠️ Not connected to Wi-Fi.")
        return

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
            firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
    except Exception as e:
        print("⚠️ Firebase init error:", e)
        return

    users = db.reference('users').get()
    if not users:
        print("⚠️ No users found in Firebase.")
        return

    # Find other devices
    candidates = []
    for uid, user in users.items():
        for dev_id, dev in user.get("peboDevices", {}).items():
            if dev.get('ssid') == current_ssid and dev_id != current_device_id:
                candidates.append({
                    'ip': dev['ipAddress'],
                    'location': dev.get('location', 'Unknown'),
                    'device_id': dev_id
                })

    if not candidates:
        print(f"⚠️ No other devices found on SSID: {current_ssid}")
        return

    # Ask user which device to connect to
    locs = [c['location'] for c in candidates]
    print(f"🎙️ Ask: Which device to connect to? Options: {', '.join(locs)}")
    location_input = listen(prompt="🎤 Which device would you like to connect to?")

    if not location_input:
        print("❌ No location input received.")
        return

    selected = next((c for c in candidates if location_input.lower() in c['location'].lower()), None)

    if selected:
        print(f"✅ Connecting to device in {selected['location']} at IP: {selected['ip']}")
        subprocess.Popen(["python3", "/home/pi/pi_audio_node.py", selected['ip']])
    else:
        print("❌ No matching device found.")

if __name__ == "__main__":
    try:
        asyncio.run(inter_device_communicator())
    except KeyboardInterrupt:
        print("🛑 Interrupted by user.")

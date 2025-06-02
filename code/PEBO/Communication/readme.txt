Objective: Ensure the Raspberry Pi retrieves its IP address whenever the Wi-Fi network changes and stores it in Firebase Realtime Database at users/{user_id}/peboDevices/{device_id}/ipAddress, running continuously after the first setup.

1. Prepare Dependencies
Install Python Packages:
bash

Copy
pip install firebase-admin
Install Wireless Tools (for SSID detection):
bash

Copy
sudo apt-get update
sudo apt-get install wireless-tools
2. Set Up Firebase Service Account
Download Service Account Key:
Go to Firebase Console > Project Settings > Service Accounts > Generate New Private Key.
Save the JSON file to the Raspberry Pi (e.g., /home/pi/firebase_service_account.json).
Note: The Firebase configuration is already extracted from your mobile app code:
text

Copy
databaseURL: https://pebo-task-manager-767f3-default-rtdb.asia-southeast1.firebasedatabase.app
3. Deploy the Script
Save the Script:
Copy the following Python script to /home/pi/store_ip_on_wifi_change.py:
python

Copy
import socket
import fcntl
import struct
import subprocess
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/pi/store_ip.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(_name_)

def initialize_firebase():
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate('/home/pi/firebase_service_account.json')
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://pebo-task-manager-767f3-default-rtdb.asia-southeast1.firebasedatabase.app'
            })
            logger.info("Firebase initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise

def get_ip_address(ifname='wlan0'):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip = socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,
            struct.pack('256s', bytes(ifname[:15], 'utf-8'))
        )[20:24])
        return ip
    except Exception as e:
        logger.warning(f"Error getting IP address: {e}")
        return None

def get_wifi_ssid():
    try:
        result = subprocess.run(['iwgetid', '-r'], capture_output=True, text=True, timeout=5)
        ssid = result.stdout.strip()
        return ssid if ssid else None
    except Exception as e:
        logger.warning(f"Error getting SSID: {e}")
        return None

def store_ip_to_firebase(user_id, device_id, ip_address, ssid):
    try:
        ref = db.reference(f'users/{user_id}/peboDevices/{device_id}')
        ref.update({
            'ipAddress': ip_address,
            'ssid': ssid or 'Unknown',
            'lastUpdated': int(time.time() * 1000)
        })
        logger.info(f"Stored IP {ip_address} and SSID {ssid} for user {user_id}, device {device_id}")
    except Exception as e:
        logger.error(f"Error storing IP to Firebase: {e}")

def main():
    try:
        initialize_firebase()
    except Exception as e:
        logger.error("Exiting due to Firebase initialization failure")
        return

    user_id = "CURRENT_USER_ID"  # Replace with actual user ID
    device_id = "pebo_rpi_1"

    last_ip = None
    last_ssid = None

    while True:
        try:
            current_ip = get_ip_address()
            current_ssid = get_wifi_ssid()

            if current_ip and (current_ip != last_ip or current_ssid != last_ssid):
                logger.info(f"Wi-Fi change detected: IP={current_ip}, SSID={current_ssid}")
                store_ip_to_firebase(user_id, device_id, current_ip, current_ssid)
                last_ip = current_ip
                last_ssid = current_ssid
            elif not current_ip:
                logger.info("No Wi-Fi connection detected")
                if last_ip or last_ssid:
                    store_ip_to_firebase(user_id, device_id, None, None)
                    last_ip = None
                    last_ssid = None

            time.sleep(30)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(60)

if _name_ == "_main_":
    main()
Update the service account key path in the script (line: cred = credentials.Certificate('/home/pi/firebase_service_account.json')).
Replace "CURRENT_USER_ID" with the actual Firebase user ID. If the user ID is dynamic, let me know how it’s provided (e.g., file, environment variable).
Set permissions:
bash

Copy
chmod +x /home/pi/store_ip_on_wifi_change.py
4. Configure Systemd Service
Create Service File:
bash

Copy
sudo nano /etc/systemd/system/store-ip-on-wifi-change.service
Add:
text

Copy
[Unit]
Description=Store Raspberry Pi IP to Firebase on Wi-Fi Change
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/store_ip_on_wifi_change.py
WorkingDirectory=/home/pi
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
Enable and Start Service:
bash

Copy
sudo systemctl enable store-ip-on-wifi-change.service
sudo systemctl start store-ip-on-wifi-change.service
Why This Ensures Autonomy: The service starts on boot, waits for network connectivity, and restarts automatically if it crashes. The script’s while True loop continuously monitors Wi-Fi changes every 30 seconds.
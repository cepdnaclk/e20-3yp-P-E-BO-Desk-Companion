PEBO - Smart Desk Assistant Robot
Introduction
PEBO is a state-of-the-art smart desk assistant robot designed to enhance productivity and deliver personalized user experiences in a workspace environment. By integrating advanced hardware, software, and cloud services, PEBO offers features such as facial recognition, voice-activated commands, real-time face tracking, emotion-based interactions, and inter-device communication. The project comprises a Raspberry Pi-based hardware system and a React Native mobile application, pebo-desk-companion, which provides an intuitive interface for user management, device control, and configuration.
This README provides a comprehensive, beginner-friendly guide to setting up, configuring, and using PEBO. It includes detailed instructions for account creation, Wi-Fi setup via QR codes, app settings, and hardware configuration, with all commands clearly formatted for ease of use.
Project Overview
PEBO is developed by a dedicated team of four:

Buddhika Ariyarathne: Hardware and software integration specialist.
Yasiru Edirimanna: AI and software development lead.
Yohan Senadheera: Hardware design and system architecture expert.
Bhagya Senevirathna: AI integration and software development contributor.

Objectives

Personalized Interactions: Identifies users via facial recognition and tailors responses.
Voice Interaction: Processes natural language commands for tasks, communication, and music playback.
Emotion Expression: Displays emotions through arm movements and dual OLED eye displays.
Face Tracking: Tracks user movements using a camera and servo motors.
Inter-Device Communication: Enables audio calls between PEBO devices on the same network.
Mobile Control: Provides a user-friendly app for profile management, Wi-Fi configuration, and device control.

Features
Hardware Features

Facial Recognition: Utilizes AWS Rekognition to identify users from camera input, enabling personalized interactions.
Face Tracking: A camera on a servo-controlled pan-tilt mechanism tracks the user’s face in real time.
Voice Interaction: Processes commands like "call pebo" or "play song " using Gemini API and Whisper for natural language understanding.
Emotion Expression:
Dual OLED displays (left and right eyes) show emotions like Happy, Sad, Angry, Love, or Normal.
Servo-controlled arms express emotions via predefined movements (e.g., say_hi, express_happy).


Inter-Device Communication:
Initiates audio calls between PEBO devices on the same Wi-Fi network.
Supports voice command "call pebo" to list available devices.
Displays caller ID and plays a ringing tone for incoming calls.
Allows call acceptance/rejection via voice or app.


Music Playback: Plays songs triggered by "play song" or "play song " commands.

Mobile App Features (pebo-desk-companion)
The pebo-desk-companion app, built with React Native and Expo, serves as the primary control interface. Key features include:

User Profile Management:
Create and manage accounts with Firebase Authentication.
Upload profile images to Amazon S3 for facial recognition.


Wi-Fi Configuration via QR Code:
Generate QR codes containing Wi-Fi credentials (SSID and password).
Enable PEBO devices to connect to networks by scanning QR codes.


Settings Configuration:
Customize notification preferences, device pairing, and user profile settings.
Manage connected PEBO devices and their statuses.


Device Control:
Initiate or accept inter-device calls.
Set tasks like reminders or control face tracking.


Over-the-Air (OTA) Updates: Seamlessly update the app using Expo’s EAS Update.
User Interface: Intuitive screens for Home, Profile, Settings, Wi-Fi Setup, and Device Management, with real-time feedback.

Cloud Integration

AWS Services:
Rekognition: Powers facial recognition.
S3: Securely stores user profile images.


Firebase:
Authentication for secure user login (email/password or Google).
Firestore and Realtime Database for user profiles and device communication.


Google Gemini API: Enables natural language processing for voice interactions.

Technology Stack
Hardware

Raspberry Pi 4: Core processing unit for running scripts and controlling peripherals.
Pi Camera Module: Captures images for facial recognition and QR code scanning.
Servo Motors (e.g., SG90): Enable pan-tilt camera movement and arm expressions.
Microphone and Speaker: Support voice input/output (USB or 3.5mm jack).
Dual OLED Displays: Display emotions on left and right eyes (I2C addresses 0x3D and 0x3C).
PCA9685 PWM Controller: Manages servo motor control (I2C address 0x40).
LED: Indicates listening state (GPIO 18).

Software

Mobile App:
React Native: Framework for building the pebo-desk-companion app.
Expo: Simplifies app development, testing, and OTA updates.
expo-image-picker: Handles profile image uploads.
react-native-qrcode-svg: Generates QR codes for Wi-Fi setup.
aws-sdk: Integrates with AWS S3 and Rekognition.
firebase: Manages authentication and real-time database.


Raspberry Pi:
Python 3.8+: Core programming language for hardware control and AI integration.
google.generativeai: Interfaces with Gemini API for natural language processing.
pygame: Handles audio playback for responses and music.
edge_tts: Converts text to speech using Microsoft Edge TTS.
speech_recognition: Captures and recognizes speech via Google Speech or PocketSphinx.
whisper: Offline speech recognition using OpenAI’s Whisper model.
sounddevice: Records audio for Whisper transcription.
numpy: Processes audio data.
scipy: Saves audio recordings as WAV files.
pyzbar: Decodes QR codes for Wi-Fi setup.
opencv-python-headless: Processes camera input for QR code scanning.
RPi.GPIO: Controls GPIO pins for LED and servo interactions.
adafruit-circuitpython-busdevice: Manages I2C communication for OLED displays.
smbus: Facilitates I2C communication for PCA9685.
firebase-admin: Integrates with Firebase for device communication.
logging: Logs system events for debugging.
socket, fcntl, struct: Retrieves IP address for device communication.
subprocess: Executes system commands (e.g., Wi-Fi connection, FFmpeg).
ffmpeg: Amplifies audio output for text-to-speech.
threading, asyncio: Manages concurrent tasks (e.g., arm and eye expressions).
re, random, os, tempfile, errno: Supports text processing, randomization, and file handling.



Cloud Services

AWS Rekognition: Facial recognition for user identification.
AWS S3: Stores user profile images.
Firebase Authentication: Manages user login (email/password, Google).
Firebase Firestore/Realtime Database: Handles user profiles and device communication.
Google Gemini API: Powers natural language understanding.

Architecture

Modular Hardware: Designed for easy upgrades and maintenance.
Cloud-Based Backend: Ensures scalability and real-time operations.

Getting Started
Prerequisites

Mobile App Development:
Node.js (v16+): nodejs.org.
Expo Go app (iOS/Android): App Store or Google Play.
Code editor (e.g., Visual Studio Code): code.visualstudio.com.


Raspberry Pi Setup:
Raspberry Pi 4 with Raspbian OS (Bullseye or later).
Pi Camera Module (USB or CSI).
Two SG90 servo motors (GPIO 17 for pan, 18 for tilt).
USB microphone and speaker (or 3.5mm jack).
Dual OLED displays (I2C addresses 0x3D, 0x3C).
PCA9685 PWM controller (I2C address 0x40).
LED on GPIO 18.
Python 3.8+.


Cloud Accounts:
AWS account (Rekognition, S3): aws.amazon.com.
Firebase account: firebase.google.com.
Google Gemini API key: ai.google.dev.



Setting Up the Mobile App

Clone the Repository:
git clone https://github.com/your-username/pebo-desk-companion.git
cd pebo-desk-companion

If the repository doesn’t exist, create one:
git init
git remote add origin https://github.com/your-username/pebo-desk-companion.git


Install Dependencies:Install Expo CLI:
npm install -g expo-cli

Install project dependencies:
npm install

Verify:
npm list


Configure Environment Variables:Create .env in the project root:
FIREBASE_API_KEY=your_firebase_api_key
FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
FIREBASE_PROJECT_ID=your_firebase_project_id
FIREBASE_STORAGE_BUCKET=your_project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=your_sender_id
FIREBASE_APP_ID=your_app_id
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_S3_BUCKET=your_s3_bucket_name
AWS_REGION=your_aws_region


Firebase: Find credentials in Firebase Console > Project Settings > General > Your Apps.
AWS: Create an IAM user with S3 and Rekognition permissions.


Update Expo Configuration:Edit app.json:
{
  "expo": {
    "name": "PEBO Desk Companion",
    "slug": "pebo-desk-companion",
    "version": "1.0.0",
    "platforms": ["ios", "android"],
    "extra": {
      "eas": {
        "projectId": "your-expo-project-id"
      }
    },
    "android": {
      "package": "com.yourusername.pebodeskcompanion"
    },
    "ios": {
      "bundleIdentifier": "com.yourusername.pebodeskcompanion"
    }
  }
}

Get projectId:
expo login
expo whoami


Account Creation and Settings Setup:

Account Creation:
Uses Firebase Authentication for email/password or Google Sign-In.
On first launch, users sign up via the login screen.
After signup, users create a profile:
Enter a username.
Upload a profile image via the Profile screen (expo-image-picker).
Image is uploaded to AWS S3 and linked to the user’s Firebase UID.


Example code (auth.js):import { getAuth, createUserWithEmailAndPassword } from 'firebase/auth';
import { getFirestore, doc, setDoc } from 'firebase/firestore';
const auth = getAuth();
const db = getFirestore();
createUserWithEmailAndPassword(auth, email, password)
  .then((userCredential) => {
    const user = userCredential.user;
    console.log('User created:', user.uid);
    setDoc(doc(db, 'users', user.uid), {
      username: 'YourName',
      profileImage: 's3://your_s3_bucket_name/user_profile.jpg'
    });
  })
  .catch((error) => {
    console.error('Error:', error.message);
  });




Settings Configuration:
Access Settings screen to configure:
Notifications: Enable/disable push notifications for calls/tasks.
Device Pairing: Link to a PEBO device using its ID (stored in Firestore).
Profile Updates: Edit username or re-upload profile image.
Language: Select display language (if supported).


Save settings:import { getFirestore, doc, updateDoc } from 'firebase/firestore';
const db = getFirestore();
await updateDoc(doc(db, 'users', user.uid), {
  notifications: true,
  pairedDevice: 'pebo_device_id',
  language: 'en'
});






Wi-Fi Configuration via QR Code:

Purpose: Allows PEBO to connect to Wi-Fi by scanning a QR code.
App Setup:
Navigate to Wi-Fi Setup screen.
Enter SSID and password.
Generate QR code (react-native-qrcode-svg):import QRCode from 'react-native-qrcode-svg';
const wifiData = `WIFI:S:${ssid};T:WPA;P:${password};;`;
return <QRCode value={wifiData} size={200} />;


Display QR code on the phone screen.


Verification:
Ensure QR code format is correct (e.g., WIFI:S:MyNetwork;T:WPA;P:MyPassword;;).
Use a QR code reader app to verify.




Run the App:
expo start


Scan the QR code with Expo Go.
Or use:expo start --ios  # iOS simulator
expo start --android  # Android emulator





Setting Up the Raspberry Pi

Prepare the Hardware:

Connect Pi Camera Module to CSI port.
Attach SG90 servo motors to GPIO 17 (pan) and 18 (tilt).
Connect USB microphone and speaker (or 3.5mm jack).
Attach dual OLED displays (I2C addresses 0x3D, 0x3C).
Connect PCA9685 PWM controller (I2C address 0x40).
Connect LED to GPIO 18.


Install Dependencies:Update system:
sudo apt update && sudo apt upgrade -y

Install Python and pip:
sudo apt install python3 python3-pip -y

Install libraries:
pip3 install firebase-admin boto3 pyzbar opencv-python-headless google-generativeai pygame edge-tts speechrecognition whisper sounddevice numpy scipy smbus adafruit-circuitpython-busdevice

Install FFmpeg:
sudo apt install ffmpeg -y

Enable camera:
sudo raspi-config

Navigate to Interface Options > Camera > Enable.

Configure Firebase:

Download service account key (Firebase Console > Project Settings > Service Accounts).
Save as /home/pi/pebo/serviceAccountKey.json.
Initialize Firebase:import firebase_admin
from firebase_admin import credentials, firestore
cred = credentials.Certificate('/home/pi/pebo/serviceAccountKey.json')
firebase_admin.initialize_app(cred, {'databaseURL': 'https://pebo-task-manager-767f3-default-rtdb.asia-southeast1.firebasedatabase.app'})
db = firestore.client()




Configure AWS:
pip3 install awscli
aws configure

Enter Access Key ID, Secret Access Key, region (e.g., us-east-1), and output format (json).

QR Code Wi-Fi Setup:Create wifi_setup.py:
import cv2
import pyzbar.pyzbar as pyzbar
cap = cv2.VideoCapture(0)
while True:
    ret, frame = cap.read()
    if not ret:
        continue
    decoded_objects = pyzbar.decode(frame)
    for obj in decoded_objects:
        wifi_data = obj.data.decode('utf-8')
        if wifi_data.startswith('WIFI:'):
            print(f'Wi-Fi Data: {wifi_data}')
            # Parse and connect (e.g., via nmcli)
    if decoded_objects:
        break
cap.release()

Connect to Wi-Fi:
nmcli dev wifi connect "ssid" password "password"


Run the Main Script:Save the provided script as pebo_main.py:
nano /home/pi/pebo/pebo_main.py

Update GOOGLE_API_KEY with your Gemini API key.Run:
python3 /home/pi/pebo/pebo_main.py



Building the Production APK

Set Up EAS Build:
npm install -g eas-cli

Create eas.json:
{
  "build": {
    "production": {
      "android": {
        "buildType": "apk"
      }
    }
  }
}


Configure Signing Credentials:
eas credentials


Build the APK:
eas build -p android --profile production


Publish OTA Updates:
eas update --branch production



Usage
Mobile App

Account Creation:
Sign up with email/password or Google Sign-In.
Set username and upload profile image in Profile screen.


Wi-Fi Configuration:
Enter SSID/password in Wi-Fi Setup screen to generate QR code.
Show QR code to PEBO’s camera.


Settings:
Configure notifications, device pairing, and profile in Settings screen.


Device Control:
Manage devices, initiate calls, or set tasks in Device Management screen.



Raspberry Pi

Voice Commands: Say "call pebo", "play song ", or trigger phrases like "hi PEBO".
Face Tracking: Camera tracks user face.
Emotion Expression: Arms and OLED eyes display emotions (Happy, Sad, etc.).
Wi-Fi Setup: Scans QR codes for network connectivity.

Troubleshooting

App Issues:
Verify .env credentials.
Run expo doctor.


Raspberry Pi Issues:
Check hardware connections.
Verify AWS/Firebase/Gemini credentials.


QR Code Issues:
Ensure correct format and lighting.


Facial Recognition Issues:
Verify AWS Rekognition and lighting conditions.


Audio Issues:
Check microphone/speaker connections and FFmpeg installation.



Contributing

Fork the repository.
Create a branch:git checkout -b feature/your-feature


Commit changes:git commit -m "Add your feature"


Push:git push origin feature/your-feature


Open a pull request.

License
MIT License. See LICENSE.
Contact

Buddhika Ariyarathne: https://www.thecn.com/EA770
Yasiru Edirimanna: https://www.thecn.com/EE452
Yohan Senadheera: https://www.thecn.com/ES1366
Bhagya Senevirathna: https://www.thecn.com/ES1368

Acknowledgments

Thanks to the React Native, Expo, AWS, Firebase, and Google AI communities.
Gratitude to our team for their innovative contributions to PEBO.

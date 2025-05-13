# pebo_camera.py - Runs on Raspberry Pi to handle image capture and upload

import time
import os
import json
import boto3
import firebase_admin
from firebase_admin import credentials, db
from picamera import PiCamera
from datetime import datetime

# Configuration
CONFIG_FILE = '/home/pi/pebo_config.json'
LOCAL_IMAGE_PATH = '/home/pi/images'
PEBO_ID = None  # Will be loaded from config

# Initialize camera
camera = PiCamera()
camera.resolution = (1280, 720)  # Set resolution as needed

# Ensure image directory exists
os.makedirs(LOCAL_IMAGE_PATH, exist_ok=True)

def load_config():
    """Load PEBO configuration from file."""
    global PEBO_ID
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            PEBO_ID = config.get('pebo_id')
            return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

def initialize_firebase(config):
    """Initialize Firebase connection."""
    try:
        # Load Firebase service account credentials from config
        if 'firebase_cred' in config:
            cred_dict = config['firebase_cred']
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                'databaseURL': config.get('firebase_url', 'https://your-project-default-rtdb.firebaseio.com/')
            })
            return True
        else:
            print("Firebase credentials not found in config")
            return False
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        return False

def get_s3_config():
    """Get S3 configuration from Firebase."""
    try:
        # Get user ID from configuration
        config = load_config()
        user_id = config.get('user_id')
        
        if not user_id:
            print("User ID not found in config")
            return None
            
        # Fetch S3 config from Firebase
        s3_config_ref = db.reference(f'/users/{user_id}/s3Config')
        s3_config = s3_config_ref.get()
        
        if not s3_config:
            print("S3 configuration not found")
            return None
            
        return s3_config
    except Exception as e:
        print(f"Error getting S3 config: {e}")
        return None

def capture_image():
    """Capture an image with the PiCamera and return the file path."""
    try:
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pebo_{PEBO_ID}_{timestamp}.jpg"
        file_path = os.path.join(LOCAL_IMAGE_PATH, filename)
        
        # Capture the image
        camera.start_preview()
        time.sleep(2)  # Give the camera time to adjust to light conditions
        camera.capture(file_path)
        camera.stop_preview()
        
        print(f"Image captured: {file_path}")
        return file_path, filename
    except Exception as e:
        print(f"Error capturing image: {e}")
        return None, None

def upload_to_s3(file_path, filename):
    """Upload captured image to S3 and return the URL."""
    try:
        # Get S3 configuration
        s3_config = get_s3_config()
        if not s3_config:
            return None
            
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=s3_config.get('accessKey'),
            aws_secret_access_key=s3_config.get('secretKey')
        )
        
        # Upload file to S3
        bucket_name = s3_config.get('bucketName')
        s3_key = f"pebo_images/{filename}"
        
        s3_client.upload_file(file_path, bucket_name, s3_key)
        
        # Generate URL
        region = s3_client.meta.region_name
        url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
        
        print(f"Image uploaded to S3: {url}")
        return url
    except Exception as e:
        print(f"Error uploading to S3: {e}")
        return None

def update_firebase_with_image_url(image_url):
    """Update Firebase with the S3 image URL."""
    try:
        if not PEBO_ID:
            print("PEBO ID not set")
            return False
            
        # Update current photo
        photo_ref = db.reference(f'/peboPhotos/{PEBO_ID}')
        photo_ref.set(image_url)
        
        # Add to history
        history_ref = db.reference(f'/peboPhotoHistory/{PEBO_ID}').push()
        history_ref.set({
            'url': image_url,
            'timestamp': datetime.now().isoformat()
        })
        
        # Update the capture status
        status_ref = db.reference(f'/peboActions/{PEBO_ID}/captureImage/status')
        status_ref.set('completed')
        
        print("Firebase updated with image URL")
        return True
    except Exception as e:
        print(f"Error updating Firebase: {e}")
        return False

def check_for_capture_request():
    """Check if there's a pending capture request in Firebase."""
    try:
        if not PEBO_ID:
            return False
            
        capture_ref = db.reference(f'/peboActions/{PEBO_ID}/captureImage')
        capture_data = capture_ref.get()
        
        if capture_data and capture_data.get('status') == 'pending':
            return True
        return False
    except Exception as e:
        print(f"Error checking for capture request: {e}")
        return False

def process_capture_request():
    """Process an image capture request."""
    try:
        # Update status to processing
        status_ref = db.reference(f'/peboActions/{PEBO_ID}/captureImage/status')
        status_ref.set('processing')
        
        # Capture image
        file_path, filename = capture_image()
        if not file_path:
            status_ref.set('failed')
            return
            
        # Upload to S3
        image_url = upload_to_s3(file_path, filename)
        if not image_url:
            status_ref.set('failed')
            return
            
        # Update Firebase with image URL
        update_firebase_with_image_url(image_url)
    except Exception as e:
        print(f"Error processing capture request: {e}")
        try:
            status_ref = db.reference(f'/peboActions/{PEBO_ID}/captureImage/status')
            status_ref.set('failed')
        except:
            pass

def main():
    """Main function to run the camera service."""
    # Load configuration
    config = load_config()
    if not PEBO_ID:
        print("PEBO ID not configured. Please set up the device first.")
        return
        
    # Initialize Firebase
    if not initialize_firebase(config):
        print("Failed to initialize Firebase. Check configuration.")
        return
        
    print(f"PEBO Camera Service started (ID: {PEBO_ID})")
    
    try:
        while True:
            # Check for capture requests
            if check_for_capture_request():
                print("Capture request detected")
                process_capture_request()
                
            # Sleep to avoid excessive polling
            time.sleep(5)
    except KeyboardInterrupt:
        print("Service stopped by user")
    finally:
        # Clean up
        camera.close()
        print("Camera closed")

if __name__ == "__main__":
    main()
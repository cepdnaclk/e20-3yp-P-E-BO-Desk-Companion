import RPi.GPIO as GPIO
import boto3
from picamera import PiCamera
from time import sleep

# AWS S3 Configuration
# AWS S3 Configuration
ACCESS_KEY = "AKIATTSKFOHRLPXVE5PM"
SECRET_KEY = "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"
BUCKET_NAME = "pebo-user-images"
IMAGE_NAME = "captured.jpg"
LOCAL_IMAGE_PATH = f"/home/pi/{IMAGE_NAME}"

# GPIO Button Setup
BUTTON_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Initialize Camera
camera = PiCamera()

def capture_and_upload():
    camera.start_preview()
    sleep(2)
    camera.capture(LOCAL_IMAGE_PATH)
    camera.stop_preview()
    print("Image Captured.")

    s3_client = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)
    s3_client.upload_file(LOCAL_IMAGE_PATH, BUCKET_NAME, IMAGE_NAME)

    print(f"Image uploaded to S3 bucket: {BUCKET_NAME}/{IMAGE_NAME}")

while True:
    if GPIO.input(BUTTON_PIN) == GPIO.LOW:
        capture_and_upload()
        sleep(1)

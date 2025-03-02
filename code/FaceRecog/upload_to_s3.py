import boto3
from picamera import PiCamera
from time import sleep

# AWS S3 Configuration
ACCESS_KEY = "YOUR_ACCESS_KEY"
SECRET_KEY = "YOUR_SECRET_KEY"
BUCKET_NAME = "pebo-user-images"
IMAGE_NAME = "captured.jpg"
LOCAL_IMAGE_PATH = f"/home/pi/{IMAGE_NAME}"

# Initialize Camera
camera = PiCamera()

# Capture Image
camera.start_preview()
sleep(2)
camera.capture(LOCAL_IMAGE_PATH)
camera.stop_preview()

print("Image Captured.")

# Upload Image to S3
s3_client = boto3.client(
    's3',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY
)
s3_client.upload_file(LOCAL_IMAGE_PATH, BUCKET_NAME, IMAGE_NAME)

print(f"Image uploaded to S3 bucket: {BUCKET_NAME}/{IMAGE_NAME}")

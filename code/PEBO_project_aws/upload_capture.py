import boto3
from picamera2 import Picamera2
from time import sleep

# AWS S3 Configuration
ACCESS_KEY = "AKIATTSKFOHRLPXVE5PM"
SECRET_KEY = "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"
BUCKET_NAME = "pebo-user-images"
#IMAGE_NAME = "user_Eeshawa.jpg"
IMAGE_NAME = "captured.jpg"
#IMAGE_NAME = "user_reference.jpg"
LOCAL_IMAGE_PATH = f"/home/pi/Documents/PEBO_project_aws/{IMAGE_NAME}"


# Initialize Camera
camera = Picamera2()

def capture_and_upload():
    camera.start()
    sleep(2)
    camera.capture_file(LOCAL_IMAGE_PATH)
    camera.stop_preview()
    print("Image Captured.")

    s3_client = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)
    s3_client.upload_file(LOCAL_IMAGE_PATH, BUCKET_NAME, IMAGE_NAME)

    print(f"Image uploaded to S3 bucket: {BUCKET_NAME}/{IMAGE_NAME}")

   
capture_and_upload()
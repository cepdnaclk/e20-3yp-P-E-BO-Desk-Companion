import cv2
import boto3

s3 = boto3.client('s3')
bucket_name = "pebo-user-image"

def capture_image():
    cam = cv2.VideoCapture(0)
    ret, frame = cam.read()
    if not ret:
        print("Failed to capture image")
        return None
    file_name = "user_image.jpg"
    cv2.imwrite(file_name, frame)
    cam.release()
    return file_name

def upload_to_s3(file_name):
    s3.upload_file(file_name, bucket_name, file_name)
    print(f"Uploaded {file_name} to {bucket_name}")

image_file = capture_image()
if image_file:
    upload_to_s3(image_file)

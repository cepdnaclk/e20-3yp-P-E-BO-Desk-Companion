from picamera2 import Picamera2
from time import sleep

# Initialize the camera
camera = Picamera2()

# Start the camera preview
camera.start()

# Give time for the camera to adjust
sleep(2)

# Capture an image
camera.capture_file('/home/pi/Documents/PEBO_project_aws/captured.jpg') #/home/pi/Documents/PEBO_project_aws/capture_image.py

# Stop the preview
camera.stop_preview()

print("Image captured: captured.jpg")



# camera.capture_file('/home/pi/Documents/PEBO_project_aws/captured.jpg') #/home/pi/Documents/PEBO_project_aws/capture_image.py

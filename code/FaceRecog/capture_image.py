from picamera import PiCamera
from time import sleep

camera = PiCamera()

# Capture an image
camera.start_preview()
sleep(2)  # Allow the camera to adjust
camera.capture('/home/pi/captured.jpg')
camera.stop_preview()

print("Image captured: captured.jpg")

import time
import RPi.GPIO as GPIO
import spidev
import adafruit_rgb_display.st7735 as st7735
from PIL import Image, ImageDraw

# Set up GPIO mode
GPIO.setmode(GPIO.BCM)

# Define pin numbers
CS_PIN = 8    # SPI Chip Select (BCM 8)
DC_PIN = 24   # Data/Command (BCM 24)
RST_PIN = 25  # Reset (BCM 25)

# Set up SPI interface
spi = spidev.SpiDev()
spi.open(0, 0)  # SPI bus 0, device 0
spi.max_speed_hz = 24000000  # 24 MHz

# Custom GPIO pin handling class
class GPIOPin:
    def __init__(self, pin):
        self.pin = pin
        GPIO.setup(self.pin, GPIO.OUT)

    def value(self, val):
        GPIO.output(self.pin, val)

# Create pin objects
cs = GPIOPin(CS_PIN)
dc = GPIOPin(DC_PIN)
rst = GPIOPin(RST_PIN)

# Initialize the ST7735 display
disp = st7735.ST7735R(
    spi, rotation=90, cs=cs, dc=dc, rst=rst,
    baudrate=24000000, width=128, height=160,
    x_offset=0, y_offset=0
)

# Clear the display
disp.fill(0)

# Create an image with red color
image = Image.new("RGB", (disp.width, disp.height), (255, 0, 0))

# Display the image
disp.image(image)

# Keep the display on for 5 seconds
time.sleep(5)

# Clean up
GPIO.cleanup()

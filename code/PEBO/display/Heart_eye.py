import board
import busio
from PIL import Image, ImageDraw
import adafruit_ssd1306
from math import sin, cos, pow

# Create the I2C interface
i2c = busio.I2C(board.SCL, board.SDA)

# Create the OLED display object (128x64 OLED)
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)

# Clear the display
oled.fill(0)
oled.show()

# Create a blank image for drawing (1-bit color)
image = Image.new("1", (oled.width, oled.height))
draw = ImageDraw.Draw(image)

def draw_heart(draw, x, y, size):
    """Draw a heart shape at position x, y with given size"""
    points = []
    for t in range(0, 628):  # 0 to 2π in steps of 0.01
        t = t / 100  # Convert to radians
        x_val = 16 * pow(sin(t), 3)
        y_val = 13 * cos(t) - 5 * cos(2*t) - 2 * cos(3*t) - cos(4*t)
        points.append((x + int(x_val * size / 16), y - int(y_val * size / 16)))
    draw.polygon(points, fill=1)

# Draw the heart in the center of the screen
draw_heart(draw, 64, 32, size=30)

# Display the image
oled.image(image)
oled.show()

#!/usr/bin/env python3
"""
FluxGarage RoboEyes for Dual OLED Displays - Python Version with Emotion Functions
Displays left eye on one OLED and right eye on another OLED
Modified for two separate I2C OLED displays with 90 degree rotation support
and dedicated emotion functions
Fixed blinking to only change height, maintaining rounded rectangle shape
Increased blinking speed by reducing interval and speeding up height transition
Fixed bottom ellipses crossing above top ellipses during blink
Added Love mood with parametric heart shapes, faster y-axis rotation, and bouncing effect
Added QR mood to display QR codes on both eyes encoding a 6-digit device ID

Original Copyright (C) 2024 Dennis Hoelscher
Modified for dual display setup, rotation fix, emotion functions, blink fix, faster blinking,
corrected ellipse positioning, Love mood with animated hearts, and QR code display
"""

import time
import board
import busio
from PIL import Image, ImageDraw
import adafruit_ssd1306
import random
from math import sin, cos, pow
import threading
import qrcode

# Constants for mood types
DEFAULT = 0
TIRED = 1
ANGRY = 2
HAPPY = 3
LOVE = 4
QR = 5  # New mood for QR code display

# For turning things on or off
ON = 1
OFF = 0

# For predefined positions
N = 1   # north, top center
NE = 2  # north-east, top right
E = 3   # east, middle right
SE = 4  # south-east, bottom right
S = 5   # south, bottom center
SW = 6  # south-west, bottom left
W = 7   # west, middle left
NW = 8  # north-west, top left

class RoboEyesDual:
    def __init__(self, left_address=0x3C, right_address=0x3D):
        i2c = busio.I2C(board.SCL, board.SDA)

        # Create the displays with their actual dimensions
        self.display_left = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=left_address)
        self.display_right = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=right_address)

        # Set screen dimensions for drawing canvas (rotated 90 degrees)
        self.screen_width = 64
        self.screen_height = 128
        self.frame_interval = 20
        self.fps_timer = time.time() * 1000
        
        # Mood and expression controls
        self.tired = False
        self.angry = False
        self.happy = False
        self.love = False
        self.qr = False  # New flag for QR mode
        self.curious = False
        self.eye_l_open = False
        self.eye_r_open = False
        
        # Eye geometry - LEFT
        self.eye_l_width_default = 60
        self.eye_l_height_default = 100
        self.eye_l_width_current = self.eye_l_width_default
        self.eye_l_height_current = 1  # Start with closed eye
        self.eye_l_width_next = self.eye_l_width_default
        self.eye_l_height_next = self.eye_l_height_default
        self.eye_l_height_offset = 0
        self.eye_l_border_radius_default = 10
        self.eye_l_border_radius_current = self.eye_l_border_radius_default
        self.eye_l_border_radius_next = self.eye_l_border_radius_default
        
        # Eye geometry - RIGHT
        self.eye_r_width_default = self.eye_l_width_default
        self.eye_r_height_default = self.eye_l_height_default
        self.eye_r_width_current = self.eye_r_width_default
        self.eye_r_height_current = 1  # Start with closed eye
        self.eye_r_width_next = self.eye_r_width_default
        self.eye_r_height_next = self.eye_r_height_default
        self.eye_r_height_offset = 0
        self.eye_r_border_radius_default = 10
        self.eye_r_border_radius_current = self.eye_r_border_radius_default
        self.eye_r_border_radius_next = self.eye_r_border_radius_default
        
        # Eye coordinates - centered
        self.eye_l_x_default = (self.screen_width - self.eye_l_width_default) // 2
        self.eye_l_y_default = (self.screen_height - self.eye_l_height_default) // 2
        self.eye_l_x = self.eye_l_x_default
        self.eye_l_y = self.eye_l_y_default
        self.eye_l_x_next = self.eye_l_x
        self.eye_l_y_next = self.eye_l_y
        
        self.eye_r_x_default = (self.screen_width - self.eye_r_width_default) // 2
        self.eye_r_y_default = (self.screen_height - self.eye_r_height_default) // 2
        self.eye_r_x = self.eye_r_x_default
        self.eye_r_y = self.eye_r_y_default
        self.eye_r_x_next = self.eye_r_x
        self.eye_r_y_next = self.eye_r_y
        
        # Eyelid parameters
        self.eyelids_height_max = self.eye_l_height_default // 2
        self.eyelids_tired_height = 0
        self.eyelids_tired_height_next = 0
        self.eyelids_angry_height = 0
        self.eyelids_angry_height_next = 0
        self.eyelids_happy_bottom_offset_max = (self.eye_l_height_default // 2) + 3
        self.eyelids_happy_bottom_offset = 0
        self.eyelids_happy_bottom_offset_next = 0
        
        # Animations
        self.h_flicker = False
        self.h_flicker_alternate = False
        self.h_flicker_amplitude = 2
        self.v_flicker = False
        self.v_flicker_alternate = False
        self.v_flicker_amplitude = 10
        
        self.autoblinker = False
        self.blink_interval = 0.5
        self.blink_interval_variation = 4
        self.blink_timer = time.time()
        
        self.idle = False
        self.idle_interval = 1
        self.idle_interval_variation = 3
        self.idle_animation_timer = time.time()
        
        self.confused = False
        self.confused_animation_timer = time.time()
        self.confused_animation_duration = 0.5
        self.confused_toggle = True
        
        self.laugh = False
        self.laugh_animation_timer = time.time()
        self.laugh_animation_duration = 0.5
        self.laugh_toggle = True
        
        # Heart animation parameters
        self.heart_animation_angle = 0
        self.heart_animation_speed = 0.5  # Radians per frame for ~1.5s cycle
        
        # QR code parameters
        self.qr_data = None  # Stores the device ID for QR code
        

    def begin(self, width, height, frame_rate):
        """Initialize RoboEyes with screen parameters"""
        self.screen_width = height
        self.screen_height = width
        self.display_left.fill(0)
        self.display_left.show()
        self.display_right.fill(0)
        self.display_right.show()
        self.eye_l_height_current = 1
        self.eye_r_height_current = 1
        self.set_framerate(frame_rate)
    
    def update(self):
        """Update the display with frame rate limiting"""
        current_time = time.time() * 1000
        if current_time - self.fps_timer >= self.frame_interval:
            self.draw_eyes()
            self.fps_timer = current_time
    
    def set_framerate(self, fps):
        """Set the frame rate"""
        self.frame_interval = 1000 / fps
    
    def set_width(self, left_eye, right_eye):
        """Set eye widths"""
        self.eye_l_width_next = left_eye
        self.eye_r_width_next = right_eye
        self.eye_l_width_default = left_eye
        self.eye_r_width_default = right_eye
    
    def set_height(self, left_eye, right_eye):
        """Set eye heights"""
        self.eye_l_height_next = left_eye
        self.eye_r_height_next = right_eye
        self.eye_l_height_default = left_eye
        self.eye_r_height_default = right_eye
    
    def set_border_radius(self, left_eye, right_eye):
        """Set border radius for eyes"""
        self.eye_l_border_radius_next = left_eye
        self.eye_r_border_radius_next = right_eye
        self.eye_l_border_radius_default = left_eye
        self.eye_r_border_radius_default = right_eye
    
    def set_mood(self, mood):
        """Set mood expression"""
        if mood == TIRED:
            self.tired = True
            self.angry = False
            self.happy = False
            self.love = False
            self.qr = False
        elif mood == ANGRY:
            self.tired = False
            self.angry = True
            self.happy = False
            self.love = False
            self.qr = False
        elif mood == HAPPY:
            self.tired = False
            self.angry = False
            self.happy = True
            self.love = False
            self.qr = False
        elif mood == LOVE:
            self.tired = False
            self.angry = False
            self.happy = False
            self.love = True
            self.qr = False
        elif mood == QR:
            self.tired = False
            self.angry = False
            self.happy = False
            self.love = False
            self.qr = True
        else:
            self.tired = False
            self.angry = False
            self.happy = False
            self.love = False
            self.qr = False
    
    def set_position(self, position):
        """Set predefined position for both eyes"""
        offset_x = int(self.screen_width * 0.3)
        offset_y = int(self.screen_height * 0.2)
        
        if position == N:
            self.eye_l_x_next = self.eye_l_x_default
            self.eye_l_y_next = self.eye_l_y_default - offset_y
            self.eye_r_x_next = self.eye_r_x_default
            self.eye_r_y_next = self.eye_r_y_default - offset_y
        elif position == NE:
            self.eye_l_x_next = self.eye_l_x_default + offset_x
            self.eye_l_y_next = self.eye_l_y_default - offset_y
            self.eye_r_x_next = self.eye_r_x_default + offset_x
            self.eye_r_y_next = self.eye_r_y_default - offset_y
        elif position == E:
            self.eye_l_x_next = self.eye_l_x_default + offset_x
            self.eye_l_y_next = self.eye_l_y_default
            self.eye_r_x_next = self.eye_r_x_default + offset_x
            self.eye_r_y_next = self.eye_r_y_default
        elif position == SE:
            self.eye_l_x_next = self.eye_l_x_default + offset_x
            self.eye_l_y_next = self.eye_l_y_default + offset_y
            self.eye_r_x_next = self.eye_r_x_default + offset_x
            self.eye_r_y_next = self.eye_r_y_default + offset_y
        elif position == S:
            self.eye_l_x_next = self.eye_l_x_default
            self.eye_l_y_next = self.eye_l_y_default + offset_y
            self.eye_r_x_next = self.eye_r_x_default
            self.eye_r_y_next = self.eye_r_y_default + offset_y
        elif position == SW:
            self.eye_l_x_next = self.eye_l_x_default - offset_x
            self.eye_l_y_next = self.eye_l_y_default + offset_y
            self.eye_r_x_next = self.eye_r_x_default - offset_x
            self.eye_r_y_next = self.eye_r_y_default + offset_y
        elif position == W:
            self.eye_l_x_next = self.eye_l_x_default - offset_x
            self.eye_l_y_next = self.eye_l_y_default
            self.eye_r_x_next = self.eye_r_x_default - offset_x
            self.eye_r_y_next = self.eye_r_y_default
        elif position == NW:
            self.eye_l_x_next = self.eye_l_x_default - offset_x
            self.eye_l_y_next = self.eye_l_y_default - offset_y
            self.eye_r_x_next = self.eye_r_x_default - offset_x
            self.eye_r_y_next = self.eye_r_y_default - offset_y
        else:
            self.eye_l_x_next = self.eye_l_x_default
            self.eye_l_y_next = self.eye_l_y_default
            self.eye_r_x_next = self.eye_r_x_default
            self.eye_r_y_next = self.eye_r_y_default
    
    def set_autoblinker(self, active, interval=1, variation=4):
        """Set automated eye blinking"""
        self.autoblinker = active
        self.blink_interval = interval
        self.blink_interval_variation = variation
    
    def set_idle_mode(self, active, interval=1, variation=3):
        """Set idle mode"""
        self.idle = active
        self.idle_interval = interval
        self.idle_interval_variation = variation
    
    def set_curiosity(self, curious_bit):
        """Set curious mode"""
        self.curious = curious_bit
    
    def set_h_flicker(self, flicker_bit, amplitude=2):
        """Set horizontal flickering"""
        self.h_flicker = flicker_bit
        self.h_flicker_amplitude = amplitude
    
    def set_v_flicker(self, flicker_bit, amplitude=10):
        """Set vertical flickering"""
        self.v_flicker = flicker_bit
        self.v_flicker_amplitude = amplitude
    
    def get_screen_constraint_x(self):
        """Returns the max x position for each eye"""
        return self.screen_width - max(self.eye_l_width_default, self.eye_r_width_default)
    
    def get_screen_constraint_y(self):
        """Returns the max y position for each eye"""
        return self.screen_height - max(self.eye_l_height_default, self.eye_r_height_default)
    
    def close(self, left=True, right=True):
        """Close eye(s)"""
        if left:
            self.eye_l_height_next = 0
            self.eye_l_open = False
        if right:
            self.eye_r_height_next = 0
            self.eye_r_open = False
    
    def open(self, left=True, right=True):
        """Open eye(s)"""
        if left:
            self.eye_l_open = True
        if right:
            self.eye_r_open = True
    
    def blink(self, left=True, right=True):
        """Trigger blink animation"""
        self.close(left, right)
        self.open(left, right)
    
    def anim_confused(self):
        """Play confused animation"""
        self.confused = True
    
    def anim_laugh(self):
        """Play laugh animation"""
        self.laugh = True
    
    def _draw_rounded_rectangle(self, draw, xy, radius, fill=255):
        """Draw a rounded rectangle"""
        x0, y0, x1, y1 = xy
        # Ensure y1 >= y0 to prevent bottom ellipses crossing top
        y1 = max(y0, y1)
        draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
        draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
        diameter = radius * 2
        draw.ellipse([x0, y0, x0 + diameter, y0 + diameter], fill=fill)
        draw.ellipse([x1 - diameter, y0, x1, y0 + diameter], fill=fill)
        draw.ellipse([x0, y1 - diameter, x0 + diameter, y1], fill=fill)
        draw.ellipse([x1 - diameter, y1 - diameter, x1, y1], fill=fill)
    
    def _draw_heart(self, draw, x, y, size, fill=255, width_scale=1.0):
        """Draw a filled heart at position x, y with given size and width scaling"""
        points = []
        for t in range(0, 628):  # 0 to 2π in steps of 0.01
            t_rad = t / 100  # Convert to radians
            x_val = 16 * pow(sin(t_rad), 3)
            y_val = 16 * cos(t_rad) - 5 * cos(2 * t_rad) - 2 * cos(3 * t_rad) - cos(4 * t_rad)
            # Apply width scaling for rotation effect
            scaled_x = x_val * width_scale
            points.append((x + int(scaled_x * size / 16), y - int(y_val * size / 16)))
        draw.polygon(points, fill=fill)
    
    def _draw_qr_code(self, draw, qr_data, x, y, size):
        """Draw a QR code on the given draw object at position x, y with specified size"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size // 21,  # Scale to fit 21x21 QR code within size
            border=0
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="white", back_color="black").convert('1')
        # Resize to fit within display
        qr_img = qr_img.resize((size, size), Image.NEAREST)
        draw.bitmap((x, y), qr_img, fill=255)
    
    def draw_eyes(self):
        """Draw the eyes, hearts, or QR codes on separate displays"""
        # Create images for drawing
        image_left = Image.new('1', (self.screen_width, self.screen_height), 0)
        draw_left = ImageDraw.Draw(image_left)
        image_right = Image.new('1', (self.screen_width, self.screen_height), 0)
        draw_right = ImageDraw.Draw(image_right)
        
        if self.qr and self.qr_data:
            # Draw QR codes centered on both displays
            qr_size = min(self.screen_width, self.screen_height)   # Leave 5-pixel border
            qr_x = (self.screen_width - qr_size) // 2
            qr_y = (self.screen_height - qr_size) // 2
            self._draw_qr_code(draw_left, self.qr_data, qr_x, qr_y, qr_size)
            self._draw_qr_code(draw_right, self.qr_data, qr_x, qr_y, qr_size)
        
        elif self.love:
            # Update heart animation angle
            self.heart_animation_angle = (self.heart_animation_angle + self.heart_animation_speed) % (2 * 3.14159)
            width_scale = abs(cos(self.heart_animation_angle))
            bounce_offset = 10 * sin(self.heart_animation_angle)  # ±5 pixel bounce
            
            # Draw animated hearts with bounce
            heart_size = 30  # Adjusted for ~60x60 pixel heart
            self._draw_heart(draw_left, self.eye_l_x + self.eye_l_width_default // 2, 
                           self.eye_l_y + heart_size + int(bounce_offset), 
                           heart_size, fill=255, width_scale=width_scale)
            self._draw_heart(draw_right, self.eye_r_x + self.eye_r_width_default // 2, 
                           self.eye_r_y + heart_size + int(bounce_offset), 
                           heart_size, fill=255, width_scale=width_scale)
        
        else:
            if self.curious:
                if self.eye_l_x < self.eye_l_x_default:
                    self.eye_l_height_offset = 8
                else:
                    self.eye_l_height_offset = 0
                if self.eye_r_x > self.eye_r_x_default:
                    self.eye_r_height_offset = 8
                else:
                    self.eye_r_height_offset = 0
            else:
                self.eye_l_height_offset = 0
                self.eye_r_height_offset = 0
            
            # Update height with fast transition
            self.eye_l_height_current = (3 * (self.eye_l_height_next + self.eye_l_height_offset) + self.eye_l_height_current) // 4
            self.eye_r_height_current = (3 * (self.eye_r_height_next + self.eye_r_height_offset) + self.eye_r_height_current) // 4
            
            # Adjust y-position with clamped height to prevent excessive shift
            effective_l_height = max(self.eye_l_height_current, 10)
            effective_r_height = max(self.eye_r_height_current, 10)
            self.eye_l_y = self.eye_l_y_default + (self.eye_l_height_default - effective_l_height) // 2
            self.eye_r_y = self.eye_r_y_default + (self.eye_r_height_default - effective_r_height) // 2
            self.eye_l_y -= self.eye_l_height_offset // 2
            self.eye_r_y -= self.eye_r_height_offset // 2
            
            # Ensure eyes open when height is near closed
            if self.eye_l_open and self.eye_l_height_current <= 1 + self.eye_l_height_offset:
                self.eye_l_height_next = self.eye_l_height_default
            if self.eye_r_open and self.eye_r_height_current <= 1 + self.eye_r_height_offset:
                self.eye_r_height_next = self.eye_r_height_default
            
            # Keep width and border radius constant
            self.eye_l_width_current = self.eye_l_width_default
            self.eye_r_width_current = self.eye_r_width_default
            self.eye_l_border_radius_current = self.eye_l_border_radius_default
            self.eye_r_border_radius_current = self.eye_r_border_radius_default
            
            # Update position with smoothing
            self.eye_l_x = (self.eye_l_x + self.eye_l_x_next) // 2
            self.eye_l_y = (self.eye_l_y + self.eye_l_y_next) // 2
            self.eye_r_x = (self.eye_r_x + self.eye_r_x_next) // 2
            self.eye_r_y = (self.eye_r_y + self.eye_r_y_next) // 2
            
            current_time = time.time()
            
            # Handle autoblinking
            if self.autoblinker and current_time >= self.blink_timer:
                self.blink()
                self.blink_timer = current_time + self.blink_interval + random.random() * self.blink_interval_variation
            
            # Handle laugh animation
            if self.laugh:
                if self.laugh_toggle:
                    self.set_v_flicker(True, 5)
                    self.laugh_animation_timer = current_time
                    self.laugh_toggle = False
                elif current_time >= self.laugh_animation_timer + self.laugh_animation_duration:
                    self.set_v_flicker(False, 0)
                    self.laugh_toggle = True
                    self.laugh = False
            
            # Handle confused animation
            if self.confused:
                if self.confused_toggle:
                    self.set_h_flicker(True, 10)
                    self.confused_animation_timer = current_time
                    self.confused_toggle = False
                elif current_time >= self.confused_animation_timer + self.confused_animation_duration:
                    self.set_h_flicker(False, 0)
                    self.confused_toggle = True
                    self.confused = False
            
            # Handle idle mode
            if self.idle and current_time >= self.idle_animation_timer:
                max_offset = int(self.screen_width * 0.25)
                self.eye_l_x_next = self.eye_l_x_default + random.randint(-max_offset, max_offset)
                self.eye_l_y_next = self.eye_l_y_default + random.randint(-max_offset, max_offset)
                self.eye_r_x_next = self.eye_r_x_default + random.randint(-max_offset, max_offset)
                self.eye_r_y_next = self.eye_r_y_default + random.randint(-max_offset, max_offset)
                
                self.eye_l_x_next = max(5, min(self.eye_l_x_next, self.screen_width - self.eye_l_width_default - 5))
                self.eye_l_y_next = max(5, min(self.eye_l_y_next, self.screen_height - self.eye_l_height_current - 5))
                self.eye_r_x_next = max(5, min(self.eye_r_x_next, self.screen_width - self.eye_r_width_default - 5))
                self.eye_r_y_next = max(5, min(self.eye_r_y_next, self.screen_height - self.eye_r_height_current - 5))
                
                self.idle_animation_timer = current_time + self.idle_interval + random.random() * self.idle_interval_variation
            
            # Apply horizontal flicker
            if self.h_flicker:
                if self.h_flicker_alternate:
                    self.eye_l_x += self.h_flicker_amplitude
                    self.eye_r_x += self.h_flicker_amplitude
                else:
                    self.eye_l_x -= self.h_flicker_amplitude
                    self.eye_r_x -= self.h_flicker_amplitude
                self.h_flicker_alternate = not self.h_flicker_alternate
            
            # Apply vertical flicker
            if self.v_flicker:
                if self.v_flicker_alternate:
                    self.eye_l_y += self.v_flicker_amplitude
                    self.eye_r_y += self.v_flicker_amplitude
                else:
                    self.eye_l_y -= self.v_flicker_amplitude
                    self.eye_r_y -= self.v_flicker_amplitude
                self.v_flicker_alternate = not self.v_flicker_alternate
            
            # Draw eyes only if height is sufficient
            if self.eye_l_height_current > 1:
                self._draw_rounded_rectangle(draw_left, 
                    [self.eye_l_x, self.eye_l_y, 
                     self.eye_l_x + self.eye_l_width_default, 
                     self.eye_l_y + self.eye_l_height_current], 
                    self.eye_l_border_radius_default, 
                    fill=255)
            
            if self.eye_r_height_current > 1:
                self._draw_rounded_rectangle(draw_right, 
                    [self.eye_r_x, self.eye_r_y, 
                     self.eye_r_x + self.eye_r_width_default, 
                     self.eye_r_y + self.eye_r_height_current], 
                    self.eye_r_border_radius_default, 
                    fill=255)
            
            # Update eyelid parameters
            if self.tired:
                self.eyelids_tired_height_next = self.eye_l_height_current // 2 if self.eye_l_height_current > 2 else 0
                self.eyelids_angry_height_next = 0
            else:
                self.eyelids_tired_height_next = 0
            
            if self.angry:
                self.eyelids_angry_height_next = self.eye_l_height_current // 2 if self.eye_l_height_current > 2 else 0
                self.eyelids_tired_height_next = 0
            else:
                self.eyelids_angry_height_next = 0
            
            if self.happy:
                self.eyelids_happy_bottom_offset_next = self.eye_l_height_current // 1.5 if self.eye_l_height_current > 2 else 0
            else:
                self.eyelids_happy_bottom_offset_next = 0
            
            self.eyelids_tired_height = (self.eyelids_tired_height + self.eyelids_tired_height_next) // 2
            self.eyelids_angry_height = (self.eyelids_angry_height + self.eyelids_angry_height_next) // 2
            self.eyelids_happy_bottom_offset = (self.eyelids_happy_bottom_offset + self.eyelids_happy_bottom_offset_next) // 2
            
            # Draw eyelids
            if self.eyelids_tired_height > 0:
                draw_left.polygon([(self.eye_l_x, self.eye_l_y - 1),
                                 (self.eye_l_x + self.eye_l_width_default, self.eye_l_y - 1),
                                 (self.eye_l_x, self.eye_l_y + self.eyelids_tired_height - 1)],
                                fill=0)
                draw_right.polygon([(self.eye_r_x, self.eye_r_y - 1),
                                  (self.eye_r_x + self.eye_r_width_default, self.eye_r_y - 1),
                                  (self.eye_r_x + self.eye_r_width_default, self.eye_r_y + self.eyelids_tired_height - 1)],
                                 fill=0)
            
            if self.eyelids_angry_height > 0:
                draw_left.polygon([(self.eye_l_x, self.eye_l_y - 1),
                                 (self.eye_l_x + self.eye_l_width_default, self.eye_l_y - 1),
                                 (self.eye_l_x + self.eye_l_width_default, self.eye_l_y + self.eyelids_angry_height - 1)],
                                fill=0)
                draw_right.polygon([(self.eye_r_x, self.eye_r_y - 1),
                                  (self.eye_r_x + self.eye_r_width_default, self.eye_r_y - 1),
                                  (self.eye_r_x, self.eye_r_y + self.eyelids_angry_height - 1)],
                                 fill=0)
            
            if self.eyelids_happy_bottom_offset > 0:
                happy_y_l = self.eye_l_y + self.eye_l_height_current - self.eyelids_happy_bottom_offset + 1
                self._draw_rounded_rectangle(draw_left,
                    [self.eye_l_x - 1, happy_y_l,
                     self.eye_l_x + self.eye_l_width_default + 2,
                     happy_y_l + self.eye_l_height_default],
                    self.eye_l_border_radius_default,
                    fill=0)
                happy_y_r = self.eye_r_y + self.eye_r_height_current - self.eyelids_happy_bottom_offset + 1
                self._draw_rounded_rectangle(draw_right,
                    [self.eye_r_x - 1, happy_y_r,
                     self.eye_r_x + self.eye_r_width_default + 2,
                     happy_y_r + self.eye_r_height_default],
                    self.eye_r_border_radius_default,
                    fill=0)
        
        # Rotate and display images
        rotated_left = image_left.rotate(-90, expand=True)
        rotated_right = image_right.rotate(-90, expand=True)
        self.display_left.image(rotated_left)
        self.display_left.show()
        self.display_right.image(rotated_right)
        self.display_right.show()
    
    def Happy(self, stop_event=None):
        """Display Happy mood"""
        self.set_mood(HAPPY)
        self.set_position(N)
        self.set_autoblinker(True, 3, 0.5)
        self.set_idle_mode(False)
        self.set_curiosity(False)
        self.anim_laugh()
        while not (stop_event and stop_event.is_set()):
            self.update()
            time.sleep(0.01)
    
    def Default(self, stop_event=None):
        """Display Default mood"""
        self.set_mood(DEFAULT)
        self.set_position(0)
        self.set_autoblinker(True, 5, 0.5)
        self.set_idle_mode(True, 2, 2)
        self.set_curiosity(False)
        while not (stop_event and stop_event.is_set()):
            self.update()
            time.sleep(0.01)
    
    def Tired(self, stop_event=None):
        """Display Tired mood"""
        self.set_mood(TIRED)
        self.set_position(S)
        self.set_autoblinker(True, 3, 0.5)
        self.set_idle_mode(False)
        self.set_curiosity(False)
        while not (stop_event and stop_event.is_set()):
            self.update()
            time.sleep(0.01)
    
    def Angry(self, stop_event=None):
        """Display Angry mood"""
        self.set_mood(ANGRY)
        self.set_autoblinker(True, 4, 0.5)
        self.set_idle_mode(False)
        self.set_curiosity(False)
        self.anim_confused()
        while not (stop_event and stop_event.is_set()):
            self.update()
            time.sleep(0.01)
    
    def Love(self, stop_event=None):
        """Display Love mood with animated hearts"""
        self.set_mood(LOVE)
        self.set_position(0)
        self.set_autoblinker(False)
        self.set_idle_mode(False)
        self.set_curiosity(False)
        while not (stop_event and stop_event.is_set()):
            self.update()
            time.sleep(0.01)
    
    def QR(self, qr_data, stop_event=None):
        """Display QR codes encoding the provided data on both eyes"""
        self.qr_data = str(qr_data)  # Use the full input string directly
        if not self.qr_data:
            raise ValueError("QR data is empty")
        self.set_mood(QR)
        self.set_autoblinker(False)
        self.set_idle_mode(False)
        self.set_curiosity(False)
        while not (stop_event and stop_event.is_set()):
            self.update()
            time.sleep(0.01)
        # Clear QR data and displays when stopping
        self.qr_data = None
        self.display_left.fill(0)
        self.display_left.show()
        self.display_right.fill(0)
        self.display_right.show()

if __name__ == "__main__":
    # Create RoboEyes instance
    eyes = RoboEyesDual(left_address=0x3D, right_address=0x3C)
    
    # Initialize with screen size and frame rate
    eyes.begin(128, 64, 50)
    
    # Main loop for testing
    try:
        # ~ # Test QR mode with a sample 6-digit device ID
        # ~ stop_event = threading.Event()
        # ~ qr_thread = threading.Thread(target=eyes.QR, args=(123456, stop_event))
        # ~ qr_thread.start()
        # ~ time.sleep(10)  # Display QR for 5 seconds
        # ~ stop_event.set()
        # ~ qr_thread.join()
        
        # Test other moods
        moods = [eyes.Default, eyes.Happy, eyes.Tired, eyes.Angry, eyes.Love, eyes.QR]
        # ~ eyes.QR(-OUukosDkZuvHboo-qX5)
        
        # Test QR mode with the user ID
        # ~ stop_event = threading.Event()
        # ~ qr_thread = threading.Thread(target=eyes.QR, args=("-OUukosDkZuvHboo-qX5", stop_event))
        # ~ qr_thread.start()
        # ~ time.sleep(10)  # Display QR for 10 seconds
        # ~ stop_event.set()
        # ~ qr_thread.join()
        
        eyes.Default()
        # ~ for mood in moods:
            # ~ stop_event = threading.Event()
            # ~ mood_thread = threading.Thread(target=mood, args=(stop_event,))
            # ~ mood_thread.start()
            # ~ time.sleep(3)  # Display each mood for 3 seconds
            # ~ stop_event.set()
            # ~ mood_thread.join()
    
    except KeyboardInterrupt:
        eyes.display_left.fill(0)
        eyes.display_left.show()
        eyes.display_right.fill(0)
        eyes.display_right.show()
        print("\nRoboEyes stopped")

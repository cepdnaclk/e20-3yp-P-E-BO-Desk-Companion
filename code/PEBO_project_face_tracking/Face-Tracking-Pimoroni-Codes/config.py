# Config.py file for face-track.py ver 0.94

# Display Settings
debug = True        # Set to False for no data display
verbose = True      # Add extra detailed information
show_fps = True     # show frames per second processing speed
window_on = True   # Set to True displays opencv windows (GUI desktop reqd)
diff_window_on = False  # Show OpenCV image difference window
thresh_window_on = False  # Show OpenCV image Threshold window
CIRCLE_SIZE = 8     # diameter of circle to show motion location in window
LINE_THICKNESS = 2  # thickness of bounding line in pixels
WINDOW_BIGGER = 1   # Resize multiplier for OpenCV Status Window
                    # if window_on=True then makes opencv window bigger
                    # Note if the window is larger than 1 then a reduced frame rate will occur

GPIOZERO_ON = False  # False = use pipan servo driver, True = gpiozero pan/tilt servo driver
GPIOZERO_PAN_PIN = 17
GPIOZERO_TILT_PIN = 23
                   
# Camera Settings
# ---------------
WEBCAM = False         # Default = False False=PiCamera True=USB WebCamera

# Web Camera Settings
WEBCAM_SRC = 0         # Default= 0   USB opencv connection number
WEBCAM_WIDTH = 640     # Default= 320 USB Webcam Image width
WEBCAM_HEIGHT = 480    # Default= 240 USB Webcam Image height
WEBCAM_HFLIP = True    # Default= False USB Webcam flip image horizontally
WEBCAM_VFLIP = False   # Default= False USB Webcam flip image vertically

# Camera Settings
CAMERA_WIDTH = 320
CAMERA_HEIGHT = 200
CAMERA_HFLIP = False
CAMERA_VFLIP = True
CAMERA_ROTATION = 0
CAMERA_FRAMERATE = 15

# FPS counter
FRAME_COUNTER = 1000  # Used for display of FPS (frames/second)

# Pan Tilt Settings
pan_servo_delay = .15
servo_max_x_deg = 180
servo_max_y_deg = 180
servo_home_xy = (130, 110)

pan_start_x = 40   # Initial x start position
pan_start_y = 20  # initial y start position

# Bounds checking for pan/tilt Movements.

pan_max_left = 0
pan_max_right = 180
pan_max_top = 30
pan_max_bottom = 70
pan_move_x = int(CAMERA_WIDTH / 8)  # Amount to pan left/right in search mode
pan_move_y = int(CAMERA_HEIGHT / 5) # Amount to pan up/down in search mode

timer_motion = 3      # seconds delay after no motion before looking for face
timer_face = 2        # seconds delay after no face found before starting pan search
timer_pan = 1         # seconds delay between pan search repositioning movements

# OpenCV haarcascade Settings
# default face frontal detection
fface1_haar_path = '/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml'
# frontal face pattern detection
fface2_haar_path = '/usr/share/opencv/haarcascades/haarcascade_frontalface_alt2.xml'
# side face pattern detection
pface1_haar_path = '/usr/share/opencv/haarcascades/haarcascade_profileface.xml'

# OpenCV Motion Tracking Settings
MIN_AREA = 2000       # sq pixels - exclude all motion contours less than or equal to this Area
THRESHOLD_SENSITIVITY = 25
BLUR_SIZE = 10

from interaction.touch_sensor import detect_continuous_touch
from facetrack.face_tracking import start_face_tracking
import threading
import time

# Global flag to control the main program state
is_running = False

def main_program():
    """
    Main program that runs when started and stops when triggered by touch.
    """
    global is_running
    print("Main program is running (face tracking)...")
    
    try:
        # Start face tracking
        start_face_tracking()
    except KeyboardInterrupt:
        print("Main program interrupted")
    finally:
        print("Main program cleanup")

def monitor_touch():
    """
    Monitors the touch sensor to start or stop the main program.
    """
    global is_running

    try:
        while True:
            if detect_continuous_touch(3):
                if not is_running:
                    print("Starting the face tracking...")
                    is_running = True
                    # Run the main program (face tracking) in a separate thread
                    tracking_thread = threading.Thread(target=main_program)
                    tracking_thread.daemon = True  # Allows program to exit even if thread is running
                    tracking_thread.start()
                else:
                    print("Stopping the face tracking...")
                    is_running = False
                    break  # Exit the monitoring loop
            
            time.sleep(0.1)  # Prevent excessive CPU usage

    except KeyboardInterrupt:
        print("Touch monitoring stopped")
    finally:
        print("Cleaning up GPIO")
        GPIO.cleanup()

# Start touch monitoring
monitor_touch()

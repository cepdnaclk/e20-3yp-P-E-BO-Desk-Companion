# voice_wake.py
import time
import threading
import asyncio

import speech_recognition as sr

# add M2_DEMO path
import os, sys
BASE = os.path.dirname(__file__)
sys.path.append(os.path.join(BASE, "code", "M2_DEMO"))

from face_tracking import start_tracking_once
from user_identitifer import capture_and_upload, recognize_user
from inter_device_communication_send_audio import main as comm_main
from assistant import speak_text


recognizer = sr.Recognizer()
mic = sr.Microphone()


def face_sequence():
    """Track face → upload/capture → identify → greet once."""
    while True:
        start_tracking_once()
        capture_and_upload()
        res = recognize_user()
        if res.get("match"):
            # user_<name>.jpg → name
            name = res["reference_image"].split("_",1)[1].rsplit(".",1)[0]
            greeting = f"Hello {name}, welcome back!"
            print(greeting)
            asyncio.run(speak_text(greeting))
            break
        else:
            print("Unknown user, retrying tracking...")


def callback(recognizer, audio):
    """Background callback: runs on each phrase."""
    try:
        # try offline first
        text = recognizer.recognize_sphinx(audio).lower()
    except sr.RequestError:
        # Sphinx engine not available
        return
    except sr.UnknownValueError:
        # silence or no speech
        return

    print(f"[wake heard] {text!r}")
    if "hey pebo" in text:
        threading.Thread(target=face_sequence, daemon=True).start()
    elif "send msg" in text:
        threading.Thread(target=comm_main, daemon=True).start()


def main():
    # 1) mic warm‑up
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
    # 2) start listening in background
    stop_listening = recognizer.listen_in_background(mic, callback)
    print(">> Listening for ‘hey pebo’ or ‘send msg’ (offline via PocketSphinx)...")

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        stop_listening()
        print("\nShutting down voice wake.")


if __name__ == "__main__":
    main()

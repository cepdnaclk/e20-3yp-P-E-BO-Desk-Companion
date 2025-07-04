import os
import subprocess
import urllib.request
import shutil
import stat
import asyncio
import edge_tts
import pygame
import tempfile
import yt_dlp
import RPi.GPIO as GPIO
import time
import threading
import signal

# Global variables
stop_music_flag = False
ffplay_process = None

def detect_double_tap(max_interval=0.5, min_interval=0.1):
    """
    Detects a double tap on the touch sensor within the specified time window.
    Sets stop_music_flag to True if a double tap is detected.

    Args:
        max_interval (float): Maximum time (seconds) between two taps to count as a double tap.
        min_interval (float): Minimum time (seconds) between taps to avoid debounce noise.
    """
    global stop_music_flag
    first_tap_time = None

    while not stop_music_flag:
        if GPIO.input(TOUCH_PIN) == GPIO.HIGH:
            if first_tap_time is None:
                first_tap_time = time.time()
                print("First tap detected")
                while GPIO.input(TOUCH_PIN) == GPIO.HIGH:
                    time.sleep(0.01)
                print("First tap released")
            else:
                current_time = time.time()
                time_since_first_tap = current_time - first_tap_time
                if min_interval <= time_since_first_tap <= max_interval:
                    print("Double tap detected! Stopping music...")
                    stop_music_flag = True
                    return
                else:
                    print("Second tap outside valid interval, resetting")
                    first_tap_time = current_time
                    while GPIO.input(TOUCH_PIN) == GPIO.HIGH:
                        time.sleep(0.01)
                    print("Second tap released")
            time.sleep(0.1)
        else:
            if first_tap_time and (time.time() - first_tap_time) > max_interval:
                print("First tap timed out, resetting")
                first_tap_time = None
            time.sleep(0.01)

async def play_music(song="Perfect Ed Sheeran", controller=None):
    """
    Search YouTube for a song and play it using yt-dlp and ffplay, with voice feedback.
    Stops playback if a double tap is detected on the touch sensor.
    
    Args:
        song (str): Song name to search for on YouTube.
        controller: RobotController instance for robot emotions (optional).
    
    Returns:
        bool: True if playback was successful, False otherwise.
    """
    global stop_music_flag, ffplay_process
    stop_music_flag = False

    # Pin configuration for touch sensor
    TOUCH_PIN = 17
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TOUCH_PIN, GPIO.IN)

    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        ffplay_exe = "ffplay"
        if not shutil.which(ffplay_exe):
            print("Error: ffplay not found in PATH. Please install ffmpeg.")
            return False

        if controller:
            emotion_task = asyncio.to_thread(controller.happy)
        else:
            emotion_task = asyncio.sleep(0)

        voice = "en-GB-SoniaNeural"
        filename = "response.mp3"
        boosted_file = "boosted_response.mp3"
        tts = edge_tts.Communicate(f"Playing {song} now!", voice)
        await tts.save(filename)

        subprocess.run(
            ["ffmpeg", "-y", "-i", filename, "-filter:a", "volume=20dB", boosted_file],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        pygame.mixer.music.load(boosted_file)
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.25)
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        os.remove(filename)
        os.remove(boosted_file)

        print(f"Searching YouTube for '{song}'...")
        try:
            ydl_opts = {
                'default_search': 'ytsearch',
                'format': 'bestaudio',
                'noplaylist': True,
                'quiet': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{song}", download=False)
                if not info or 'entries' not in info or not info['entries']:
                    print(f"No audio URL found for '{song}'.")
                    if controller:
                        await asyncio.to_thread(controller.sad)
                        tts = edge_tts.Communicate(f"Sorry, I couldn't find {song}.", voice)
                        await tts.save(filename)
                        subprocess.run(
                            ["ffmpeg", "-y", "-i", filename, "-filter:a", "volume=20dB", boosted_file],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                        )
                        pygame.mixer.music.load(boosted_file)
                        pygame.mixer.music.set_volume(1.0)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy():
                            await asyncio.sleep(0.25)
                        pygame.mixer.music.stop()
                        pygame.mixer.music.unload()
                        os.remove(filename)
                        os.remove(boosted_file)
                    return False
                audio_url = info['entries'][0]['url']
        except Exception as e:
            print(f"yt-dlp error: {e}")
            if controller:
                await asyncio.to_thread(controller.sad)
                tts = edge_tts.Communicate(f"Error searching for {song}.", voice)
                await tts.save(filename)
                subprocess.run(
                    ["ffmpeg", "-y", "-i", filename, "-filter:a", "volume=20dB", boosted_file],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                pygame.mixer.music.load(boosted_file)
                pygame.mixer.music.set_volume(1.0)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    await asyncio.sleep(0.25)
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
                os.remove(filename)
                os.remove(boosted_file)
            return False

        print(f"Now playing: {song}")
        print(f"Audio URL: {audio_url}")

        touch_thread = threading.Thread(target=detect_double_tap, args=(0.5, 0.1))
        touch_thread.start()

        try:
            ffplay_process = subprocess.Popen(
                [ffplay_exe, "-nodisp", "-autoexit", "-loglevel", "quiet", audio_url],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            while ffplay_process.poll() is None:
                if stop_music_flag:
                    ffplay_process.terminate()
                    ffplay_process.wait()
                    print("Music stopped due to double tap detection.")
                    break
                await asyncio.sleep(0.1)
            else:
                ffplay_process.wait()

            stop_music_flag = True
            touch_thread.join()

            if stop_music_flag:
                message = "Music stopped."
            else:
                message = "Finished playing the song. Anything else?"
            
            if controller and stop_music_flag:
                emotion_task = asyncio.to_thread(controller.sad)
            elif controller:
                emotion_task = asyncio.to_thread(controller.normal)
            
            tts = edge_tts.Communicate(message, voice)
            await tts.save(filename)
            subprocess.run(
                ["ffmpeg", "-y", "-i", filename, "-filter:a", "volume=20dB", boosted_file],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            pygame.mixer.music.load(boosted_file)
            pygame.mixer.music.set_volume(1.0)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.25)
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            os.remove(filename)
            os.remove(boosted_file)
            await asyncio.gather(emotion_task, asyncio.sleep(0))
            return not stop_music_flag
        except Exception as e:
            print(f"ffplay error: {e}")
            stop_music_flag = True
            touch_thread.join()
            if controller:
                await asyncio.to_thread(controller.sad)
                tts = edge_tts.Communicate(f"Error playing {song}.", voice)
                await tts.save(filename)
                subprocess.run(
                    ["ffmpeg", "-y", "-i", filename, "-filter:a", "volume=20dB", boosted_file],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                pygame.mixer.music.load(boosted_file)
                pygame.mixer.music.set_volume(1.0)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    await asyncio.sleep(0.25)
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
                os.remove(filename)
                os.remove(boosted_file)
            return False
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(play_music("soft music"))
    except KeyboardInterrupt:
        print("Script interrupted by user.")
        stop_music_flag = True  # No global declaration needed
        if ffplay_process and ffplay_process.poll() is None:
            ffplay_process.terminate()
            ffplay_process.wait()
        GPIO.cleanup()
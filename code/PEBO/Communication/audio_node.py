# audio_node.py
import socket
import pyaudio
import threading
import time
import queue

class AudioNode:
    def __init__(self, listen_port, target_host, target_port):
        self.CHUNK = 2048
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 48000
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port
        self.audio_queue = queue.Queue(maxsize=10)
        self.audio = pyaudio.PyAudio()
        self.running = False
        self.threads = []

    def setup_audio(self):
        self.mic_stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        self.speaker_stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            output=True,
            frames_per_buffer=self.CHUNK
        )

    def send_audio(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            time.sleep(2)
            sock.connect((self.target_host, self.target_port))
            print(f"[SEND] Connected to {self.target_host}:{self.target_port}")
            while self.running:
                data = self.mic_stream.read(self.CHUNK, exception_on_overflow=False)
                sock.send(data)
        except Exception as e:
            print(f"[SEND ERROR] {e}")
        finally:
            sock.close()

    def receive_audio(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            sock.bind(('0.0.0.0', self.listen_port))
            sock.listen(1)
            print(f"[RECEIVE] Listening on {self.listen_port}")
            conn, addr = sock.accept()
            print(f"[RECEIVE] Connected from {addr}")
            while self.running:
                data = conn.recv(self.CHUNK * 2)
                if not data:
                    break
                if not self.audio_queue.full():
                    self.audio_queue.put(data)
        except Exception as e:
            print(f"[RECEIVE ERROR] {e}")
        finally:
            sock.close()

    def play_audio(self):
        while self.running:
            try:
                data = self.audio_queue.get(timeout=0.1)
                self.speaker_stream.write(data)
            except queue.Empty:
                continue

    def start(self):
        print("[AUDIO] Starting full-duplex communication")
        self.running = True
        self.setup_audio()
        self.threads = [
            threading.Thread(target=self.send_audio),
            threading.Thread(target=self.receive_audio),
            threading.Thread(target=self.play_audio)
        ]
        for t in self.threads:
            t.daemon = True
            t.start()

    def stop(self):
        print("[AUDIO] Stopping communication")
        self.running = False
        time.sleep(1)
        try:
            self.mic_stream.stop_stream()
            self.speaker_stream.stop_stream()
            self.mic_stream.close()
            self.speaker_stream.close()
            self.audio.terminate()
        except Exception as e:
            print(f"[STOP ERROR] {e}")

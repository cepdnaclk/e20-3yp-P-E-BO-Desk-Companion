import socket
import pyaudio
import threading
import time
import queue
import audioop


class AudioNode:
    def __init__(self, listen_port=8888, target_host='192.168.124.182', target_port=8889):
        self.CHUNK = 2048
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 48000
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port
        self.audio_queue = queue.Queue(maxsize=10)
        self.audio = pyaudio.PyAudio()
        self.running = True
        self.setup_audio()

    def setup_audio(self):
        self.mic_stream = self.audio.open(format=self.FORMAT, channels=self.CHANNELS,
                                          rate=self.RATE, input=True, frames_per_buffer=self.CHUNK)
        self.speaker_stream = self.audio.open(format=self.FORMAT, channels=self.CHANNELS,
                                              rate=self.RATE, output=True, frames_per_buffer=self.CHUNK)

    def send_audio(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            time.sleep(2)
            sock.connect((self.target_host, self.target_port))
            print(f"Connected to laptop at {self.target_host}:{self.target_port}")
            while self.running:
                data = self.mic_stream.read(self.CHUNK, exception_on_overflow=False)
                sock.send(data)
        except Exception as e:
            print(f"Send error: {e}")
        finally:
            sock.close()
    def send_audio(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            time.sleep(2)
            sock.connect((self.target_host, self.target_port))
            print(f"Connected to laptop at {self.target_host}:{self.target_port}")

            threshold = 500  # Adjust this value to your environment

            while self.running:
                data = self.mic_stream.read(self.CHUNK, exception_on_overflow=False)
                rms = audioop.rms(data, 2)  # 2 bytes/sample for paInt16

                # Debug: Print volume to help tune
                #Sprint(f"RMS: {rms}")

                if rms > threshold:
                    sock.send(data)
                else:
                    silence = b'\x00' * len(data)
                    sock.send(silence)

        except Exception as e:
            print(f"Send error: {e}")
        finally:
            sock.close()


    def receive_audio(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            sock.bind(('0.0.0.0', self.listen_port))
            sock.listen(1)
            print(f"Listening for laptop connection on port {self.listen_port}")
            conn, addr = sock.accept()
            print(f"Laptop connected from {addr}")
            while self.running:
                data = conn.recv(self.CHUNK * 2)
                if not data:
                    break
                if not self.audio_queue.full():
                    self.audio_queue.put(data)
        except Exception as e:
            print(f"Receive error: {e}")
        finally:
            conn.close()
            sock.close()

    def play_audio(self):
        while self.running:
            try:
                data = self.audio_queue.get(timeout=0.1)
                self.speaker_stream.write(data)
            except queue.Empty:
                continue

    def send_trigger_signal(self, ip='192.168.124.94', port=8890):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, port))
                s.sendall(b'start')
                print(f"Trigger signal sent to {ip}:{port}")
        except Exception as e:
            print(f"Failed to send trigger signal: {e}")

    def start(self):
        print("Starting Pi audio node...")
        print("Using 48kHz to match Pi Bluetooth speakers")

        self.send_trigger_signal(self.target_host, 8890)  # ✅ Trigger Device 2

        send_thread = threading.Thread(target=self.send_audio)
        receive_thread = threading.Thread(target=self.receive_audio)
        play_thread = threading.Thread(target=self.play_audio)

        send_thread.daemon = True
        receive_thread.daemon = True
        play_thread.daemon = True

        receive_thread.start()
        play_thread.start()
        send_thread.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
            self.running = False

        self.mic_stream.stop_stream()
        self.speaker_stream.stop_stream()
        self.mic_stream.close()
        self.speaker_stream.close()
        self.audio.terminate()

    

if __name__ == "__main__":
    LAPTOP_IP = "192.168.124.182"  # Replace with Device 2 IP
    node = AudioNode(listen_port=8888, target_host=LAPTOP_IP, target_port=8889)
    node.start()

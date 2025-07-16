import socket
import subprocess

TRIGGER_PORT = 8890

def wait_for_trigger():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('0.0.0.0', TRIGGER_PORT))
        s.listen(1)
        print(f"[Trigger Listener] Waiting for trigger on port {TRIGGER_PORT}...")
        conn, addr = s.accept()
        with conn:
            print(f"[Trigger Listener] Connection from {addr}")
            data = conn.recv(1024)
            if data == b'start':
                print("[Trigger Listener] Start signal received. Launching receiver...")
                subprocess.Popen(['python3', 'receiver.py'])  # Adjust path if needed

if __name__ == "__main__":
    wait_for_trigger()

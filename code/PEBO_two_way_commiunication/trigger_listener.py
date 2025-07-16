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
                #subprocess.Popen(['python', 'receiver.py'])  # Adjust path if needed
                subprocess.Popen(['python', r'c:\Users\DELL\Documents\sem5\3yp\e20-3yp-P-E-BO-Desk-Companion\code\PEBO_two_way_commiunication\receiver.py'])

if __name__ == "__main__":
    wait_for_trigger()

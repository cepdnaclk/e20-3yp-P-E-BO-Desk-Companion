import socket
import threading
import pyaudio
import wave
import os
import time
import tkinter as tk
from tkinter import messagebox

class VoiceChatApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Voice Chat Application")
        self.master.geometry("500x300")
        self.master.resizable(False, False)
        
        # Network settings
        self.host = tk.StringVar(value="")
        self.port = tk.IntVar(value=12345)
        self.connected = False
        self.socket = None
        self.connection = None
        self.address = None
        
        # Audio settings
        self.chunk = 1024
        self.sample_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.seconds = 0
        self.p = pyaudio.PyAudio()
        self.recording = False
        self.playing = False
        
        # File paths
        self.temp_dir = "temp_audio"
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        
        self.setup_ui()
    
    def setup_ui(self):
        # Connection frame
        conn_frame = tk.LabelFrame(self.master, text="Connection Settings", padx=10, pady=10)
        conn_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(conn_frame, text="IP Address:").grid(row=0, column=0, sticky="w")
        tk.Entry(conn_frame, textvariable=self.host, width=15).grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(conn_frame, text="Port:").grid(row=0, column=2, sticky="w")
        tk.Entry(conn_frame, textvariable=self.port, width=6).grid(row=0, column=3, padx=5, pady=5)
        
        self.server_btn = tk.Button(conn_frame, text="Start Server", command=self.start_server)
        self.server_btn.grid(row=0, column=4, padx=5, pady=5)
        
        self.client_btn = tk.Button(conn_frame, text="Connect", command=self.connect_to_server)
        self.client_btn.grid(row=0, column=5, padx=5, pady=5)
        
        # Voice controls frame
        voice_frame = tk.LabelFrame(self.master, text="Voice Controls", padx=10, pady=10)
        voice_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.record_btn = tk.Button(voice_frame, text="Start Recording", command=self.toggle_recording, state="disabled", height=2)
        self.record_btn.pack(fill="x", padx=20, pady=10)
        
        self.send_btn = tk.Button(voice_frame, text="Send Message", command=self.send_recording, state="disabled", height=2)
        self.send_btn.pack(fill="x", padx=20, pady=10)
        
        self.play_btn = tk.Button(voice_frame, text="Play Received Message", command=self.play_received, state="disabled", height=2)
        self.play_btn.pack(fill="x", padx=20, pady=10)
        
        # Status bar
        self.status_var = tk.StringVar(value="Not connected")
        self.status_bar = tk.Label(self.master, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill="x", side=tk.BOTTOM, padx=0, pady=0)
    
    def start_server(self):
        if not self.connected:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.bind(('', self.port.get()))
                self.socket.listen(1)
                
                self.status_var.set(f"Server started on port {self.port.get()}. Waiting for connection...")
                threading.Thread(target=self.accept_connection, daemon=True).start()
                
                self.server_btn.config(text="Stop Server", command=self.stop_connection)
                self.client_btn.config(state="disabled")
            except Exception as e:
                messagebox.showerror("Error", f"Could not start server: {str(e)}")
    
    def accept_connection(self):
        try:
            self.connection, self.address = self.socket.accept()
            self.status_var.set(f"Connected to {self.address[0]}")
            self.connected = True
            
            self.master.after(0, self.enable_voice_controls)
            
            threading.Thread(target=self.receive_messages, daemon=True).start()
        except:
            if hasattr(self, 'socket') and self.socket:
                self.socket.close()
    
    def connect_to_server(self):
        if not self.connected:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host.get(), self.port.get()))
                self.connection = self.socket
                self.status_var.set(f"Connected to {self.host.get()}")
                self.connected = True
                
                self.client_btn.config(text="Disconnect", command=self.stop_connection)
                self.server_btn.config(state="disabled")
                self.enable_voice_controls()
                
                threading.Thread(target=self.receive_messages, daemon=True).start()
            except Exception as e:
                messagebox.showerror("Error", f"Could not connect to server: {str(e)}")
    
    def stop_connection(self):
        if self.connected:
            self.connected = False
            if self.connection:
                self.connection.close()
            if self.socket:
                self.socket.close()
            
            self.status_var.set("Disconnected")
            self.server_btn.config(text="Start Server", command=self.start_server, state="normal")
            self.client_btn.config(text="Connect", command=self.connect_to_server, state="normal")
            self.disable_voice_controls()
    
    def enable_voice_controls(self):
        self.record_btn.config(state="normal")
        self.send_btn.config(state="disabled")  # Enable after recording
        self.play_btn.config(state="disabled")  # Enable when message received
    
    def disable_voice_controls(self):
        self.record_btn.config(state="disabled", text="Start Recording")
        self.send_btn.config(state="disabled")
        self.play_btn.config(state="disabled")
        self.recording = False
    
    def toggle_recording(self):
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        self.recording = True
        self.record_btn.config(text="Stop Recording")
        self.send_btn.config(state="disabled")
        self.status_var.set("Recording... Speak now")
        
        self.frames = []
        self.stream = self.p.open(
            format=self.sample_format,
            channels=self.channels,
            rate=self.rate,
            frames_per_buffer=self.chunk,
            input=True
        )
        
        threading.Thread(target=self.record_audio, daemon=True).start()
    
    def record_audio(self):
        while self.recording:
            try:
                data = self.stream.read(self.chunk)
                self.frames.append(data)
            except:
                break
    
    def stop_recording(self):
        self.recording = False
        self.stream.stop_stream()
        self.stream.close()
        
        self.output_filename = os.path.join(self.temp_dir, f"outgoing_{int(time.time())}.wav")
        
        # Save the recorded data as a WAV file
        wf = wave.open(self.output_filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.p.get_sample_size(self.sample_format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        
        self.record_btn.config(text="Start Recording")
        self.send_btn.config(state="normal")
        self.status_var.set("Recording saved. Ready to send.")
    
    def send_recording(self):
        if not self.connected or not hasattr(self, 'output_filename'):
            return
        
        try:
            # Get file size
            file_size = os.path.getsize(self.output_filename)
            
            # Send file size first
            self.connection.sendall(str(file_size).encode())
            
            # Wait for acknowledgment
            self.connection.recv(1024)
            
            # Send file data
            with open(self.output_filename, 'rb') as f:
                data = f.read(1024)
                while data:
                    self.connection.sendall(data)
                    data = f.read(1024)
            
            self.status_var.set("Message sent successfully")
            self.send_btn.config(state="disabled")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send recording: {str(e)}")
    
    def receive_messages(self):
        while self.connected:
            try:
                # Receive file size first
                file_size_data = self.connection.recv(1024)
                if not file_size_data:
                    continue
                
                file_size = int(file_size_data.decode())
                
                # Send acknowledgment
                self.connection.sendall(b"ACK")
                
                # Prepare to receive file
                self.input_filename = os.path.join(self.temp_dir, f"incoming_{int(time.time())}.wav")
                bytes_received = 0
                
                with open(self.input_filename, 'wb') as f:
                    while bytes_received < file_size:
                        data = self.connection.recv(min(1024, file_size - bytes_received))
                        if not data:
                            break
                        f.write(data)
                        bytes_received += len(data)
                
                self.master.after(0, self.message_received)
            except:
                if not self.connected:
                    break
    
    def message_received(self):
        self.status_var.set("New message received")
        self.play_btn.config(state="normal")
    
    def play_received(self):
        if not hasattr(self, 'input_filename') or self.playing:
            return
        
        try:
            self.playing = True
            self.play_btn.config(state="disabled")
            self.status_var.set("Playing message...")
            
            # Open the wave file
            wf = wave.open(self.input_filename, 'rb')
            
            # Open a stream
            stream = self.p.open(
                format=self.p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True
            )
            
            # Read data in chunks
            data = wf.readframes(self.chunk)
            
            def play_callback():
                nonlocal data
                if data:
                    stream.write(data)
                    data = wf.readframes(self.chunk)
                    self.master.after(10, play_callback)
                else:
                    stream.stop_stream()
                    stream.close()
                    self.playing = False
                    self.play_btn.config(state="normal")
                    self.status_var.set("Ready")
            
            play_callback()
            
        except Exception as e:
            self.playing = False
            self.play_btn.config(state="normal")
            messagebox.showerror("Error", f"Failed to play recording: {str(e)}")
    
    def on_closing(self):
        if self.connected:
            self.stop_connection()
        self.p.terminate()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = VoiceChatApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
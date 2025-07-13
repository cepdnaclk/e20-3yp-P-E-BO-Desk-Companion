import socket
import threading
import time
import json
from datetime import datetime
import hashlib
import os
import subprocess
import psutil
import random

class RaspberryPiMiniPeboBOT:
    def __init__(self):
        self.main_pebo_host = None  # Will be set when connecting
        self.main_pebo_port = 8888
        self.socket = None
        self.connected = False
        self.running = False
        self.device_id = None
        
        # Security
        self.auth_key = "pebo_secure_2024"
        
        # Device info
        self.device_info = {
            'device_type': 'raspberry_pi',
            'hostname': os.uname().nodename,
            'capabilities': ['gpio', 'sensors', 'camera', 'network_monitor', 'system_control'],
            'status': 'initializing'
        }
        
        # Sensor simulation (replace with actual sensor code)
        self.sensors = {
            'temperature': 0,
            'humidity': 0,
            'motion': False,
            'light': 0
        }
        
    def get_system_info(self):
        """Get Raspberry Pi system information"""
        try:
            cpu_temp = self.get_cpu_temperature()
            return {
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'cpu_temperature': cpu_temp,
                'uptime': time.time() - psutil.boot_time(),
                'network_io': psutil.net_io_counters()._asdict()
            }
        except:
            return {'error': 'Could not get system info'}
    
    def get_cpu_temperature(self):
        """Get CPU temperature (Raspberry Pi specific)"""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read()) / 1000.0
                return round(temp, 1)
        except:
            return 0
    
    def simulate_sensors(self):
        """Simulate sensor readings (replace with actual sensor code)"""
        self.sensors = {
            'temperature': round(random.uniform(20, 30), 1),
            'humidity': round(random.uniform(40, 70), 1),
            'motion': random.choice([True, False]),
            'light': random.randint(0, 1000),
            'cpu_temp': self.get_cpu_temperature()
        }
    
    def connect_to_main_pebo(self, host):
        """Connect to main PeboBOT"""
        self.main_pebo_host = host
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.main_pebo_host, self.main_pebo_port))
            
            # Send authentication
            auth_message = json.dumps({
                'auth_key': self.auth_key,
                'device_type': 'raspberry_pi',
                'hostname': self.device_info['hostname'],
                'capabilities': self.device_info['capabilities']
            })
            
            self.socket.send(auth_message.encode('utf-8'))
            response = self.socket.recv(1024).decode('utf-8')
            
            try:
                auth_response = json.loads(response)
                if auth_response.get('status') == 'authenticated':
                    self.connected = True
                    self.device_id = auth_response.get('device_id')
                    self.device_info['status'] = 'connected'
                    print(f"[RASPBERRY PI] Connected to main PeboBOT as {self.device_id}")
                    return True
                else:
                    print(f"[RASPBERRY PI] Authentication failed: {auth_response}")
                    return False
            except:
                print(f"[RASPBERRY PI] Invalid auth response: {response}")
                return False
                
        except Exception as e:
            print(f"[RASPBERRY PI] Connection error: {e}")
            return False
    
    def send_message(self, message):
        """Send message to main PeboBOT"""
        if self.connected and self.socket:
            try:
                if isinstance(message, dict):
                    message = json.dumps(message)
                self.socket.send(message.encode('utf-8'))
                return True
            except:
                self.connected = False
                return False
        return False
    
    def receive_message(self):
        """Receive message from main PeboBOT"""
        if self.connected and self.socket:
            try:
                message = self.socket.recv(1024).decode('utf-8')
                if message:
                    return message
                else:
                    self.connected = False
                    return None
            except:
                self.connected = False
                return None
        return None
    
    def send_status_update(self):
        """Send status update to main PeboBOT"""
        status_message = {
            'type': 'status_update',
            'device_id': self.device_id,
            'status': self.device_info['status'],
            'capabilities': self.device_info['capabilities'],
            'system_info': self.get_system_info(),
            'timestamp': datetime.now().isoformat()
        }
        return self.send_message(status_message)
    
    def send_sensor_data(self):
        """Send sensor data to main PeboBOT"""
        self.simulate_sensors()
        sensor_message = {
            'type': 'sensor_data',
            'device_id': self.device_id,
            'sensors': self.sensors,
            'timestamp': datetime.now().isoformat()
        }
        return self.send_message(sensor_message)
    
    def send_heartbeat(self):
        """Send heartbeat to main PeboBOT"""
        heartbeat_message = {
            'type': 'heartbeat',
            'device_id': self.device_id,
            'status': 'alive',
            'timestamp': datetime.now().isoformat()
        }
        return self.send_message(heartbeat_message)
    
    def process_command(self, command):
        """Process commands from main PeboBOT"""
        if command == 'get_status':
            return {
                'status': self.device_info['status'],
                'system_info': self.get_system_info(),
                'sensors': self.sensors
            }
        
        elif command == 'get_sensors':
            self.simulate_sensors()
            return {'sensors': self.sensors}
        
        elif command == 'reboot':
            if self.device_info['status'] == 'connected':
                # Simulate reboot (uncomment for actual reboot)
                # subprocess.run(['sudo', 'reboot'])
                return {'status': 'rebooting'}
        
        elif command == 'network_scan':
            return self.network_scan()
        
        elif command == 'camera_capture':
            return self.camera_capture()
        
        else:
            return {'error': f'Unknown command: {command}'}
    
    def network_scan(self):
        """Scan local network"""
        try:
            # Get network interface info
            interfaces = psutil.net_if_addrs()
            network_info = {}
            for interface, addresses in interfaces.items():
                for addr in addresses:
                    if addr.family == socket.AF_INET:
                        network_info[interface] = addr.address
            
            return {
                'network_interfaces': network_info,
                'connected_to': self.main_pebo_host
            }
        except:
            return {'error': 'Network scan failed'}
    
    def camera_capture(self):
        """Simulate camera capture"""
        # Replace with actual camera code
        return {
            'camera_status': 'simulated_capture',
            'timestamp': datetime.now().isoformat(),
            'image_path': '/tmp/capture.jpg'
        }
    
    def message_handler(self):
        """Handle messages from main PeboBOT"""
        while self.running and self.connected:
            message = self.receive_message()
            if message:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type', 'unknown')
                    
                    if msg_type == 'heartbeat':
                        print(f"[RASPBERRY PI] Heartbeat from main PeboBOT")
                        self.send_heartbeat()
                    
                    elif msg_type == 'command':
                        command = data.get('command', '')
                        print(f"[RASPBERRY PI] Command received: {command}")
                        result = self.process_command(command)
                        response = {
                            'type': 'command_response',
                            'command': command,
                            'result': result,
                            'timestamp': datetime.now().isoformat()
                        }
                        self.send_message(response)
                    
                    elif msg_type == 'sync_request':
                        print(f"[RASPBERRY PI] Sync request received")
                        self.send_status_update()
                        self.send_sensor_data()
                    
                    else:
                        print(f"[RASPBERRY PI] Unknown message: {message}")
                        
                except json.JSONDecodeError:
                    print(f"[RASPBERRY PI] Non-JSON message: {message}")
                    # Handle simple text messages
                    if message.lower() == 'ping':
                        self.send_message('pong from raspberry pi')
                    elif message.lower() == 'status':
                        self.send_status_update()
            else:
                time.sleep(0.1)
    
    def data_sender(self):
        """Send periodic data to main PeboBOT"""
        while self.running and self.connected:
            # Send sensor data every 15 seconds
            self.send_sensor_data()
            time.sleep(15)
            
            # Send status update every 30 seconds
            self.send_status_update()
            time.sleep(15)
    
    def start_mini_pebo(self, main_pebo_host):
        """Start the mini PeboBOT"""
        self.running = True
        
        if self.connect_to_main_pebo(main_pebo_host):
            print(f"[RASPBERRY PI] Mini PeboBOT started, connected to {main_pebo_host}")
            
            # Start message handler thread
            message_thread = threading.Thread(target=self.message_handler)
            message_thread.daemon = True
            message_thread.start()
            
            # Start data sender thread
            data_thread = threading.Thread(target=self.data_sender)
            data_thread.daemon = True
            data_thread.start()
            
            # Send initial status
            self.send_status_update()
            
            # Keep alive
            try:
                while self.running and self.connected:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n[RASPBERRY PI] Shutting down...")
                self.stop_mini_pebo()
        else:
            print(f"[RASPBERRY PI] Failed to connect to main PeboBOT at {main_pebo_host}")
    
    def stop_mini_pebo(self):
        """Stop the mini PeboBOT"""
        self.running = False
        self.connected = False
        if self.socket:
            self.socket.close()
        print("[RASPBERRY PI] Mini PeboBOT stopped")

# Interactive setup and run
if __name__ == "__main__":
    try:
        raspberry_pi = RaspberryPiMiniPeboBOT()
        
        # Get main PeboBOT IP address
        main_pebo_ip = input("Enter main PeboBOT (laptop) IP address: ").strip()
        if not main_pebo_ip:
            main_pebo_ip = "192.168.1.100"  # Default IP
            
        print(f"Connecting to main PeboBOT at {main_pebo_ip}...")
        raspberry_pi.start_mini_pebo(main_pebo_ip)
        
    except KeyboardInterrupt:
        print("\nShutting down Raspberry Pi Mini PeboBOT...")
    except Exception as e:
        print(f"Error: {e}")
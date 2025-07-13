import socket
import threading
import time
import json
from datetime import datetime
import hashlib
import os
import psutil

class LaptopMainPeboBOT:
    def __init__(self):
        self.host = '0.0.0.0'  # Listen on all interfaces
        self.port = 8888
        self.clients = {}
        self.mini_pebos = {}
        self.running = False
        self.server_socket = None
        
        # Security
        self.auth_key = "pebo_secure_2024"
        
        # Status
        self.status = {
            'online': True,
            'connected_devices': 0,
            'last_activity': datetime.now().isoformat(),
            'system_health': 'optimal',
            'device_type': 'laptop_main'
        }
        
    def get_system_info(self):
        """Get laptop system information"""
        return {
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'battery': psutil.sensors_battery().percent if psutil.sensors_battery() else 'N/A',
            'network_io': psutil.net_io_counters()._asdict()
        }
        
    def generate_device_id(self, address):
        """Generate unique device ID based on address"""
        return hashlib.md5(f"{address[0]}:{address[1]}".encode()).hexdigest()[:8]
    
    def authenticate_device(self, message, client_socket):
        """Authenticate connecting device"""
        try:
            data = json.loads(message)
            if data.get('auth_key') == self.auth_key:
                device_id = self.generate_device_id(client_socket.getpeername())
                device_type = data.get('device_type', 'unknown')
                
                response = {
                    'status': 'authenticated',
                    'device_id': device_id,
                    'device_type': device_type,
                    'timestamp': datetime.now().isoformat(),
                    'main_pebo': True,
                    'commands': ['status', 'ping', 'system_info', 'network_scan', 'shutdown']
                }
                return json.dumps(response)
            else:
                return json.dumps({'status': 'auth_failed', 'message': 'Invalid auth key'})
        except:
            return json.dumps({'status': 'auth_failed', 'message': 'Invalid auth format'})
    
    def handle_client(self, client_socket, address):
        """Handle individual client connections"""
        device_id = self.generate_device_id(address)
        print(f"[LAPTOP MAIN] New connection from {address} (ID: {device_id})")
        
        try:
            while self.running:
                message = client_socket.recv(1024).decode('utf-8')
                if not message:
                    break
                
                print(f"[LAPTOP MAIN] Received from {device_id}: {message}")
                
                # Handle authentication
                if message.startswith('{"auth_key"'):
                    response = self.authenticate_device(message, client_socket)
                    client_socket.send(response.encode('utf-8'))
                    
                    # Store client info
                    try:
                        data = json.loads(message)
                        self.clients[device_id] = {
                            'socket': client_socket,
                            'address': address,
                            'device_type': data.get('device_type', 'unknown'),
                            'connected_at': datetime.now().isoformat()
                        }
                        self.status['connected_devices'] += 1
                        
                        if data.get('device_type') == 'raspberry_pi':
                            self.mini_pebos[device_id] = {
                                'type': 'raspberry_pi',
                                'status': 'connected',
                                'last_seen': datetime.now().isoformat()
                            }
                            print(f"[LAPTOP MAIN] Raspberry Pi mini PeboBOT connected: {device_id}")
                    except:
                        pass
                    continue
                
                # Handle different message types
                try:
                    data = json.loads(message)
                    response = self.process_message(data, device_id)
                    client_socket.send(response.encode('utf-8'))
                except json.JSONDecodeError:
                    # Handle simple text messages
                    response = self.process_text_message(message, device_id)
                    client_socket.send(response.encode('utf-8'))
                
                # Update status
                self.status['last_activity'] = datetime.now().isoformat()
                
        except Exception as e:
            print(f"[LAPTOP MAIN] Error handling client {device_id}: {e}")
        finally:
            if device_id in self.clients:
                del self.clients[device_id]
            if device_id in self.mini_pebos:
                del self.mini_pebos[device_id]
            client_socket.close()
            self.status['connected_devices'] -= 1
            print(f"[LAPTOP MAIN] Client {device_id} disconnected")
    
    def process_message(self, data, device_id):
        """Process structured JSON messages"""
        msg_type = data.get('type', 'unknown')
        
        if msg_type == 'status_update':
            if device_id in self.mini_pebos:
                self.mini_pebos[device_id].update({
                    'status': data.get('status', 'unknown'),
                    'last_seen': datetime.now().isoformat(),
                    'capabilities': data.get('capabilities', []),
                    'system_info': data.get('system_info', {})
                })
            return json.dumps({
                'status': 'received',
                'message': 'Status updated',
                'timestamp': datetime.now().isoformat()
            })
        
        elif msg_type == 'command':
            return self.execute_command(data.get('command', ''), device_id)
        
        elif msg_type == 'sync_request':
            return self.handle_sync_request(device_id)
        
        elif msg_type == 'heartbeat':
            return json.dumps({
                'status': 'alive',
                'timestamp': datetime.now().isoformat(),
                'main_pebo': True,
                'device_type': 'laptop_main'
            })
        
        elif msg_type == 'sensor_data':
            return self.handle_sensor_data(data, device_id)
        
        else:
            return json.dumps({
                'status': 'unknown_message_type',
                'message': f'Unknown message type: {msg_type}'
            })
    
    def process_text_message(self, message, device_id):
        """Process simple text messages"""
        print(f"[LAPTOP MAIN] Processing text from {device_id}: {message}")
        
        # Simple command processing
        if message.lower() == 'status':
            return self.get_status_report()
        elif message.lower() == 'ping':
            return 'pong from laptop main'
        elif message.lower() == 'system_info':
            return json.dumps(self.get_system_info())
        elif message.lower().startswith('echo '):
            return f"Laptop Main Echo: {message[5:]}"
        elif message.lower() == 'network_scan':
            return self.network_scan()
        else:
            return f"Laptop Main PeboBOT received: {message}"
    
    def execute_command(self, command, device_id):
        """Execute commands from mini PeboBOTs"""
        if command == 'get_network_status':
            return json.dumps({
                'network_status': 'connected',
                'devices': len(self.clients),
                'mini_pebos': len(self.mini_pebos),
                'system_info': self.get_system_info()
            })
        
        elif command == 'get_device_list':
            devices = {}
            for did, client in self.clients.items():
                devices[did] = {
                    'device_type': client['device_type'],
                    'connected_at': client['connected_at']
                }
            return json.dumps({
                'devices': devices,
                'mini_pebos': self.mini_pebos
            })
        
        elif command == 'relay_command':
            # Relay command to other devices
            return self.relay_command_to_devices(command, device_id)
        
        else:
            return json.dumps({
                'status': 'unknown_command',
                'message': f'Unknown command: {command}'
            })
    
    def handle_sensor_data(self, data, device_id):
        """Handle sensor data from Raspberry Pi"""
        print(f"[LAPTOP MAIN] Sensor data from {device_id}: {data}")
        
        # Store sensor data
        if device_id in self.mini_pebos:
            self.mini_pebos[device_id]['sensor_data'] = data.get('sensors', {})
            self.mini_pebos[device_id]['last_sensor_update'] = datetime.now().isoformat()
        
        return json.dumps({
            'status': 'sensor_data_received',
            'timestamp': datetime.now().isoformat()
        })
    
    def handle_sync_request(self, device_id):
        """Handle synchronization requests"""
        sync_data = {
            'timestamp': datetime.now().isoformat(),
            'main_pebo_status': self.status,
            'network_devices': len(self.clients),
            'mini_pebos': self.mini_pebos,
            'system_info': self.get_system_info(),
            'sync_complete': True
        }
        return json.dumps(sync_data)
    
    def network_scan(self):
        """Scan network for devices"""
        connected_devices = []
        for device_id, client in self.clients.items():
            connected_devices.append({
                'device_id': device_id,
                'device_type': client['device_type'],
                'address': client['address'],
                'connected_at': client['connected_at']
            })
        
        return json.dumps({
            'network_scan': connected_devices,
            'total_devices': len(connected_devices),
            'mini_pebos': len(self.mini_pebos)
        })
    
    def get_status_report(self):
        """Get comprehensive status report"""
        system_info = self.get_system_info()
        report = f"""
LAPTOP MAIN PEBO STATUS REPORT
=============================
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Status: {self.status['system_health']}
Connected Devices: {self.status['connected_devices']}
Mini PeboBOTs: {len(self.mini_pebos)}
Last Activity: {self.status['last_activity']}

SYSTEM INFORMATION:
CPU Usage: {system_info['cpu_usage']}%
Memory Usage: {system_info['memory_usage']}%
Disk Usage: {system_info['disk_usage']}%
Battery: {system_info['battery']}%

CONNECTED MINI PEBOS:
{chr(10).join([f"- {pid}: {info['status']} ({info['type']})" for pid, info in self.mini_pebos.items()])}

NETWORK CLIENTS:
{chr(10).join([f"- {cid}: {client['device_type']} from {client['address']}" for cid, client in self.clients.items()])}
"""
        return report
    
    def broadcast_message(self, message, exclude_device=None):
        """Broadcast message to all connected devices"""
        disconnected = []
        for device_id, client_info in self.clients.items():
            if device_id != exclude_device:
                try:
                    client_info['socket'].send(message.encode('utf-8'))
                except:
                    disconnected.append(device_id)
        
        # Clean up disconnected clients
        for device_id in disconnected:
            if device_id in self.clients:
                del self.clients[device_id]
    
    def status_monitor(self):
        """Monitor system status"""
        while self.running:
            time.sleep(30)  # Check every 30 seconds
            print(f"[LAPTOP MAIN] Status: {len(self.clients)} clients, {len(self.mini_pebos)} mini PeboBOTs")
            
            # Send heartbeat to all devices
            heartbeat = json.dumps({
                'type': 'heartbeat',
                'timestamp': datetime.now().isoformat(),
                'from': 'laptop_main',
                'system_info': self.get_system_info()
            })
            self.broadcast_message(heartbeat)
    
    def start_server(self):
        """Start the main PeboBOT server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print(f"[LAPTOP MAIN] PeboBOT server started on {self.host}:{self.port}")
            print(f"[LAPTOP MAIN] System: {self.get_system_info()}")
            
            # Start status monitor thread
            monitor_thread = threading.Thread(target=self.status_monitor)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except:
                    if self.running:
                        print("[LAPTOP MAIN] Error accepting connection")
                        
        except Exception as e:
            print(f"[LAPTOP MAIN] Server error: {e}")
        finally:
            self.stop_server()
    
    def stop_server(self):
        """Stop the server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("[LAPTOP MAIN] Server stopped")

# Run the laptop main PeboBOT
if __name__ == "__main__":
    try:
        laptop_main = LaptopMainPeboBOT()
        print("Starting Laptop Main PeboBOT...")
        laptop_main.start_server()
    except KeyboardInterrupt:
        print("\nShutting down Laptop Main PeboBOT...")
    except Exception as e:
        print(f"Error: {e}")
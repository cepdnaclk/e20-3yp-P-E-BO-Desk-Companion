import paho.mqtt.client as mqtt
import base64
import json
import pyaudio
import wave
import threading
import time
import os
import argparse
import boto3
from botocore.exceptions import ClientError

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 1  # Short chunks for real-time communication

# AWS IoT Core settings
AWS_REGION = "us-east-1"  # Change to your AWS region
AWS_IOT_ENDPOINT = "your-iot-endpoint.iot.us-east-1.amazonaws.com"  # Replace with your AWS IoT endpoint
AWS_IOT_PORT = 8883
AWS_IOT_ROOT_CA = "certificates/AmazonRootCA1.pem"  # Path to AWS IoT Root CA
AWS_IOT_PRIVATE_KEY = "certificates/private.pem.key"  # Path to device private key
AWS_IOT_CERTIFICATE = "certificates/certificate.pem.crt"  # Path to device certificate

class PeboVoiceCall:
    def __init__(self, device_id):
        self.device_id = device_id
        self.other_device = None
        self.call_active = False
        self.audio = pyaudio.PyAudio()
        
        # Initialize MQTT client for AWS IoT
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        # Configure TLS for AWS IoT
        self.client.tls_set(
            ca_certs=AWS_IOT_ROOT_CA,
            certfile=AWS_IOT_CERTIFICATE,
            keyfile=AWS_IOT_PRIVATE_KEY,
            tls_version=mqtt.ssl.PROTOCOL_TLSv1_2
        )
        
        # Connect to AWS IoT Core
        try:
            self.client.connect(AWS_IOT_ENDPOINT, AWS_IOT_PORT, 60)
            self.client.loop_start()
            print(f"PEBO {self.device_id} connected to AWS IoT Core")
        except Exception as e:
            print(f"Failed to connect to AWS IoT Core: {e}")
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected to AWS IoT Core with result code {rc}")
            # Subscribe to control channel and voice channel
            self.client.subscribe(f"pebo/control/{self.device_id}")
            self.client.subscribe(f"pebo/voice/{self.device_id}")
        else:
            print(f"Failed to connect to AWS IoT Core with result code {rc}")
    
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        
        if topic == f"pebo/control/{self.device_id}":
            self.handle_control(msg.payload.decode())
        elif topic == f"pebo/voice/{self.device_id}":
            self.handle_voice(msg.payload)
    
    def handle_control(self, payload):
        try:
            data = json.loads(payload)
            action = data.get("action")
            caller = data.get("caller")
            
            if action == "call_request" and not self.call_active:
                print(f"\nIncoming call from {caller}. Accept? (y/n)")
                self.other_device = caller
                
            elif action == "call_accept" and caller == self.other_device:
                print(f"Call accepted by {caller}")
                self.call_active = True
                # Start voice streaming
                threading.Thread(target=self.stream_voice).start()
                
            elif action == "call_end":
                if self.call_active:
                    print(f"Call ended by {caller}")
                    self.call_active = False
                    self.other_device = None
        except Exception as e:
            print(f"Error handling control message: {e}")
    
    def handle_voice(self, payload):
        if not self.call_active:
            return
            
        try:
            # Save audio data to temp file
            temp_file = f"temp_audio_{self.device_id}.wav"
            
            with open(temp_file, "wb") as f:
                f.write(payload)
            
            # Play the audio
            self.play_audio(temp_file)
        except Exception as e:
            print(f"Error handling voice data: {e}")
    
    def initiate_call(self, recipient):
        if self.call_active:
            print("Already in a call!")
            return False
            
        self.other_device = recipient
        
        # Send call request
        control_data = {
            "action": "call_request",
            "caller": self.device_id,
            "timestamp": int(time.time())
        }
        
        self.client.publish(f"pebo/control/{recipient}", json.dumps(control_data))
        print(f"Calling {recipient}...")
        return True
    
    def accept_call(self):
        if not self.other_device:
            print("No incoming call to accept!")
            return False
            
        # Send acceptance
        control_data = {
            "action": "call_accept",
            "caller": self.device_id,
            "timestamp": int(time.time())
        }
        
        self.client.publish(f"pebo/control/{self.other_device}", json.dumps(control_data))
        self.call_active = True
        
        # Start voice streaming
        threading.Thread(target=self.stream_voice).start()
        print(f"Call with {self.other_device} started!")
        return True
    
    def end_call(self):
        if not self.call_active:
            print("No active call to end!")
            return False
            
        # Send end call signal
        control_data = {
            "action": "call_end",
            "caller": self.device_id,
            "timestamp": int(time.time())
        }
        
        self.client.publish(f"pebo/control/{self.other_device}", json.dumps(control_data))
        self.call_active = False
        print(f"Call with {self.other_device} ended!")
        self.other_device = None
        return True
    
    def record_audio(self, duration=1):
        stream = self.audio.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK)
        
        frames = []
        
        for i in range(0, int(RATE / CHUNK * duration)):
            data = stream.read(CHUNK)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        
        # Save to temp file
        temp_file = f"temp_recording_{self.device_id}.wav"
        wf = wave.open(temp_file, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        return temp_file
    
    def play_audio(self, filename):
        try:
            wf = wave.open(filename, 'rb')
            stream = self.audio.open(format=self.audio.get_format_from_width(wf.getsampwidth()),
                                channels=wf.getnchannels(),
                                rate=wf.getframerate(),
                                output=True)
            
            data = wf.readframes(CHUNK)
            while data and self.call_active:
                stream.write(data)
                data = wf.readframes(CHUNK)
            
            stream.stop_stream()
            stream.close()
            
            # Clean up temp file
            try:
                os.remove(filename)
            except:
                pass
        except Exception as e:
            print(f"Error playing audio: {e}")
    
    def stream_voice(self):
        print("Voice streaming started. Speak now!")
        
        while self.call_active:
            try:
                # Record a chunk of audio
                audio_file = self.record_audio(RECORD_SECONDS)
                
                # Read the recorded data
                with open(audio_file, "rb") as f:
                    audio_data = f.read()
                
                # Send to the other device through AWS IoT
                self.client.publish(f"pebo/voice/{self.other_device}", audio_data, qos=0)
                
                # Clean up temp file
                try:
                    os.remove(audio_file)
                except:
                    pass
                
                # Slight delay to prevent overwhelming the connection
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error in voice streaming: {e}")
                break
        
        print("Voice streaming ended.")
    
    def setup_aws_certificates(self):
        """Create directory for certificates if it doesn't exist"""
        os.makedirs("certificates", exist_ok=True)
        print("Please place your AWS IoT certificates in the 'certificates' folder:")
        print(f"  - {AWS_IOT_ROOT_CA}")
        print(f"  - {AWS_IOT_CERTIFICATE}")
        print(f"  - {AWS_IOT_PRIVATE_KEY}")
    
    def interactive_console(self):
        # Check for AWS certificates
        if not os.path.exists(AWS_IOT_ROOT_CA) or not os.path.exists(AWS_IOT_CERTIFICATE) or not os.path.exists(AWS_IOT_PRIVATE_KEY):
            self.setup_aws_certificates()
            print("Please restart the application after setting up the certificates.")
            return
            
        print(f"=== PEBO Voice Call System ({self.device_id}) ===")
        print("Commands:")
        print("  call <pebo_id> - Start a call with another PEBO")
        print("  accept         - Accept incoming call")
        print("  end            - End current call")
        print("  exit           - Exit application")
        
        while True:
            try:
                command = input("\nEnter command: ").strip()
                
                if command.startswith("call "):
                    recipient = command.split(" ")[1]
                    self.initiate_call(recipient)
                    
                elif command == "accept":
                    self.accept_call()
                    
                elif command == "end":
                    self.end_call()
                    
                elif command == "exit":
                    if self.call_active:
                        self.end_call()
                    self.client.loop_stop()
                    self.client.disconnect()
                    break
                    
                else:
                    print("Unknown command")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
        
        print("Exiting PEBO Voice Call System")

class AWSIoTSetup:
    """Helper class to create and manage AWS IoT resources"""
    
    def __init__(self, region_name):
        self.region = region_name
        self.iot_client = boto3.client('iot', region_name=region_name)
    
    def create_thing(self, thing_name):
        try:
            response = self.iot_client.create_thing(thingName=thing_name)
            print(f"Thing '{thing_name}' created successfully")
            return response['thingName']
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                print(f"Thing '{thing_name}' already exists")
                return thing_name
            else:
                print(f"Error creating thing: {e}")
                return None
    
    def create_certificate(self, thing_name):
        try:
            # Create keys and certificate
            response = self.iot_client.create_keys_and_certificate(setAsActive=True)
            
            certificate_id = response['certificateId']
            certificate_arn = response['certificateArn']
            certificate_pem = response['certificatePem']
            private_key = response['keyPair']['PrivateKey']
            
            # Save certificate and private key
            os.makedirs("certificates", exist_ok=True)
            
            with open("certificates/certificate.pem.crt", "w") as f:
                f.write(certificate_pem)
                
            with open("certificates/private.pem.key", "w") as f:
                f.write(private_key)
                
            # Download Amazon root CA
            import requests
            root_ca = requests.get("https://www.amazontrust.com/repository/AmazonRootCA1.pem")
            with open("certificates/AmazonRootCA1.pem", "w") as f:
                f.write(root_ca.text)
            
            # Attach policy and thing to certificate
            policy_name = f"{thing_name}_policy"
            self.create_policy(policy_name)
            
            self.iot_client.attach_policy(
                policyName=policy_name,
                target=certificate_arn
            )
            
            self.iot_client.attach_thing_principal(
                thingName=thing_name,
                principal=certificate_arn
            )
            
            print(f"Certificate created and attached to {thing_name}")
            return True
        except Exception as e:
            print(f"Error creating certificate: {e}")
            return False
    
    def create_policy(self, policy_name):
        try:
            # Create a policy that allows connect, publish, subscribe, and receive
            policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "iot:Connect",
                        "Resource": f"arn:aws:iot:{self.region}:*:client/*"
                    },
                    {
                        "Effect": "Allow",
                        "Action": "iot:Publish",
                        "Resource": "arn:aws:iot:{}:*:topic/pebo/*".format(self.region)
                    },
                    {
                        "Effect": "Allow",
                        "Action": "iot:Subscribe",
                        "Resource": "arn:aws:iot:{}:*:topicfilter/pebo/*".format(self.region)
                    },
                    {
                        "Effect": "Allow",
                        "Action": "iot:Receive",
                        "Resource": "arn:aws:iot:{}:*:topic/pebo/*".format(self.region)
                    }
                ]
            }
            
            self.iot_client.create_policy(
                policyName=policy_name,
                policyDocument=json.dumps(policy_document)
            )
            print(f"Policy '{policy_name}' created successfully")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                print(f"Policy '{policy_name}' already exists")
                return True
            else:
                print(f"Error creating policy: {e}")
                return False
    
    def get_endpoint(self):
        try:
            response = self.iot_client.describe_endpoint(
                endpointType='iot:Data-ATS'
            )
            return response['endpointAddress']
        except Exception as e:
            print(f"Error getting IoT endpoint: {e}")
            return None

def setup_aws_device(device_id):
    """Setup AWS IoT resources for a device"""
    print(f"Setting up AWS IoT for device {device_id}...")
    
    setup = AWSIoTSetup(AWS_REGION)
    
    # Create thing
    thing_name = setup.create_thing(device_id)
    
    if thing_name:
        # Create certificate and policy
        setup.create_certificate(thing_name)
        
        # Get IoT endpoint
        endpoint = setup.get_endpoint()
        if endpoint:
            print(f"Your AWS IoT endpoint is: {endpoint}")
            print("Update the AWS_IOT_ENDPOINT variable in the script with this value.")
        
        print(f"""
Setup complete! Before running the application:
1. Update the AWS_REGION variable if needed (currently {AWS_REGION})
2. Update the AWS_IOT_ENDPOINT variable with your endpoint
3. Make sure your AWS credentials are configured with appropriate permissions
""")
    else:
        print("Failed to set up AWS IoT resources.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PEBO Voice Call System using AWS IoT')
    parser.add_argument('device_id', type=str, help='Unique device ID (e.g., pebo1)')
    parser.add_argument('--setup', action='store_true', help='Set up AWS IoT resources for this device')
    
    args = parser.parse_args()
    
    if args.setup:
        setup_aws_device(args.device_id)
    else:
        pebo = PeboVoiceCall(args.device_id)
        pebo.interactive_console()
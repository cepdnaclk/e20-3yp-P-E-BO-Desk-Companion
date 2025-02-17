import paho.mqtt.client as mqtt

# Define the MQTT broker address and port
broker_address = "localhost"  # Change to the IP address of your broker if remote
broker_port = 1883
topic = "pebo/task"  # Define the topic to subscribe to

# Define the callback for connection
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(topic)

# Define the callback for message reception
def on_message(client, userdata, msg):
    print(f"Message received on topic {msg.topic}: {msg.payload.decode()}")

# Create the client instance
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Connect to the broker
client.connect(broker_address, broker_port, 60)

# Start the loop to listen for messages
client.loop_start()

# Keep the script running to receive messages
import time
time.sleep(10)

# Stop the loop and disconnect the client
client.loop_stop()
client.disconnect()

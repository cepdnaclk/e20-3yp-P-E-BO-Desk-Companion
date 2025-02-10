import paho.mqtt.client as mqtt
import time

# Define the MQTT broker address and port
broker_address = "localhost"  # Change to the IP address of your broker if remote
broker_port = 1883
topic = "pebo/task"  # Define the topic to publish to

# Define the callback for publishing
def on_publish(client, userdata, mid):
    print(f"Message {mid} published.")

# Create the client instance
client = mqtt.Client()
client.on_publish = on_publish

# Connect to the broker
client.connect(broker_address, broker_port, 60)

# Start the loop
client.loop_start()

# Simulate publishing a message to the topic
message = "Hello from MQTT Publisher!"
client.publish(topic, message)

# Wait for a while to allow message delivery
time.sleep(2)

# Stop the loop and disconnect the client
client.loop_stop()
client.disconnect()

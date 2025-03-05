import paho.mqtt.client as mqtt

BROKER = "localhost"  # Use 'test.mosquitto.org' if you want a public broker
TOPIC = "pebo/task"

def on_message(client, userdata, message):
    print(f"Received message: {message.payload.decode()}")

client = mqtt.Client()
client.on_message = on_message
client.connect(BROKER, 1883, 60)
client.subscribe(TOPIC)
client.loop_start()

# Function to send a task update
def send_task_update(task):
    client.publish(TOPIC, task)

# Example usage
send_task_update("PEBO received a new task")

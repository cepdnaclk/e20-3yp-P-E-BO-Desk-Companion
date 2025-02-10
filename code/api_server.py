from flask import Flask, request, jsonify
from firebase_setup import add_task, get_tasks
from mqtt_setup import send_task_update

app = Flask(__name__)

@app.route("/add_task", methods=["POST"])
def add_new_task():
    data = request.json
    add_task(data["task_id"], data)
    send_task_update(f"New task added: {data['title']}")
    return jsonify({"message": "Task added successfully"})

@app.route("/get_tasks", methods=["GET"])
def fetch_tasks():
    return jsonify(get_tasks())

if __name__ == "__main__":
    app.run(debug=True, port=5000)

import firebase_admin
from firebase_admin import credentials, db

# Load Firebase credentials
cred = credentials.Certificate("data\\pebo-task-manager-767f3-firebase-adminsdk-fbsvc-5c1cf078ce.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://pebo-task-manager-767f3-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

# Reference the database
task_ref = db.reference('tasks')
task_ref.set({"message": "Hello from PEBO server!"}) 

# Function to add a task
def add_task(task_id, task_data):
    task_ref.child(task_id).set(task_data)

# Function to get tasks
def get_tasks():
    return task_ref.get()

# Example usage
add_task("task1", {"title": "Test Task", "time": "10:00 AM"})
print(get_tasks())
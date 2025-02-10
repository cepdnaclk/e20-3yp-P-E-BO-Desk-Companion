import firebase_admin
from firebase_admin import credentials, db

# Load Firebase credentials
cred = credentials.Certificate("firebase_config.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://pebo-task-manager-767f3-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

# Reference the database
task_ref = db.reference('tasks')

# Function to add a task
def add_task(task_id, task_data):
    try:
        task_ref.child(task_id).set(task_data)
        print(f"Task '{task_id}' added successfully.")
    except Exception as e:
        print(f"Failed to add task '{task_id}': {e}")


# Function to get tasks
def get_tasks():
    return task_ref.get()

# Example usage
add_task("task1", {"title": "Test Task", "time": "10:00 AM"})
add_task("task4", {"title": "New Task", "time": "11:00 AM", "status": "pending"})

print(get_tasks())
tasks = get_tasks()
completed_tasks = {k: v for k, v in tasks.items() if v.get('status') == 'completed'}
print(completed_tasks)

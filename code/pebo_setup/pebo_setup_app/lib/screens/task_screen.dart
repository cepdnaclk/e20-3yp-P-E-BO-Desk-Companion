import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:intl/intl.dart'; // For date and time formatting

class Task {
  String id; // Unique ID for each task
  String title;
  bool isCompleted;
  DateTime? deadline; // Nullable deadline (includes date and time)

  Task({
    required this.id,
    required this.title,
    this.isCompleted = false,
    this.deadline,
  });

  // Convert a Task object to a Map for Firestore
  Map<String, dynamic> toMap() {
    return {
      'title': title,
      'isCompleted': isCompleted,
      'deadline': deadline, // Include deadline in the map
    };
  }

  // Create a Task object from a Firestore document
  factory Task.fromMap(String id, Map<String, dynamic> data) {
    return Task(
      id: id,
      title: data['title'],
      isCompleted: data['isCompleted'],
      deadline:
          data['deadline']?.toDate(), // Convert Firestore Timestamp to DateTime
    );
  }
}

class TaskScreen extends StatefulWidget {
  const TaskScreen({super.key});

  @override
  State<TaskScreen> createState() => _TaskScreenState();
}

class _TaskScreenState extends State<TaskScreen> {
  final TextEditingController _taskController = TextEditingController();
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  DateTime? _selectedDeadline; // To store the selected deadline (date and time)

  // Add a new task to Firestore
  Future<void> _addTask() async {
    if (_taskController.text.trim().isNotEmpty) {
      await _firestore.collection('tasks').add({
        'title': _taskController.text.trim(),
        'isCompleted': false,
        'deadline': _selectedDeadline, // Include the deadline
      });
      _taskController.clear();
      setState(() {
        _selectedDeadline = null; // Reset the deadline after adding the task
      });
    }
  }

  // Toggle task completion status in Firestore
  Future<void> _toggleTaskStatus(Task task) async {
    await _firestore.collection('tasks').doc(task.id).update({
      'isCompleted': !task.isCompleted,
    });
  }

  // Delete a task from Firestore
  Future<void> _deleteTask(String taskId) async {
    await _firestore.collection('tasks').doc(taskId).delete();
  }

  // Show a date and time picker to select the deadline
  Future<void> _selectDeadline(BuildContext context) async {
    final DateTime? pickedDate = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime.now(),
      lastDate: DateTime(2100),
    );
    if (pickedDate != null) {
      final TimeOfDay? pickedTime = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.now(),
      );
      if (pickedTime != null) {
        setState(() {
          _selectedDeadline = DateTime(
            pickedDate.year,
            pickedDate.month,
            pickedDate.day,
            pickedTime.hour,
            pickedTime.minute,
          );
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('PEBO Tasks'),
        backgroundColor: Colors.blue,
        foregroundColor: Colors.white,
      ),
      body: Column(
        children: [
          // Task input field
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _taskController,
                    decoration: const InputDecoration(
                      hintText: 'Add a new task',
                      border: OutlineInputBorder(),
                    ),
                    onSubmitted: (_) => _addTask(),
                  ),
                ),
                const SizedBox(width: 16),
                IconButton(
                  icon: const Icon(
                    Icons.add_circle,
                    color: Colors.blue,
                    size: 36,
                  ),
                  onPressed: _addTask,
                ),
              ],
            ),
          ),
          // Deadline selection
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0),
            child: Row(
              children: [
                Text(
                  _selectedDeadline == null
                      ? 'No deadline'
                      : 'Deadline: ${DateFormat('yyyy-MM-dd HH:mm').format(_selectedDeadline!)}',
                ),
                const SizedBox(width: 16),
                TextButton(
                  onPressed: () => _selectDeadline(context),
                  child: const Text('Set Deadline'),
                ),
              ],
            ),
          ),
          // Task list from Firestore
          Expanded(
            child: StreamBuilder<QuerySnapshot>(
              stream: _firestore.collection('tasks').snapshots(),
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return Center(child: Text('Error: ${snapshot.error}'));
                }
                if (!snapshot.hasData || snapshot.data!.docs.isEmpty) {
                  return const Center(child: Text('No tasks found.'));
                }
                final tasks =
                    snapshot.data!.docs.map((doc) {
                      return Task.fromMap(
                        doc.id,
                        doc.data() as Map<String, dynamic>,
                      );
                    }).toList();
                return ListView.builder(
                  itemCount: tasks.length,
                  itemBuilder: (context, index) {
                    final task = tasks[index];
                    return ListTile(
                      leading: Checkbox(
                        value: task.isCompleted,
                        onChanged: (_) => _toggleTaskStatus(task),
                      ),
                      title: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            task.title,
                            style: TextStyle(
                              decoration:
                                  task.isCompleted
                                      ? TextDecoration.lineThrough
                                      : null,
                              color:
                                  task.isCompleted ? Colors.grey : Colors.black,
                            ),
                          ),
                          if (task.deadline != null)
                            Text(
                              'Deadline: ${DateFormat('yyyy-MM-dd HH:mm').format(task.deadline!)}',
                              style: const TextStyle(
                                fontSize: 12,
                                color: Colors.grey,
                              ),
                            ),
                        ],
                      ),
                      trailing: IconButton(
                        icon: const Icon(Icons.delete, color: Colors.red),
                        onPressed: () => _deleteTask(task.id),
                      ),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          showDialog(
            context: context,
            builder:
                (context) => AlertDialog(
                  title: const Text('Add Task'),
                  content: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      TextField(
                        controller: _taskController,
                        decoration: const InputDecoration(
                          hintText: 'Task description',
                        ),
                        autofocus: true,
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: [
                          Text(
                            _selectedDeadline == null
                                ? 'No deadline'
                                : 'Deadline: ${DateFormat('yyyy-MM-dd HH:mm').format(_selectedDeadline!)}',
                          ),
                          const SizedBox(width: 16),
                          TextButton(
                            onPressed: () => _selectDeadline(context),
                            child: const Text('Set Deadline'),
                          ),
                        ],
                      ),
                    ],
                  ),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text('CANCEL'),
                    ),
                    TextButton(
                      onPressed: () {
                        _addTask();
                        Navigator.pop(context);
                      },
                      child: const Text('ADD'),
                    ),
                  ],
                ),
          );
        },
        backgroundColor: Colors.blue,
        child: const Icon(Icons.add, color: Colors.white),
      ),
    );
  }
}

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';

class Task {
  final String id;
  final String title;
  final DateTime time;
  final bool isCompleted;

  Task({
    required this.id,
    required this.title,
    required this.time,
    this.isCompleted = false,
  });

  Map<String, dynamic> toMap() {
    return {'title': title, 'time': time, 'isCompleted': isCompleted};
  }

  factory Task.fromMap(Map<String, dynamic> map, String id) {
    return Task(
      id: id,
      title: map['title'] ?? '',
      time: (map['time'] as Timestamp).toDate(),
      isCompleted: map['isCompleted'] ?? false,
    );
  }
}

class FirebaseService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  final FirebaseAuth _auth = FirebaseAuth.instance;

  // Get tasks collection reference for current user
  CollectionReference get _tasksCollection {
    final userId = _auth.currentUser?.uid;
    if (userId == null) {
      throw 'User not authenticated';
    }
    return _firestore.collection('users').doc(userId).collection('tasks');
  }

  // Get stream of tasks
  Stream<List<Task>> getTasks() {
    return _tasksCollection.orderBy('time').snapshots().map((snapshot) {
      return snapshot.docs
          .map(
            (doc) => Task.fromMap(doc.data() as Map<String, dynamic>, doc.id),
          )
          .toList();
    });
  }

  // Add a new task
  Future<void> addTask(String title, DateTime time) async {
    await _tasksCollection.add({
      'title': title,
      'time': time,
      'isCompleted': false,
      'createdAt': FieldValue.serverTimestamp(),
    });

    // In a real app, you would trigger MQTT sync to PEBO device here
  }

  // Toggle task completion status
  Future<void> toggleTaskStatus(String taskId, bool isCompleted) async {
    await _tasksCollection.doc(taskId).update({
      'isCompleted': isCompleted,
      'updatedAt': FieldValue.serverTimestamp(),
    });
  }

  // Delete a task
  Future<void> deleteTask(String taskId) async {
    await _tasksCollection.doc(taskId).delete();
  }
}

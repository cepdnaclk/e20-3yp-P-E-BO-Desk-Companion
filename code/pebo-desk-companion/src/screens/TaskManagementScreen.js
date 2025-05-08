import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  ActivityIndicator,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  Picker,
  Alert,
} from "react-native";
import { addTask, getTaskOverview } from "../services/firebase";
import DateTimePickerModal from "react-native-modal-datetime-picker";

const TaskManagementScreen = () => {
  const [task, setTask] = useState("");
  const [deadline, setDeadline] = useState(null);
  const [priority, setPriority] = useState("Medium");
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [isDatePickerVisible, setDatePickerVisible] = useState(false);

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const tasksData = await getTaskOverview();
      setTasks(tasksData.reverse());
    } catch (error) {
      Alert.alert("Error", "Failed to fetch tasks. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleAddTask = async () => {
    if (task.trim() === "") {
      Alert.alert("Input Error", "Please enter a task description.");
      return;
    }

    if (!deadline) {
      Alert.alert("Input Error", "Please select a deadline.");
      return;
    }

    setAdding(true);
    const newTask = {
      description: task.trim(),
      completed: false,
      deadline: deadline.toISOString(),
      priority,
    };

    try {
      await addTask(newTask);
      setTask("");
      setDeadline(null);
      setPriority("Medium");
      await fetchTasks();
    } catch (error) {
      Alert.alert("Error", "Failed to add task. Please try again.");
    } finally {
      setAdding(false);
    }
  };

  const renderItem = ({ item }) => (
    <View style={styles.taskItem}>
      <Text style={styles.taskText}>{item.description}</Text>
      {item.deadline && (
        <Text style={styles.deadlineText}>
          Deadline: {new Date(item.deadline).toLocaleString()}
        </Text>
      )}
      <Text style={styles.priorityText}>Priority: {item.priority}</Text>
    </View>
  );

  const showDatePicker = () => {
    setDatePickerVisible(true);
  };

  const hideDatePicker = () => {
    setDatePickerVisible(false);
  };

  const handleDateConfirm = (date) => {
    setDeadline(date);
    hideDatePicker();
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      style={styles.container}
    >
      <Text style={styles.header}>📝 Task Management</Text>

      <View style={styles.inputContainer}>
        <TextInput
          style={styles.input}
          placeholder="Enter a task..."
          value={task}
          onChangeText={setTask}
        />
        <View style={styles.row}>
          <TouchableOpacity style={styles.input} onPress={showDatePicker}>
            <Text style={styles.dateText}>
              {deadline ? deadline.toLocaleString() : "Select a deadline"}
            </Text>
          </TouchableOpacity>

          <Picker
            selectedValue={priority}
            style={styles.picker}
            onValueChange={(itemValue) => setPriority(itemValue)}
          >
            <Picker.Item label="High" value="High" />
            <Picker.Item label="Medium" value="Medium" />
            <Picker.Item label="Low" value="Low" />
          </Picker>
        </View>
      </View>

      <View style={styles.addButtonContainer}>
        <TouchableOpacity
          style={styles.addButton}
          onPress={handleAddTask}
          disabled={adding}
        >
          <Text style={styles.addButtonText}>
            {adding ? "Adding..." : "Add Task"}
          </Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <ActivityIndicator
          size="large"
          color="#007AFF"
          style={{ marginTop: 40 }}
        />
      ) : tasks.length === 0 ? (
        <Text style={styles.noTasksText}>No tasks found.</Text>
      ) : (
        <>
          <Text style={styles.countText}>Total Tasks: {tasks.length}</Text>
          <FlatList
            data={tasks}
            keyExtractor={(item) => item.id}
            renderItem={renderItem}
            style={styles.taskList}
          />
        </>
      )}

      <DateTimePickerModal
        isVisible={isDatePickerVisible}
        mode="datetime"
        onConfirm={handleDateConfirm}
        onCancel={hideDatePicker}
      />
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F4F7FB",
    paddingHorizontal: 20,
    paddingTop: 60,
  },
  header: {
    fontSize: 26,
    fontWeight: "bold",
    marginBottom: 20,
    textAlign: "center",
    color: "#333",
  },
  inputContainer: {
    flexDirection: "column",
    marginBottom: 16,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
  },
  input: {
    flex: 1,
    height: 48,
    backgroundColor: "#fff",
    borderRadius: 10,
    paddingHorizontal: 16,
    fontSize: 16,
    borderColor: "#ccc",
    borderWidth: 1,
    marginBottom: 10,
  },
  picker: {
    height: 48,
    width: "48%",
    borderRadius: 10,
    backgroundColor: "#fff",
    borderColor: "#ccc",
    borderWidth: 1,
    paddingLeft: 10,
  },
  dateText: {
    fontSize: 16,
    color: "#007AFF",
    textAlign: "center",
  },
  addButtonContainer: {
    alignItems: "center",
    marginTop: 10,
    marginBottom: 20,
  },
  addButton: {
    backgroundColor: "#007AFF",
    paddingHorizontal: 40,
    paddingVertical: 12,
    justifyContent: "center",
    borderRadius: 10,
    alignItems: "center",
    width: "60%",
  },
  addButtonText: {
    color: "#fff",
    fontWeight: "600",
    fontSize: 16,
  },
  taskList: {
    marginTop: 10,
  },
  taskItem: {
    backgroundColor: "#fff",
    padding: 14,
    borderRadius: 10,
    marginBottom: 10,
    elevation: 2,
  },
  taskText: {
    fontSize: 16,
    color: "#333",
  },
  deadlineText: {
    fontSize: 14,
    color: "#777",
    marginTop: 5,
  },
  priorityText: {
    fontSize: 14,
    color: "#007AFF",
    marginTop: 5,
  },
  noTasksText: {
    textAlign: "center",
    fontSize: 16,
    color: "#666",
    marginTop: 40,
  },
  countText: {
    fontSize: 14,
    color: "#666",
    marginBottom: 8,
  },
});

export default TaskManagementScreen;

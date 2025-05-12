import React, { useEffect, useState } from "react";
import { markTaskCompleted, updateTask } from "../services/firebase";
import moment from "moment"; 
import {
  View,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Alert,
  StyleSheet,
  ScrollView,
  Dimensions,
} from "react-native";
import {
  TextInput,
  Button,
  Card,
  Text,
  Menu,
  Provider as PaperProvider,
  DefaultTheme,
  ActivityIndicator,
} from "react-native-paper";
import DateTimePickerModal from "react-native-modal-datetime-picker";
import { addTask, getTaskOverview } from "../services/firebase";
import { SafeAreaView } from "react-native";

const { width } = Dimensions.get("window");

export default function TaskManagementScreen() {
  const [task, setTask] = useState("");
  const [deadline, setDeadline] = useState(null);
  const [isPickerVisible, setPickerVisible] = useState(false);
  const [category, setCategory] = useState("Work");
  const [priority, setPriority] = useState("Medium");
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [sortPreference, setSortPreference] = useState("deadline");
  const [showSortMenu, setShowSortMenu] = useState(false);
  const [showCatMenu, setShowCatMenu] = useState(false);
  const [showPriorityMenu, setShowPriorityMenu] = useState(false);
  const [tasks, setTasks] = useState([]);

  // Fetch & sort on mount or sortPreference change
  useEffect(() => {
    fetchAndSortTasks();
  }, [sortPreference]);

  // Update task completion status
  async function toggleCompleted(taskItem) {
    try {
      // Update task completion status in the database
      await updateTask(taskItem.id, {
        completed: !taskItem.completed,
      });

      // Update the task in the local state without needing to fetch all tasks again
      setTasks((prevTasks) =>
        prevTasks.map((task) =>
          task.id === taskItem.id
            ? { ...task, completed: !task.completed }
            : task
        )
      );
    } catch {
      Alert.alert("Error", "Failed to update task.");
    }
  }

  async function fetchAndSortTasks() {
    setLoading(true);
    try {
      const data = await getTaskOverview();
      if (!Array.isArray(data)) throw new Error();
      setTasks(sortTasks(data));
    } catch {
      Alert.alert("Error", "Failed to fetch tasks.");
    } finally {
      setLoading(false);
    }
  }

  function sortTasks(data) {
    if (sortPreference === "priority") {
      const order = { High: 0, Medium: 1, Low: 2 };
      return data.sort((a, b) => order[a.priority] - order[b.priority]);
    }
    return data.sort(
      (a, b) => new Date(a.deadline).getTime() - new Date(b.deadline).getTime()
    );
  }

  async function handleAddTask() {
    if (!task.trim()) return Alert.alert("Input Error", "Enter a task.");
    if (!deadline) return Alert.alert("Input Error", "Select deadline.");

    setAdding(true);
    try {
      await addTask({
        description: task.trim(),
        completed: false,
        deadline: deadline.toISOString(),
        category,
        priority,
      });
      setTask("");
      setDeadline(null);
      setCategory("Work");
      setPriority("Medium");
      await fetchAndSortTasks();
    } catch {
      Alert.alert("Error", "Failed to add task.");
    } finally {
      setAdding(false);
    }
  }

  const renderTask = ({ item }) => (
    <Card style={[styles.card, item.completed && styles.completedCard]}>
      <Card.Title
        titleStyle={[styles.cardTitle, item.completed && styles.completedText]}
        title={item.description}
        right={() => (
          <Button
            icon={
              item.completed ? "check-circle" : "checkbox-blank-circle-outline"
            }
            onPress={() => toggleCompleted(item)}
            compact
          />
        )}
      />
      <Card.Content>
        <View style={styles.taskInfoRow}>
          <Text style={styles.infoText}>
            📅 {new Date(item.deadline).toLocaleString()}
          </Text>
          <Text style={styles.infoText}>🚦 {item.priority}</Text>
          <Text style={styles.infoText}>📂 {item.category}</Text>
        </View>
      </Card.Content>
    </Card>
  );

  const renderMenu = (title, value, items, visible, setVisible, onChange) => (
    <Menu
      visible={visible}
      onDismiss={() => setVisible(false)}
      anchor={
        <Button
          mode="outlined"
          onPress={() => setVisible(true)}
          style={styles.input}
        >
          {title}: {value}
        </Button>
      }
    >
      {items.map((v) => (
        <Menu.Item
          key={v}
          title={`• ${v}`}
          onPress={() => {
            onChange(v);
            setVisible(false);
          }}
          leadingIcon="chevron-right"
        />
      ))}
    </Menu>
  );

  return (
    <PaperProvider theme={theme}>
      <SafeAreaView style={{ flex: 1, backgroundColor: "#0f0f0f" }}>
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          style={{ flex: 1 }}
          keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 20}
        >
          <View style={styles.container}>
            <Text style={styles.header}>🗒️ My Tasks</Text>

            <TextInput
              label="Task description"
              value={task}
              onChangeText={setTask}
              mode="outlined"
              style={styles.input}
            />

            <Button
              mode="outlined"
              icon="calendar"
              onPress={() => setPickerVisible(true)}
              style={styles.input}
            >
              {deadline
                ? moment(deadline).format("DD MMM YYYY, hh:mm A")
                : "Select deaddline & time"}
            </Button>

            <DateTimePickerModal
              isVisible={isPickerVisible}
              mode="datetime"
              onConfirm={(date) => {
                setDeadline(date);
                setPickerVisible(false);
              }}
              onCancel={() => setPickerVisible(false)}
            />

            {renderMenu(
              "🚦 Priority",
              priority,
              ["High", "Medium", "Low"],
              showPriorityMenu,
              setShowPriorityMenu,
              setPriority
            )}

            {renderMenu(
              "📂 Category",
              category,
              ["Work", "Personal", "Study"],
              showCatMenu,
              setShowCatMenu,
              setCategory
            )}

            <Button
              mode="contained"
              icon="plus-circle"
              onPress={handleAddTask}
              loading={adding}
              style={styles.addBtn}
            >
              Add New Task
            </Button>

            <View style={styles.sortRow}>
              <Text>Sort by:</Text>
              {renderMenu(
                "Sort",
                sortPreference.charAt(0).toUpperCase() +
                  sortPreference.slice(1),
                ["Deadline", "Priority"],
                showSortMenu,
                setShowSortMenu,
                (val) => setSortPreference(val.toLowerCase())
              )}
            </View>

            <View style={styles.flex}>
              {loading ? (
                <ActivityIndicator style={{ marginTop: 24 }} />
              ) : tasks.length === 0 ? (
                <Text
                  style={{ textAlign: "center", marginTop: 24, color: "#888" }}
                >
                  No tasks available.
                </Text>
              ) : (
                <FlatList
                  data={tasks}
                  renderItem={renderTask}
                  keyExtractor={(item, index) => item.id || index.toString()}
                  contentContainerStyle={{ paddingBottom: 100 }}
                  keyboardShouldPersistTaps="handled"
                  
                />
              )}
            </View>
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </PaperProvider>
  );
}

// Light theme override
const theme = {
  ...DefaultTheme,
  roundness: 12,
  colors: {
    ...DefaultTheme.colors,
    primary: "#4C9EEB", // Calming blue
    accent: "#FFB64D", // Warm orange
    background: "#FAFAFC", // Soft off-white
    surface: "#FFFFFF",
    text: "#1E1E1E",
    placeholder: "#9E9E9E",
    disabled: "#E0E0E0",
    elevation: {
      level2: "#F2F2F2",
    },
  },
};


// Styles
const styles = StyleSheet.create({
  flex: { flex: 1 },

  container: {
    flex: 1,
    padding: 20,
    paddingTop: 60,
    backgroundColor: "#FAFAFC",
  },

  header: {
    fontSize: 28,
    fontWeight: "bold",
    color: "#333",
    marginBottom: 20,
    textAlign: "center",
  },

  input: {
    marginBottom: 12,
    backgroundColor: "#fff",
    borderRadius: 14,
    elevation: 2,
    shadowColor: "#aaa",
    shadowOpacity: 0.1,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
  },

  addBtn: {
    marginVertical: 16,
    borderRadius: 14,
    paddingVertical: 12,
    backgroundColor: "#4C9EEB",
    elevation: 3,
  },

  sortRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginVertical: 10,
  },

  taskInfoRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 10,
  },

  infoText: {
    color: "#6A6A6A",
    fontSize: 13,
  },

  card: {
    backgroundColor: "#fff",
    marginBottom: 14,
    borderRadius: 16,
    paddingVertical: 8,
    width: width * 0.92,
    alignSelf: "center",
    elevation: 3,
    shadowColor: "#ccc",
    shadowOpacity: 0.2,
    shadowOffset: { width: 0, height: 2 },
  },

  cardTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: "#1E1E1E",
  },

  completedCard: {
    backgroundColor: "#F0F0F0",
  },

  completedText: {
    textDecorationLine: "line-through",
    color: "#9E9E9E",
  },
});

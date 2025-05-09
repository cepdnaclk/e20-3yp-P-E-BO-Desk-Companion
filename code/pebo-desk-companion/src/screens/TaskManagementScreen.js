import React, { useEffect, useState } from "react";
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
    <Card style={styles.card}>
      <Card.Title title={item.description} />
      <Card.Content>
        <Text>📅 {new Date(item.deadline).toLocaleString()}</Text>
        <Text>🚦 {item.priority}</Text>
        <Text>📂 {item.category}</Text>
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
          title={v}
          onPress={() => {
            onChange(v);
            setVisible(false);
          }}
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
              {deadline ? deadline.toLocaleString() : "Select deadline & time"}
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
              onPress={handleAddTask}
              loading={adding}
              style={styles.addBtn}
            >
              ➕ Add Task
            </Button>

            <View style={styles.sortRow}>
              <Text>Sort by:</Text>
              {renderMenu(
                "Sort",
                sortPreference,
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
  roundness: 10,
  colors: {
    ...DefaultTheme.colors,
    primary: "#007AFF", // iOS blue
    accent: "#FF9500", // iOS orange for highlights
    background: "#F2F2F7", // iOS system background
    surface: "#FFFFFF",
    text: "#1C1C1E", // dark gray for text
    placeholder: "#A1A1A1",
    disabled: "#D1D1D6",
    elevation: {
      level2: "#FFFFFF",
    },
  },
};


const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flex: 1,
    padding: 16,
    paddingTop: 50,
    alignItems: "center",
    backgroundColor: "#F2F2F7",
  },
  scroll: {
    alignItems: "center",
    padding: 16,
    minWidth: width,
  },
  header: {
    fontSize: 26,
    fontWeight: "bold",
    color: "#1C1C1E",
    marginBottom: 20,
  },
  input: {
    width: "100%",
    marginBottom: 12,
    backgroundColor: "#FFFFFF",
    borderRadius: 10,
  },
  addBtn: {
    width: "100%",
    marginVertical: 16,
    borderRadius: 10,
    paddingVertical: 6,
  },
  sortRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    width: "100%",
    marginBottom: 16,
  },
  card: {
    width: "100%",
    marginBottom: 12,
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    elevation: 2,
  },
});

import React, { useEffect, useState } from "react";
import {
  View,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Alert,
  StyleSheet,
  Dimensions,
  SafeAreaView,
} from "react-native";
import { Ionicons, MaterialIcons } from "@expo/vector-icons";
import PopupModal from "../components/PopupModal";
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
import { addTask, getTaskOverview, updateTask } from "../services/firebase";
import moment from "moment";

const { width } = Dimensions.get("window");

export default function TaskManagementScreen() {
  const [task, setTask] = useState("");
  const [deadline, setDeadline] = useState(null);
  const [isPickerVisible, setPickerVisible] = useState(false);
  const [category, setCategory] = useState("Work");
  const [priority, setPriority] = useState("Medium");
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [sortPref, setSortPref] = useState("deadline");
  const [showSortMenu, setShowSortMenu] = useState(false);
  const [showCatMenu, setShowCatMenu] = useState(false);
  const [showPriMenu, setShowPriMenu] = useState(false);
  const [tasks, setTasks] = useState([]);
  const [popupVisible, setPopupVisible] = useState(false);
  const [popupContent, setPopupContent] = useState({
    title: "",
    message: "",
    icon: "checkmark-circle",
  });

  useEffect(() => {
    fetchAndSort();
  }, [sortPref]);

  async function fetchAndSort() {
    setLoading(true);
    try {
      const data = await getTaskOverview();
      if (!Array.isArray(data)) throw new Error();
      const order = { High: 0, Medium: 1, Low: 2 };
      const sorted = data.sort((a, b) => {
        if (sortPref === "priority")
          return order[a.priority] - order[b.priority];
        return new Date(a.deadline) - new Date(b.deadline);
      });
      setTasks(sorted);
    } catch {
      showPopup("Error", "Failed to fetch tasks", "alert-circle");
    } finally {
      setLoading(false);
    }
  }

  async function toggleCompleted(item) {
    try {
      await updateTask(item.id, { completed: !item.completed });
      setTasks((ts) =>
        ts.map((t) =>
          t.id === item.id ? { ...t, completed: !t.completed } : t
        )
      );
    } catch {
      showPopup("Error", "Failed to update task", "alert-circle");
    }
  }

  function showPopup(title, message, icon = "checkmark-circle") {
    setPopupContent({ title, message, icon });
    setPopupVisible(true);
  }

  async function addNew() {
    if (!task.trim())
      return showPopup("Input Error", "Enter a task", "alert-circle");
    if (!deadline)
      return showPopup("Input Error", "Select deadline", "alert-circle");
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
      await fetchAndSort();
      showPopup("Success", "Task added successfully", "checkmark-circle");
    } catch {
      showPopup("Error", "Failed to add task", "alert-circle");
    } finally {
      setAdding(false);
    }
  }

  const renderMenu = (label, val, opts, vis, setVis, onSelect) => (
    <Menu
      visible={vis}
      onDismiss={() => setVis(false)}
      anchor={
        <Button
          mode="outlined"
          onPress={() => setVis(true)}
          style={styles.input}
          contentStyle={{ justifyContent: "space-between" }}
        >
          {label}: {val}
        </Button>
      }
    >
      {opts.map((o) => (
        <Menu.Item
          key={o}
          title={`• ${o}`}
          leadingIcon="chevron-right"
          onPress={() => {
            onSelect(o);
            setVis(false);
          }}
        />
      ))}
    </Menu>
  );

  const renderTask = ({ item }) => (
    <Card style={[styles.card, item.completed && styles.completedCard]}>
      <Card.Title
        title={item.description}
        titleStyle={[styles.cardTitle, item.completed && styles.completedText]}
        right={() => (
          <Button
            icon={
              item.completed ? "check-circle" : "checkbox-blank-circle-outline"
            }
            onPress={() => toggleCompleted(item)}
            compact
            color="#007AFF"
          />
        )}
      />
      <Card.Content>
        <View style={styles.taskInfo}>
          <Text style={styles.info}>
            📅 {moment(item.deadline).format("DD MMM, hh:mm A")}
          </Text>
          <Text style={styles.info}>🚦 {item.priority}</Text>
          <Text style={styles.info}>📂 {item.category}</Text>
        </View>
      </Card.Content>
    </Card>
  );

  return (
    <PaperProvider theme={theme}>
      <SafeAreaView style={styles.container}>
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          style={{ flex: 1 }}
          keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 20}
        >
          <Text style={styles.appName}>My Tasks</Text>

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
              : "Select deadline & time"}
          </Button>

          <DateTimePickerModal
            isVisible={isPickerVisible}
            mode="datetime"
            onConfirm={(d) => {
              setDeadline(d);
              setPickerVisible(false);
            }}
            onCancel={() => setPickerVisible(false)}
          />

          {renderMenu(
            "🚦 Priority",
            priority,
            ["High", "Medium", "Low"],
            showPriMenu,
            setShowPriMenu,
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
            onPress={addNew}
            loading={adding}
            style={styles.addBtn}
            contentStyle={{ paddingVertical: 6 }}
            labelStyle={{ color: "white", fontWeight: "600" }}
          >
            Add New Task
          </Button>

          <View style={styles.sortRow}>
            <Text style={styles.sortText}>Sort by:</Text>
            {renderMenu(
              "Sort",
              sortPref.charAt(0).toUpperCase() + sortPref.slice(1),
              ["Deadline", "Priority"],
              showSortMenu,
              setShowSortMenu,
              (v) => setSortPref(v.toLowerCase())
            )}
          </View>

          <View style={{ flex: 1 }}>
            {loading ? (
              <ActivityIndicator style={{ marginTop: 24 }} />
            ) : tasks.length === 0 ? (
              <Text style={styles.empty}>No tasks available.</Text>
            ) : (
              <FlatList
                data={tasks}
                renderItem={renderTask}
                keyExtractor={(_, i) => i.toString()}
                contentContainerStyle={{ paddingBottom: 100 }}
              />
            )}
          </View>

          <PopupModal
            visible={popupVisible}
            onClose={() => setPopupVisible(false)}
            title={popupContent.title}
            message={popupContent.message}
            icon={popupContent.icon}
            style={styles.popup}
            contentStyle={styles.popupContent}
          />
        </KeyboardAvoidingView>
      </SafeAreaView>
    </PaperProvider>
  );
}

const theme = {
  ...DefaultTheme,
  roundness: 12,
  colors: {
    ...DefaultTheme.colors,
    primary: "#007AFF",
    accent: "#03DAC6",
    background: "#F4F9FF",
    surface: "#FFFFFF",
    text: "#1C1C1E",
    placeholder: "#999999",
    disabled: "#BDBDBD",
  },
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F4F9FF",
    padding: 24,
    paddingTop: 50,
  },
  appName: {
    fontSize: 28,
    fontWeight: "700",
    color: "#007AFF",
    textAlign: "center",
    marginBottom: 30,
  },
  input: {
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 14,
    fontSize: 16,
    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 6,
    elevation: 2,
  },
  addBtn: {
    backgroundColor: "#007AFF",
    borderRadius: 14,
    paddingVertical: 12,
    justifyContent: "center",
    marginTop: 12,
  },
  sortRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginVertical: 20,
    alignItems: "center",
  },
  sortText: { fontSize: 16, color: "#007AFF", fontWeight: "600" },
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    marginBottom: 14,
    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 8,
    elevation: 4,
  },
  completedCard: { backgroundColor: "#ECECEC" },
  cardTitle: { fontSize: 18, fontWeight: "600", color: "#1C1C1E" },
  completedText: { textDecorationLine: "line-through", color: "#A4A4A4" },
  taskInfo: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: 12,
    paddingBottom: 12,
  },
  info: { fontSize: 14, color: "#6C6C6C" },
  empty: {
    textAlign: "center",
    color: "#999999",
    fontStyle: "italic",
    marginTop: 24,
  },
  popup: { backgroundColor: "#FFFFFF", borderRadius: 16, padding: 20 },
  popupContent: { alignItems: "center" },
});

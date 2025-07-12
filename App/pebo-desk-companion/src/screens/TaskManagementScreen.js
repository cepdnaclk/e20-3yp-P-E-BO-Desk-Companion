import React, { useEffect, useState, useRef } from "react";
import {
  View,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  Text,
  TextInput,
  ActivityIndicator,
  Animated,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Menu, Provider as PaperProvider } from "react-native-paper";
import DateTimePickerModal from "react-native-modal-datetime-picker";
import PopupModal from "../components/PopupModal";
import {
  auth,
  db,
  addTask,
  getTaskOverview,
  updateTask,
} from "../services/firebase";
import moment from "moment";

const TaskManagementScreen = () => {
  // State Management
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
  const [username, setUsername] = useState("");
  const [currentUser, setCurrentUser] = useState(null);
  const [showAddTask, setShowAddTask] = useState(false);
  const slideAnim = useRef(new Animated.Value(0)).current;

  // Check if required fields are filled for FAB icon
  const isFormComplete = task.trim() && deadline;

  // Authentication and Username Fetching
  useEffect(() => {
    let unsubscribeAuth;
    unsubscribeAuth = auth.onAuthStateChanged((user) => {
      console.log("Auth state changed:", user ? user.uid : null);
      setCurrentUser(user);
      setLoading(false);
    });
    return () => unsubscribeAuth && unsubscribeAuth();
  }, []);

  useEffect(() => {
    let unsubscribeUsername;
    if (currentUser?.uid) {
      const usernameRef = db.ref(`users/${currentUser.uid}/username`);
      unsubscribeUsername = usernameRef.on(
        "value",
        (snapshot) => {
          const fetchedUsername = snapshot?.exists() ? snapshot.val() : null;
          console.log("Firebase username:", fetchedUsername);
          setUsername(fetchedUsername || `user_${currentUser.uid.slice(0, 8)}`);
        },
        (error) => {
          console.error("Firebase username listener error:", error);
          setUsername(`user_${currentUser.uid.slice(0, 8)}`);
        }
      );
    }
    return () => unsubscribeUsername && unsubscribeUsername();
  }, [currentUser]);

  // Fetch and Sort Tasks
  useEffect(() => {
    if (currentUser?.uid) fetchAndSort();
  }, [sortPref, currentUser]);

  // Animation for Add Task Container
  useEffect(() => {
    Animated.timing(slideAnim, {
      toValue: showAddTask ? 1 : 0,
      duration: 300,
      useNativeDriver: true,
    }).start();
  }, [showAddTask]);

  const fetchAndSort = async () => {
    setLoading(true);
    try {
      const data = await getTaskOverview();
      console.log("Fetched tasks:", data);
      if (!Array.isArray(data)) throw new Error("Invalid task data");
      const order = { High: 0, Medium: 1, Low: 2 };
      const sorted = data.sort((a, b) => {
        if (sortPref === "priority")
          return order[a.priority] - order[b.priority];
        return new Date(a.deadline) - new Date(b.deadline);
      });
      setTasks(sorted);
    } catch (error) {
      console.error("Fetch tasks error:", error);
      showPopup("Error", "Failed to fetch tasks", "alert-circle");
    } finally {
      setLoading(false);
    }
  };

  // Task Management Functions
  const toggleCompleted = async (item) => {
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
  };

  const showPopup = (title, message, icon = "checkmark-circle") => {
    setPopupContent({ title, message, icon });
    setPopupVisible(true);
  };

  const addNew = async () => {
    if (!task.trim())
      return showPopup("Input Error", "Enter a task", "alert-circle");
    if (!deadline)
      return showPopup("Input Error", "Select deadline", "alert-circle");
    if (!username.trim())
      return showPopup(
        "Error",
        "Username not found. Please update your profile.",
        "alert-circle"
      );
    setAdding(true);
    try {
      await addTask({
        description: task.trim(),
        completed: false,
        deadline: deadline.toISOString(),
        category,
        priority,
        createdBy: username,
      });
      console.log("Added task with category:", category, "priority:", priority);
      setTask("");
      setDeadline(null);
      setCategory("Work");
      setPriority("Medium");
      setShowAddTask(false);
      await fetchAndSort();
      showPopup("Success", "Task added successfully", "checkmark-circle");
    } catch (error) {
      console.error("Add task error:", error);
      showPopup("Error", "Failed to add task", "alert-circle");
    } finally {
      setAdding(false);
    }
  };

  const handleFabPress = () => {
    if (showAddTask) {
      if (isFormComplete) {
        addNew();
      } else {
        setTask("");
        setDeadline(null);
        setCategory("Work");
        setPriority("Medium");
        setShowAddTask(false);
      }
    } else {
      setShowAddTask(true);
    }
  };

  // Render Helper Functions
  const renderMenu = (label, val, opts, vis, setVis, onSelect, icon) => (
    <Menu
      visible={vis}
      onDismiss={() => setVis(false)}
      anchor={
        <TouchableOpacity
          onPress={() => setVis(true)}
          style={styles.menuButton}
          accessibilityLabel={`Select ${label}`}
          accessibilityRole="button"
        >
          <Ionicons name={icon} size={18} color="#1976D2" />
          <Text style={[styles.menuLabel, val && styles.menuLabelSelected]}>
            {val || label}
          </Text>
          <Ionicons name="chevron-down" size={18} color="#1976D2" />
        </TouchableOpacity>
      }
      style={styles.menu}
    >
      {opts.map((o) => (
        <Menu.Item
          key={o}
          title={o}
          leadingIcon={o === val ? "check" : undefined}
          onPress={() => {
            console.log(`Selected ${label}:`, o);
            onSelect(o);
            setVis(false);
          }}
          titleStyle={
            o === val ? styles.menuItemTextSelected : styles.menuItemText
          }
          style={o === val ? styles.menuItemSelected : styles.menuItem}
        />
      ))}
    </Menu>
  );

  const renderTask = ({ item }) => (
    <View style={[styles.taskItem, item.completed && styles.completedItem]}>
      <View style={styles.taskHeader}>
        <Text
          style={[styles.taskTitle, item.completed && styles.completedText]}
          numberOfLines={2}
        >
          {item.description}
        </Text>
        <TouchableOpacity
          onPress={() => toggleCompleted(item)}
          accessibilityLabel={
            item.completed ? "Mark task incomplete" : "Mark task complete"
          }
          accessibilityRole="button"
        >
          <Ionicons
            name={item.completed ? "checkmark-circle" : "ellipse-outline"}
            size={22}
            color={item.completed ? "#4CAF50" : "#1976D2"}
          />
        </TouchableOpacity>
      </View>
      <Text style={styles.taskSubtitle}>
        By: {item.createdBy || "Unknown User"}
      </Text>
      <View style={styles.taskInfo}>
        <View style={styles.infoItem}>
          <Ionicons name="calendar-outline" size={14} color="#757575" />
          <Text style={styles.infoText}>
            {moment(item.deadline).format("DD MMM, hh:mm A")}
          </Text>
        </View>
        <View style={styles.infoItem}>
          <Ionicons name="alert-circle-outline" size={14} color="#757575" />
          <Text style={styles.infoText}>{item.priority || "N/A"}</Text>
        </View>
        <View style={styles.infoItem}>
          <Ionicons name="folder-outline" size={14} color="#757575" />
          <Text style={styles.infoText}>{item.category || "N/A"}</Text>
        </View>
      </View>
    </View>
  );

  return (
    <PaperProvider>
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>My Tasks</Text>
        </View>
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          style={{ flex: 1 }}
          keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 20}
        >
          {showAddTask && (
            <Animated.View
              style={{
                opacity: slideAnim,
                transform: [
                  {
                    translateY: slideAnim.interpolate({
                      inputRange: [0, 1],
                      outputRange: [50, 0],
                    }),
                  },
                ],
              }}
            >
              <View style={styles.inputCard}>
                <Text style={styles.sectionTitle}>Add New Task</Text>
                <View style={styles.inputRow}>
                  <Ionicons
                    name="create-outline"
                    size={20}
                    color="#1976D2"
                    style={styles.inputIcon}
                  />
                  <TextInput
                    placeholder="Task description"
                    value={task}
                    onChangeText={setTask}
                    style={[styles.input, !task.trim() && styles.inputError]}
                    placeholderTextColor="#757575"
                    accessibilityLabel="Task description"
                  />
                </View>
                <View style={styles.inputRow}>
                  <Ionicons
                    name="calendar-outline"
                    size={20}
                    color="#1976D2"
                    style={styles.inputIcon}
                  />
                  <TouchableOpacity
                    onPress={() => setPickerVisible(true)}
                    style={styles.dateButton}
                    accessibilityLabel="Select deadline"
                    accessibilityRole="button"
                  >
                    <Text
                      style={
                        deadline
                          ? styles.buttonLabel
                          : styles.buttonLabelPlaceholder
                      }
                    >
                      {deadline
                        ? moment(deadline).format("DD MMM YYYY, hh:mm A")
                        : "Select deadline & time"}
                    </Text>
                  </TouchableOpacity>
                </View>
                <View style={styles.filterRow}>
                  {renderMenu(
                    "Priority",
                    priority,
                    ["High", "Medium", "Low"],
                    showPriMenu,
                    setShowPriMenu,
                    setPriority,
                    "alert-circle-outline"
                  )}
                  {renderMenu(
                    "Category",
                    category,
                    ["Work", "Personal", "Study"],
                    showCatMenu,
                    setShowCatMenu,
                    setCategory,
                    "folder-outline"
                  )}
                </View>
              </View>
            </Animated.View>
          )}

          <DateTimePickerModal
            isVisible={isPickerVisible}
            mode="datetime"
            onConfirm={(date) => {
              setDeadline(date);
              setPickerVisible(false);
            }}
            onCancel={() => setPickerVisible(false)}
            buttonColor="#1976D2"
            confirmTextStyle={{ color: "#1976D2" }}
            cancelTextStyle={{ color: "#D32F2F" }}
            headerTextStyle={{ color: "#212121" }}
          />

          <View style={styles.filterBar}>
            <Text style={styles.sortTitle}>Sort By:</Text>
            {renderMenu(
              "Sort",
              sortPref.charAt(0).toUpperCase() + sortPref.slice(1),
              ["Deadline", "Priority"],
              showSortMenu,
              setShowSortMenu,
              (v) => setSortPref(v.toLowerCase()),
              "swap-vertical"
            )}
          </View>

          <View style={styles.taskListContainer}>
            {loading ? (
              <ActivityIndicator
                style={styles.loading}
                color="#1976D2"
                size="large"
              />
            ) : tasks.length === 0 ? (
              <View style={styles.emptyContainer}>
                <Text style={styles.emptyText}>
                  No tasks yet. Tap the "+" button to add one!
                </Text>
              </View>
            ) : (
              <FlatList
                data={tasks}
                renderItem={renderTask}
                keyExtractor={(item) => item.id}
                contentContainerStyle={styles.taskListContent}
                initialNumToRender={10}
              />
            )}
          </View>

          <TouchableOpacity
            style={[styles.fab, adding && styles.fabDisabled]}
            onPress={handleFabPress}
            disabled={adding}
            accessibilityLabel={
              showAddTask
                ? isFormComplete
                  ? "Add task"
                  : "Cancel"
                : "Add new task"
            }
            accessibilityRole="button"
          >
            {adding ? (
              <ActivityIndicator size="small" color="#FFFFFF" />
            ) : (
              <Ionicons
                name={
                  showAddTask ? (isFormComplete ? "checkmark" : "close") : "add"
                }
                size={32}
                color="#FFFFFF"
              />
            )}
          </TouchableOpacity>

          <PopupModal
            visible={popupVisible}
            onClose={() => setPopupVisible(false)}
            title={popupContent.title}
            message={popupContent.message}
            icon={popupContent.icon}
          />
        </KeyboardAvoidingView>
      </SafeAreaView>
    </PaperProvider>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F4F9FF",
    padding: 24,
  },
  header: {
    marginTop: 20,
    marginBottom: 20,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: "bold",
    color: "#1976D2",
    textAlign: "center",
  },
  inputCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    elevation: 3,
    shadowColor: "#000000",
    shadowOpacity: 0.1,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: "#1976D2",
    marginBottom: 12,
  },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#ECEFF1",
    borderRadius: 8,
    marginBottom: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  inputIcon: {
    marginRight: 8,
  },
  input: {
    flex: 1,
    backgroundColor: "transparent",
    fontSize: 14,
    color: "#212121",
  },
  inputError: {
    borderColor: "#D32F2F",
    borderWidth: 1,
  },
  dateButton: {
    flex: 1,
    backgroundColor: "transparent",
    paddingVertical: 10,
    justifyContent: "flex-start",
  },
  buttonLabel: {
    fontSize: 14,
    color: "#212121",
    fontWeight: "600",
  },
  buttonLabelPlaceholder: {
    fontSize: 14,
    color: "#757575",
    fontWeight: "500",
  },
  filterRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 8,
  },
  filterBar: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
    elevation: 3,
    shadowColor: "#000000",
    shadowOpacity: 0.1,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
  },
  sortTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#1976D2",
    marginRight: 8,
  },
  menuButton: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#ECEFF1",
    borderRadius: 8,
    paddingVertical: 6,
    paddingHorizontal: 10,
    flex: 1,
  },
  menuLabel: {
    fontSize: 14,
    color: "#212121",
    fontWeight: "600",
    marginRight: 4,
    flex: 1,
  },
  menuLabelSelected: {
    color: "#1976D2",
  },
  menu: {
    backgroundColor: "#FFFFFF",
    borderRadius: 8,
    elevation: 3,
    shadowColor: "#000000",
    shadowOpacity: 0.1,
    shadowRadius: 8,
    marginTop: 8,
  },
  menuItem: {
    backgroundColor: "#FFFFFF",
  },
  menuItemSelected: {
    backgroundColor: "#ECEFF1",
  },
  menuItemText: {
    fontSize: 14,
    color: "#212121",
    fontWeight: "500",
  },
  menuItemTextSelected: {
    fontSize: 14,
    color: "#1976D2",
    fontWeight: "600",
  },
  taskListContainer: {
    flex: 1,
  },
  taskListContent: {
    paddingBottom: 80,
  },
  taskItem: {
    backgroundColor: "#ECEFF1",
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
  },
  completedItem: {
    backgroundColor: "#F5F5F5",
  },
  taskHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  taskTitle: {
    fontSize: 14,
    fontWeight: "500",
    color: "#212121",
    flex: 1,
    marginRight: 8,
  },
  taskSubtitle: {
    fontSize: 12,
    color: "#757575",
    marginBottom: 8,
  },
  completedText: {
    textDecorationLine: "line-through",
    color: "#90A4AE",
  },
  taskInfo: {
    flexDirection: "row",
    justifyContent: "flex-start",
    flexWrap: "wrap",
    gap: 8,
  },
  infoItem: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderRadius: 8,
    paddingVertical: 4,
    paddingHorizontal: 8,
  },
  infoText: {
    fontSize: 12,
    color: "#757575",
    marginLeft: 4,
    flexShrink: 1,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#F5F5F5",
    borderRadius: 8,
    padding: 12,
  },
  emptyText: {
    fontSize: 14,
    color: "#757575",
    textAlign: "center",
    fontWeight: "500",
  },
  fab: {
    position: "absolute",
    bottom: 24,
    right: 24,
    backgroundColor: "#4CAF50",
    borderRadius: 32,
    width: 56,
    height: 56,
    justifyContent: "center",
    alignItems: "center",
    elevation: 5,
    shadowColor: "#000000",
    shadowOpacity: 0.1,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
  },
  fabDisabled: {
    backgroundColor: "#B0BEC5",
  },
  loading: {
    marginTop: 32,
  },
});

export default TaskManagementScreen;

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
  StatusBar,
  Pressable,
  Alert,
  Switch,
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
  deleteTask,
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
  const [editingTask, setEditingTask] = useState(null);
  const [reminderEnabled, setReminderEnabled] = useState(false);
  const [reminderTime1, setReminderTime1] = useState(30); // minutes before
  const [reminderTime2, setReminderTime2] = useState(5); // minutes before
  const [showReminderMenu1, setShowReminderMenu1] = useState(false);
  const [showReminderMenu2, setShowReminderMenu2] = useState(false);

  // Add state for delete confirmation
  const [deletePopupVisible, setDeletePopupVisible] = useState(false);
  const [taskToDelete, setTaskToDelete] = useState(null);

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

  const deleteTaskHandler = async (taskId) => {
    setTaskToDelete(taskId);
    setDeletePopupVisible(true);
  };

  const confirmDeleteTask = async () => {
    if (!taskToDelete) return;

    try {
      await deleteTask(taskToDelete);
      setTasks((ts) => ts.filter((t) => t.id !== taskToDelete));
      showPopup("Success", "Task deleted successfully", "checkmark-circle");
    } catch {
      showPopup("Error", "Failed to delete task", "alert-circle");
    } finally {
      setDeletePopupVisible(false);
      setTaskToDelete(null);
    }
  };

  const editTaskHandler = (item) => {
    setEditingTask(item);
    setTask(item.description);
    setDeadline(new Date(item.deadline));
    setCategory(item.category || "Work");
    setPriority(item.priority || "Medium");
    setReminderEnabled(item.reminderEnabled || false);
    setReminderTime1(item.reminderTime1 || 30);
    setReminderTime2(item.reminderTime2 || 5);
    setShowAddTask(true);
  };

  const showPopup = (title, message, icon = "checkmark-circle") => {
    setPopupContent({ title, message, icon });
    setPopupVisible(true);
  };

  const resetForm = () => {
    setTask("");
    setDeadline(null);
    setCategory("Work");
    setPriority("Medium");
    setReminderEnabled(false);
    setReminderTime1(30);
    setReminderTime2(5);
    setEditingTask(null);
    setShowAddTask(false);
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
      const taskData = {
        description: task.trim(),
        completed: false,
        deadline: deadline.toISOString(),
        category,
        priority,
        createdBy: username,
        reminderEnabled,
        reminderTime1,
        reminderTime2,
      };

      if (editingTask) {
        await updateTask(editingTask.id, taskData);
        showPopup("Success", "Task updated successfully", "checkmark-circle");
      } else {
        await addTask(taskData);
        showPopup("Success", "Task added successfully", "checkmark-circle");
      }

      resetForm();
      await fetchAndSort();
    } catch (error) {
      console.error("Add/Update task error:", error);
      showPopup(
        "Error",
        `Failed to ${editingTask ? "update" : "add"} task`,
        "alert-circle"
      );
    } finally {
      setAdding(false);
    }
  };

  const handleFabPress = () => {
    if (showAddTask) {
      if (isFormComplete) {
        addNew();
      } else {
        resetForm();
      }
    } else {
      setShowAddTask(true);
    }
  };

  // Get priority color
  const getPriorityColor = (priority) => {
    switch (priority) {
      case "High":
        return "#FF5252";
      case "Medium":
        return "#FF9800";
      case "Low":
        return "#4CAF50";
      default:
        return "#1DE9B6";
    }
  };

  // Get category icon
  const getCategoryIcon = (category) => {
    switch (category) {
      case "Work":
        return "briefcase-outline";
      case "Personal":
        return "person-outline";
      case "Study":
        return "book-outline";
      default:
        return "folder-outline";
    }
  };

  // Format reminder time
  const formatReminderTime = (minutes) => {
    if (minutes < 60) return `${minutes}min`;
    if (minutes < 1440) return `${Math.floor(minutes / 60)}hr`;
    return `${Math.floor(minutes / 1440)}day`;
  };

  // Reminder time options
  const reminderOptions = [
    { label: "5 minutes", value: 5 },
    { label: "10 minutes", value: 10 },
    { label: "15 minutes", value: 15 },
    { label: "30 minutes", value: 30 },
    { label: "1 hour", value: 60 },
    { label: "2 hours", value: 120 },
    { label: "1 day", value: 1440 },
  ];

  // Enhanced Render Menu Function with Better Labels
  const renderMenuWithLabel = (
    label,
    val,
    opts,
    vis,
    setVis,
    onSelect,
    icon
  ) => (
    <Menu
      visible={vis}
      onDismiss={() => setVis(false)}
      anchor={
        <Pressable
          onPress={() => setVis(true)}
          style={styles.menuButtonWithLabel}
          accessibilityLabel={`Select ${label}`}
          accessibilityRole="button"
        >
          <Ionicons name={icon} size={16} color="#1DE9B6" />
          <View style={styles.menuLabelContainer}>
            <Text style={styles.menuLabelText}>{label}</Text>
            <Text style={styles.menuValueText}>{val || `Select ${label}`}</Text>
          </View>
          <Ionicons name="chevron-down" size={16} color="#1DE9B6" />
        </Pressable>
      }
      contentStyle={styles.menu}
    >
      {opts.map((o) => (
        <Menu.Item
          key={o}
          onPress={() => {
            console.log(`Selected ${label}:`, o);
            onSelect(o);
            setVis(false);
          }}
          title={o}
          titleStyle={
            o === val ? styles.menuItemTextSelected : styles.menuItemText
          }
          style={o === val ? styles.menuItemSelected : styles.menuItem}
        />
      ))}
    </Menu>
  );

  const renderReminderMenu = (label, val, vis, setVis, onSelect, icon) => (
    <Menu
      visible={vis}
      onDismiss={() => setVis(false)}
      anchor={
        <Pressable
          onPress={() => setVis(true)}
          style={styles.reminderButton}
          accessibilityLabel={`Select ${label}`}
          accessibilityRole="button"
        >
          <Ionicons name={icon} size={16} color="#1DE9B6" />
          <Text style={styles.reminderLabel}>{formatReminderTime(val)}</Text>
          <Ionicons name="chevron-down" size={16} color="#1DE9B6" />
        </Pressable>
      }
      contentStyle={styles.menu}
    >
      {reminderOptions.map((o) => (
        <Menu.Item
          key={o.value}
          onPress={() => {
            onSelect(o.value);
            setVis(false);
          }}
          title={o.label}
          titleStyle={
            o.value === val ? styles.menuItemTextSelected : styles.menuItemText
          }
          style={o.value === val ? styles.menuItemSelected : styles.menuItem}
        />
      ))}
    </Menu>
  );

  const renderTask = ({ item }) => (
    <View style={[styles.taskItem, item.completed && styles.completedItem]}>
      <View style={styles.taskHeader}>
        <View style={styles.taskContent}>
          <Text
            style={[styles.taskTitle, item.completed && styles.completedText]}
          >
            {item.description}
          </Text>
          <Text style={styles.taskSubtitle}>
            By: {item.createdBy || "Unknown User"}
          </Text>
        </View>
        <View style={styles.taskActions}>
          <Pressable
            onPress={() => editTaskHandler(item)}
            style={styles.actionButton}
            accessibilityLabel="Edit task"
            accessibilityRole="button"
          >
            <Ionicons name="create-outline" size={20} color="#1DE9B6" />
          </Pressable>
          <Pressable
            onPress={() => deleteTaskHandler(item.id)}
            style={styles.actionButton}
            accessibilityLabel="Delete task"
            accessibilityRole="button"
          >
            <Ionicons name="trash-outline" size={20} color="#FF5252" />
          </Pressable>
          <Pressable
            onPress={() => toggleCompleted(item)}
            style={[
              styles.checkButton,
              item.completed && styles.checkButtonCompleted,
            ]}
            accessibilityLabel={
              item.completed ? "Mark task incomplete" : "Mark task complete"
            }
            accessibilityRole="button"
          >
            <Ionicons
              name={item.completed ? "checkmark" : "ellipse-outline"}
              size={20}
              color={item.completed ? "#0A0A0A" : "#1DE9B6"}
            />
          </Pressable>
        </View>
      </View>

      <View style={styles.taskInfo}>
        <View style={styles.infoItem}>
          <Ionicons name="time-outline" size={14} color="#888" />
          <Text style={styles.infoText}>
            {moment(item.deadline).format("DD MMM, hh:mm A")}
          </Text>
        </View>
        <View style={[styles.infoItem, styles.priorityItem]}>
          <View
            style={[
              styles.priorityDot,
              { backgroundColor: getPriorityColor(item.priority) },
            ]}
          />
          <Text style={styles.infoText}>{item.priority || "N/A"}</Text>
        </View>
        <View style={styles.infoItem}>
          <Ionicons
            name={getCategoryIcon(item.category)}
            size={14}
            color="#888"
          />
          <Text style={styles.infoText}>{item.category || "N/A"}</Text>
        </View>
        {item.reminderEnabled && (
          <View style={styles.infoItem}>
            <Ionicons name="notifications-outline" size={14} color="#1DE9B6" />
            <Text style={styles.infoText}>
              {formatReminderTime(item.reminderTime1)},{" "}
              {formatReminderTime(item.reminderTime2)}
            </Text>
          </View>
        )}
      </View>
    </View>
  );

  return (
    <PaperProvider>
      <StatusBar barStyle="light-content" backgroundColor="#0A0A0A" />
      <SafeAreaView style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>My Tasks</Text>
          <View style={styles.headerStats}>
            <Text style={styles.statsText}>
              {tasks.filter((t) => !t.completed).length} pending
            </Text>
          </View>
        </View>

        <KeyboardAvoidingView
          style={styles.content}
          behavior={Platform.OS === "ios" ? "padding" : "height"}
        >
          {/* Add Task Section */}
          {showAddTask && (
            <Animated.View
              style={[
                styles.addTaskContainer,
                {
                  opacity: slideAnim,
                  transform: [
                    {
                      translateY: slideAnim.interpolate({
                        inputRange: [0, 1],
                        outputRange: [-20, 0],
                      }),
                    },
                  ],
                },
              ]}
            >
              <View style={styles.addTaskHeader}>
                <Text style={styles.addTaskTitle}>
                  {editingTask ? "Edit Task" : "Add New Task"}
                </Text>
                <Pressable onPress={resetForm} style={styles.closeButton}>
                  <Ionicons name="close" size={20} color="#888" />
                </Pressable>
              </View>

              <View style={styles.inputWrapper}>
                <Ionicons
                  name="document-text-outline"
                  size={20}
                  color="#1DE9B6"
                />
                <TextInput
                  placeholder="Enter task description..."
                  value={task}
                  onChangeText={setTask}
                  style={styles.input}
                  placeholderTextColor="#888"
                  multiline
                />
              </View>

              <Pressable
                onPress={() => setPickerVisible(true)}
                style={styles.inputWrapper}
              >
                <Ionicons name="calendar-outline" size={20} color="#1DE9B6" />
                <Text style={[styles.input, !deadline && styles.placeholder]}>
                  {deadline
                    ? moment(deadline).format("DD MMM YYYY, hh:mm A")
                    : "Select deadline & time"}
                </Text>
              </Pressable>

              <View style={styles.menuRow}>
                {renderMenuWithLabel(
                  "Priority",
                  priority,
                  ["High", "Medium", "Low"],
                  showPriMenu,
                  setShowPriMenu,
                  setPriority,
                  "alert-circle-outline"
                )}
                {renderMenuWithLabel(
                  "Category",
                  category,
                  ["Work", "Personal", "Study"],
                  showCatMenu,
                  setShowCatMenu,
                  setCategory,
                  "folder-outline"
                )}
              </View>

              {/* Reminder Section */}
              <View style={styles.reminderSection}>
                <View style={styles.reminderToggle}>
                  <Ionicons
                    name="notifications-outline"
                    size={20}
                    color="#1DE9B6"
                  />
                  <Text style={styles.reminderToggleText}>
                    Enable Reminders
                  </Text>
                  <Switch
                    value={reminderEnabled}
                    onValueChange={setReminderEnabled}
                    trackColor={{ false: "#333", true: "#1DE9B6" }}
                    thumbColor={reminderEnabled ? "#0A0A0A" : "#888"}
                  />
                </View>

                {reminderEnabled && (
                  <View style={styles.reminderTimesContainer}>
                    <Text style={styles.reminderTimesLabel}>
                      Remind me before:
                    </Text>
                    <View style={styles.reminderTimesRow}>
                      {renderReminderMenu(
                        "First Reminder",
                        reminderTime1,
                        showReminderMenu1,
                        setShowReminderMenu1,
                        setReminderTime1,
                        "time-outline"
                      )}
                      {renderReminderMenu(
                        "Second Reminder",
                        reminderTime2,
                        showReminderMenu2,
                        setShowReminderMenu2,
                        setReminderTime2,
                        "time-outline"
                      )}
                    </View>
                  </View>
                )}
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
            minimumDate={new Date()}
            isDarkModeEnabled={true}
            themeVariant="dark"
          />

          {/* Filter Bar */}
          <View style={styles.filterBar}>
            <View style={styles.filterLeft}>
              <Ionicons name="filter-outline" size={20} color="#1DE9B6" />
              <Text style={styles.filterTitle}>Sort By:</Text>
            </View>
            {renderMenuWithLabel(
              "Sort",
              sortPref === "deadline"
                ? "Deadline"
                : sortPref === "priority"
                ? "Priority"
                : null,
              ["Deadline", "Priority"],
              showSortMenu,
              setShowSortMenu,
              (v) => setSortPref(v.toLowerCase()),
              "swap-vertical"
            )}
          </View>

          {/* Task List */}
          <View style={styles.taskListContainer}>
            {loading ? (
              <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color="#1DE9B6" />
                <Text style={styles.loadingText}>Loading tasks...</Text>
              </View>
            ) : tasks.length === 0 ? (
              <View style={styles.emptyContainer}>
                <Ionicons name="clipboard-outline" size={48} color="#555" />
                <Text style={styles.emptyText}>No tasks yet</Text>
                <Text style={styles.emptySubtext}>
                  Tap the "+" button to add your first task!
                </Text>
              </View>
            ) : (
              <FlatList
                data={tasks}
                renderItem={renderTask}
                keyExtractor={(item) => item.id}
                contentContainerStyle={styles.taskListContent}
                showsVerticalScrollIndicator={false}
                initialNumToRender={10}
              />
            )}
          </View>

          {/* Floating Action Button */}
          <Pressable
            style={[
              styles.fab,
              showAddTask && !isFormComplete && styles.fabClose,
              showAddTask && isFormComplete && styles.fabSave,
            ]}
            onPress={handleFabPress}
          >
            {adding ? (
              <ActivityIndicator size="small" color="#0A0A0A" />
            ) : (
              <Ionicons
                name={
                  showAddTask ? (isFormComplete ? "checkmark" : "close") : "add"
                }
                size={24}
                color="#0A0A0A"
              />
            )}
          </Pressable>

          {/* Regular Success/Error Popup */}
          <PopupModal
            visible={popupVisible}
            onClose={() => setPopupVisible(false)}
            title={popupContent.title}
            message={popupContent.message}
            icon={popupContent.icon}
          />

          {/* Delete Confirmation Popup */}
          <PopupModal
            visible={deletePopupVisible}
            onClose={() => {
              setDeletePopupVisible(false);
              setTaskToDelete(null);
            }}
            title="Delete Task"
            message="Are you sure you want to delete this task? This action cannot be undone."
            icon="trash-outline"
            showButtons={true}
            onConfirm={confirmDeleteTask}
            onCancel={() => {
              setDeletePopupVisible(false);
              setTaskToDelete(null);
            }}
            confirmText="Delete"
            cancelText="Cancel"
          />
        </KeyboardAvoidingView>
      </SafeAreaView>
    </PaperProvider>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0A0A0A",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 24,
    paddingTop: 60,
    paddingBottom: 20,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(29, 233, 182, 0.1)",
  },
  headerTitle: {
    fontSize: 32,
    fontWeight: "bold",
    color: "#FFFFFF",
  },
  headerStats: {
    alignItems: "flex-end",
  },
  statsText: {
    fontSize: 14,
    color: "#888",
    fontWeight: "500",
  },
  content: {
    flex: 1,
    padding: 24,
  },
  addTaskContainer: {
    backgroundColor: "#1A1A1A",
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)"
  },
  addTaskHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16
  },
  addTaskTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: "#FFFFFF",
  },
  closeButton: {
    padding: 4,
  },
  inputWrapper: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#0A0A0A",
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  input: {
    flex: 1,
    color: "#FFFFFF",
    fontSize: 16,
    marginLeft: 12,
  },
  placeholder: {
    color: "#888",
  },
  menuRow: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 16,
  },
  menuButtonWithLabel: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#0A0A0A",
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    flex: 1,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
    minHeight: 56,
  },
  menuLabelContainer: {
    flex: 1,
    marginLeft: 8,
    marginRight: 8,
    justifyContent: "center", // Add this
  },
  menuLabelText: {
    fontSize: 12,
    color: "#888",
    marginBottom: 2,
    lineHeight: 14, // Add this
  },
  menuValueText: {
    fontSize: 14,
    color: "#FFFFFF",
    fontWeight: "500",
    lineHeight: 16, // Add this
  },

  reminderSection: {
    backgroundColor: "#0A0A0A",
    borderRadius: 12,
    padding: 16,
    marginTop: 20,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  reminderToggle: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  reminderToggleText: {
    fontSize: 16,
    color: "#FFFFFF",
    marginLeft: 8,
    flex: 1,
  },
  reminderTimesContainer: {
    marginTop: 16,
  },
  reminderTimesLabel: {
    fontSize: 14,
    color: "#888",
    marginBottom: 8,
  },
  reminderTimesRow: {
    flexDirection: "row",
    gap: 12,
  },
  reminderButton: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#1A1A1A",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    flex: 1,
    width: 100,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  reminderLabel: {
    fontSize: 12,
    height: 17,
    justifyContent: "center",
    alignItems: "center",
    color: "#FFFFFF",
    marginLeft: 6,
    marginRight: 6,
    flex: 1,
  },
  menu: {
    backgroundColor: "#1A1A1A",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  menuItem: {
    backgroundColor: "transparent",
  },
  menuItemSelected: {
    backgroundColor: "rgba(29, 233, 182, 0.1)",
  },
  menuItemText: {
    color: "#FFFFFF",
    fontSize: 14,
  },
  menuItemTextSelected: {
    color: "#1DE9B6",
    fontSize: 14,
    fontWeight: "600",
  },
  filterBar: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "#1A1A1A",
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  filterLeft: {
    flexDirection: "row",
    alignItems: "center",
  },
  filterTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#FFFFFF",
    marginLeft: 8,
  },
  taskListContainer: {
    flex: 1,
  },
  taskListContent: {
    paddingBottom: 100,
  },
  taskItem: {
    backgroundColor: "#1A1A1A",
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  completedItem: {
    backgroundColor: "#0F0F0F",
    borderColor: "rgba(255, 255, 255, 0.1)",
  },
  taskHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 12,
  },
  taskContent: {
    flex: 1,
    marginRight: 12,
  },
  taskTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#FFFFFF",
    marginBottom: 4,
    lineHeight: 22,
  },
  completedText: {
    textDecorationLine: "line-through",
    color: "#888",
  },
  taskSubtitle: {
    fontSize: 12,
    color: "#888",
  },
  taskActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  actionButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "rgba(29, 233, 182, 0.1)",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  checkButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "rgba(29, 233, 182, 0.1)",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#1DE9B6",
  },
  checkButtonCompleted: {
    backgroundColor: "#1DE9B6",
    borderColor: "#1DE9B6",
  },
  taskInfo: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  infoItem: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#0A0A0A",
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  priorityItem: {
    paddingLeft: 6,
  },
  priorityDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  infoText: {
    fontSize: 12,
    color: "#888",
    marginLeft: 4,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingVertical: 40,
  },
  loadingText: {
    fontSize: 16,
    color: "#888",
    marginTop: 12,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingVertical: 40,
  },
  emptyText: {
    fontSize: 18,
    color: "#FFFFFF",
    marginTop: 16,
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 14,
    color: "#888",
    textAlign: "center",
  },
  fab: {
    position: "absolute",
    bottom: 24,
    right: 24,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: "#1DE9B6",
    justifyContent: "center",
    alignItems: "center",
    elevation: 8,
    shadowColor: "#000",
    shadowOpacity: 0.3,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
  },
  fabClose: {
    backgroundColor: "#FF5252",
  },
  fabSave: {
    backgroundColor: "#4CAF50",
  },
});

export default TaskManagementScreen;

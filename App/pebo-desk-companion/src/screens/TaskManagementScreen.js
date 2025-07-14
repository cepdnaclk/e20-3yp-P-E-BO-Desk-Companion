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
  Dimensions,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Menu, Provider as PaperProvider } from "react-native-paper";
import { LinearGradient } from "expo-linear-gradient";
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

const { width, height } = Dimensions.get("window");

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
  const [reminderTime1, setReminderTime1] = useState(30);
  const [reminderTime2, setReminderTime2] = useState(5);
  const [showReminderMenu1, setShowReminderMenu1] = useState(false);
  const [showReminderMenu2, setShowReminderMenu2] = useState(false);
  const [deletePopupVisible, setDeletePopupVisible] = useState(false);
  const [taskToDelete, setTaskToDelete] = useState(null);
  const [customCategories, setCustomCategories] = useState([]);
  const [newCategoryInput, setNewCategoryInput] = useState("");
  const [showAddCategoryInput, setShowAddCategoryInput] = useState(false);

  // Animation refs for futuristic effects
  const slideAnim = useRef(new Animated.Value(0)).current;
  const pulse = useRef(new Animated.Value(0)).current;
  const glow = useRef(new Animated.Value(0)).current;

  // Futuristic animations
  useEffect(() => {
    // Pulsing animation for interactive elements
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1,
          duration: 2000,
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 0,
          duration: 2000,
          useNativeDriver: true,
        }),
      ])
    ).start();

    // Glowing effect
    Animated.loop(
      Animated.sequence([
        Animated.timing(glow, {
          toValue: 1,
          duration: 2500,
          useNativeDriver: true,
        }),
        Animated.timing(glow, {
          toValue: 0,
          duration: 2500,
          useNativeDriver: true,
        }),
      ])
    ).start();
  }, []);

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

  // Fetch custom categories
  useEffect(() => {
    if (currentUser?.uid) {
      const categoriesRef = db.ref(`users/${currentUser.uid}/customCategories`);
      categoriesRef.on("value", (snapshot) => {
        const categories = snapshot.val() || [];
        setCustomCategories(Array.isArray(categories) ? categories : []);
      });
    }
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
    setShowAddCategoryInput(false);
    setNewCategoryInput("");
  };

  const addCustomCategory = async () => {
    if (!newCategoryInput.trim()) return;

    const newCategory = newCategoryInput.trim();
    if (getAllCategories().includes(newCategory)) {
      showPopup("Error", "Category already exists", "alert-circle");
      return;
    }

    try {
      const updatedCategories = [...customCategories, newCategory];
      await db
        .ref(`users/${currentUser.uid}/customCategories`)
        .set(updatedCategories);
      setCustomCategories(updatedCategories);
      setCategory(newCategory);
      setNewCategoryInput("");
      setShowAddCategoryInput(false);
      showPopup("Success", "Category added successfully", "checkmark-circle");
    } catch (error) {
      showPopup("Error", "Failed to add category", "alert-circle");
    }
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

  // Get all categories (default + custom)
  const getAllCategories = () => {
    const defaultCategories = ["Work", "Personal", "Study"];
    return [...defaultCategories, ...customCategories];
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

  // Get category icon with emojis for custom categories
  const getCategoryIcon = (category) => {
    switch (category) {
      case "Work":
        return "briefcase-outline";
      case "Personal":
        return "person-outline";
      case "Study":
        return "book-outline";
      default:
        // For custom categories, return a generic icon
        return "folder-outline";
    }
  };

  // Get category emoji for display
  const getCategoryEmoji = (category) => {
    switch (category) {
      case "Work":
        return "💼";
      case "Personal":
        return "👤";
      case "Study":
        return "📚";
      case "Health":
        return "🏥";
      case "Finance":
        return "💰";
      case "Travel":
        return "✈️";
      case "Shopping":
        return "🛒";
      case "Home":
        return "🏠";
      case "Fitness":
        return "💪";
      case "Entertainment":
        return "🎬";
      default:
        return "📁";
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

  // Enhanced Category Menu with Add New Option
  const renderCategoryMenu = () => (
    <Menu
      visible={showCatMenu}
      onDismiss={() => setShowCatMenu(false)}
      anchor={
        <Pressable
          onPress={() => setShowCatMenu(true)}
          style={styles.menuButtonWithLabel}
          accessibilityLabel="Select Category"
          accessibilityRole="button"
        >
          <Ionicons name="folder-outline" size={16} color="#1DE9B6" />
          <View style={styles.menuLabelContainer}>
            <Text style={styles.menuLabelText}>Category</Text>
            <Text style={styles.menuValueText}>
              {getCategoryEmoji(category)} {category}
            </Text>
          </View>
          <Ionicons name="chevron-down" size={16} color="#1DE9B6" />
        </Pressable>
      }
      contentStyle={styles.menu}
    >
      {getAllCategories().map((cat) => (
        <Menu.Item
          key={cat}
          onPress={() => {
            setCategory(cat);
            setShowCatMenu(false);
          }}
          title={`${getCategoryEmoji(cat)} ${cat}`}
          titleStyle={
            cat === category ? styles.menuItemTextSelected : styles.menuItemText
          }
          style={cat === category ? styles.menuItemSelected : styles.menuItem}
        />
      ))}
      <Menu.Item
        onPress={() => {
          setShowCatMenu(false);
          setShowAddCategoryInput(true);
        }}
        title="➕ Add New Category"
        titleStyle={styles.menuItemText}
        style={styles.menuItem}
      />
    </Menu>
  );

  // Fixed Reminder Menu Function
  const renderReminderMenu = (label, val, vis, setVis, onSelect, icon) => (
    <Menu
      visible={vis}
      onDismiss={() => setVis(false)}
      anchor={
        <Pressable
          onPress={() => setVis(true)}
          style={styles.reminderMenuButton}
          accessibilityLabel={`Select ${label}`}
          accessibilityRole="button"
        >
          <Ionicons name={icon} size={16} color="#1DE9B6" />
          <View style={styles.reminderLabelContainer}>
            <Text style={styles.reminderLabelText}>{label}</Text>
            <View style={styles.reminderValueContainer}>
              <Ionicons
                name={val >= 1440 ? "calendar" : val >= 60 ? "time" : "flash"}
                size={12}
                color="#1DE9B6"
                style={styles.reminderValueIcon}
              />
              <Text style={styles.reminderValueText}>
                {formatReminderTime(val)}
              </Text>
            </View>
          </View>
          <Ionicons name="chevron-down" size={16} color="#1DE9B6" />
        </Pressable>
      }
      contentStyle={styles.menu}
    >
      {reminderOptions.map((option) => (
        <Menu.Item
          key={option.value}
          onPress={() => {
            onSelect(option.value);
            setVis(false);
          }}
          title={option.label}
          titleStyle={
            option.value === val
              ? styles.menuItemTextSelected
              : styles.menuItemText
          }
          style={
            option.value === val ? styles.menuItemSelected : styles.menuItem
          }
        />
      ))}
    </Menu>
  );

  const renderTask = ({ item }) => (
    <Animated.View
      style={[
        styles.taskItem,
        item.completed && styles.completedItem,
        {
          shadowOpacity: pulse.interpolate({
            inputRange: [0, 1],
            outputRange: [0.1, 0.3],
          }),
        },
      ]}
    >
      <LinearGradient
        colors={
          item.completed
            ? ["rgba(26, 26, 26, 0.8)", "rgba(26, 26, 26, 0.4)"]
            : ["rgba(26, 26, 26, 0.8)", "rgba(26, 26, 26, 0.4)"]
        }
        style={styles.taskGradient}
      >
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
                color={item.completed ? "#000000" : "#1DE9B6"}
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
            <Animated.View
              style={[
                styles.priorityDot,
                {
                  backgroundColor: getPriorityColor(item.priority),
                  opacity: pulse.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0.7, 1],
                  }),
                },
              ]}
            />
            <Text style={styles.infoText}>{item.priority || "N/A"}</Text>
          </View>
          <View style={styles.infoItem}>
            <Text style={styles.categoryEmoji}>
              {getCategoryEmoji(item.category)}
            </Text>
            <Text style={styles.infoText}>{item.category || "N/A"}</Text>
          </View>
          {item.reminderEnabled && (
            <View style={styles.infoItem}>
              <Ionicons
                name="notifications-outline"
                size={14}
                color="#1DE9B6"
              />
              <Text style={styles.infoText}>
                {formatReminderTime(item.reminderTime1)},{" "}
                {formatReminderTime(item.reminderTime2)}
              </Text>
            </View>
          )}
        </View>
      </LinearGradient>
    </Animated.View>
  );

  return (
    <PaperProvider>
      <StatusBar barStyle="light-content" backgroundColor="#000000" />
      <SafeAreaView style={styles.container}>
        {/* Futuristic Background Effects */}
        <View style={styles.backgroundContainer}>
          <Animated.View
            style={[
              styles.backgroundOrb1,
              {
                opacity: glow.interpolate({
                  inputRange: [0, 1],
                  outputRange: [0.1, 0.3],
                }),
              },
            ]}
          />
          <Animated.View
            style={[
              styles.backgroundOrb2,
              {
                opacity: pulse.interpolate({
                  inputRange: [0, 1],
                  outputRange: [0.05, 0.2],
                }),
              },
            ]}
          />
        </View>

        {/* Header with Gradient */}
        <LinearGradient
          colors={["rgba(29, 233, 182, 0.2)", "transparent"]}
          style={styles.header}
        >
          <View style={styles.headerContent}>
            <Text style={styles.headerTitle}>TASK MANAGER</Text>
            <Text style={styles.headerSubtitle}>
              Task and Reminders Control Center
            </Text>
          </View>
          <Animated.View
            style={[
              styles.headerStats,
              {
                shadowOpacity: glow.interpolate({
                  inputRange: [0, 1],
                  outputRange: [0.3, 0.8],
                }),
              },
            ]}
          >
            <Text style={styles.statsText}>
              {tasks.filter((t) => !t.completed).length} ACTIVE
            </Text>
            <Text style={styles.statsSubtext}>TASKS</Text>
          </Animated.View>
        </LinearGradient>

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
              <LinearGradient
                colors={["rgba(26, 26, 26, 0.8)", "rgba(26, 26, 26, 0.4)"]}
                style={styles.addTaskGradient}
              >
                <View style={styles.addTaskHeader}>
                  <Text style={styles.addTaskTitle}>
                    <Ionicons
                      name="add-circle-outline"
                      size={20}
                      color="#1DE9B6"
                    />
                    {editingTask ? " EDIT TASK" : " NEW TASK"}
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

                {/* Add New Category Input */}
                {showAddCategoryInput && (
                  <View style={styles.addCategoryContainer}>
                    <View style={styles.inputWrapper}>
                      <Ionicons name="add-outline" size={20} color="#1DE9B6" />
                      <TextInput
                        placeholder="Enter new category name..."
                        value={newCategoryInput}
                        onChangeText={setNewCategoryInput}
                        style={styles.input}
                        placeholderTextColor="#888"
                        onSubmitEditing={addCustomCategory}
                      />
                    </View>
                    <View style={styles.addCategoryButtons}>
                      <Pressable
                        onPress={addCustomCategory}
                        style={styles.addCategoryButton}
                      >
                        <Text style={styles.addCategoryButtonText}>Add</Text>
                      </Pressable>
                      <Pressable
                        onPress={() => {
                          setShowAddCategoryInput(false);
                          setNewCategoryInput("");
                        }}
                        style={[styles.addCategoryButton, styles.cancelButton]}
                      >
                        <Text style={styles.addCategoryButtonText}>Cancel</Text>
                      </Pressable>
                    </View>
                  </View>
                )}

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
                  {renderCategoryMenu()}
                </View>

                {/* Reminder Section */}
                <View style={styles.reminderSection}>
                  <View style={styles.reminderToggle}>
                    <Ionicons
                      name="notifications-outline"
                      size={20}
                      color="#1DE9B6"
                    />
                    <Text style={styles.reminderToggleText}>ENABLE ALERTS</Text>
                    <Switch
                      value={reminderEnabled}
                      onValueChange={setReminderEnabled}
                      trackColor={{ false: "#333", true: "#1DE9B6" }}
                      thumbColor={reminderEnabled ? "#000000" : "#888"}
                    />
                  </View>

                  {reminderEnabled && (
                    <View style={styles.reminderTimesContainer}>
                      <Text style={styles.reminderTimesLabel}>
                        ALERT SCHEDULE:
                      </Text>
                      <View style={styles.reminderTimesRow}>
                        {renderReminderMenu(
                          "Primary Alert",
                          reminderTime1,
                          showReminderMenu1,
                          setShowReminderMenu1,
                          setReminderTime1,
                          "alarm-outline"
                        )}
                        {renderReminderMenu(
                          "Secondary Alert",
                          reminderTime2,
                          showReminderMenu2,
                          setShowReminderMenu2,
                          setReminderTime2,
                          "notifications-outline"
                        )}
                      </View>
                    </View>
                  )}
                </View>
              </LinearGradient>
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
          <LinearGradient
            colors={["rgba(26, 26, 26, 0.8)", "rgba(26, 26, 26, 0.4)"]}
            style={styles.filterBar}
          >
            <View style={styles.filterLeft}>
              <Ionicons name="filter-outline" size={20} color="#1DE9B6" />
              <Text style={styles.filterTitle}>SORT TASKS:</Text>
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
          </LinearGradient>

          {/* Task List */}
          <View style={styles.taskListContainer}>
            {loading ? (
              <View style={styles.loadingContainer}>
                <Animated.View
                  style={[
                    styles.loadingSpinner,
                    {
                      opacity: pulse.interpolate({
                        inputRange: [0, 1],
                        outputRange: [0.5, 1],
                      }),
                    },
                  ]}
                >
                  <ActivityIndicator size="large" color="#1DE9B6" />
                </Animated.View>
                <Text style={styles.loadingText}>LOADING TASKS...</Text>
              </View>
            ) : tasks.length === 0 ? (
              <View style={styles.emptyContainer}>
                <Ionicons name="clipboard-outline" size={48} color="#555" />
                <Text style={styles.emptyText}>NO ACTIVE TASKS</Text>
                <Text style={styles.emptySubtext}>
                  Tap the "+" button to create your first task!
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
          <Animated.View
            style={[
              styles.fab,
              showAddTask && !isFormComplete && styles.fabClose,
              showAddTask && isFormComplete && styles.fabSave,
              {
                shadowOpacity: glow.interpolate({
                  inputRange: [0, 1],
                  outputRange: [0.3, 0.8],
                }),
              },
            ]}
          >
            <Pressable style={styles.fabButton} onPress={handleFabPress}>
              <LinearGradient
                colors={
                  showAddTask
                    ? isFormComplete
                      ? ["#4CAF50", "#45A049"]
                      : ["#FF5252", "#F44336"]
                    : ["#1DE9B6", "#00BFA5"]
                }
                style={styles.fabGradient}
              >
                {adding ? (
                  <ActivityIndicator size="small" color="#000000" />
                ) : (
                  <Ionicons
                    name={
                      showAddTask
                        ? isFormComplete
                          ? "checkmark"
                          : "close"
                        : "add"
                    }
                    size={24}
                    color="#000000"
                  />
                )}
              </LinearGradient>
            </Pressable>
          </Animated.View>

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
    backgroundColor: "#000000",
  },
  backgroundContainer: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 0,
  },
  backgroundOrb1: {
    position: "absolute",
    top: 100,
    left: 50,
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: "rgba(29, 233, 182, 0.1)",
  },
  backgroundOrb2: {
    position: "absolute",
    top: 300,
    right: 30,
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: "rgba(255, 82, 82, 0.1)",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 24,
    paddingTop: 60,
    paddingBottom: 20,
    zIndex: 1,
  },
  headerContent: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 32,
    fontWeight: "900",
    color: "#FFFFFF",
    letterSpacing: 2,
    textShadowColor: "#1DE9B6",
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 10,
  },
  headerSubtitle: {
    fontSize: 12,
    color: "#1DE9B6",
    marginTop: 4,
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  headerStats: {
    alignItems: "flex-end",
    backgroundColor: "rgba(26, 26, 26, 0.3)",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
    shadowColor: "#1DE9B6",
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 10,
  },
  statsText: {
    fontSize: 16,
    color: "#1DE9B6",
    fontWeight: "900",
    letterSpacing: 1,
  },
  statsSubtext: {
    fontSize: 10,
    color: "#888",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  content: {
    flex: 1,
    padding: 24,
    zIndex: 1,
  },
  addTaskContainer: {
    marginBottom: 20,
    borderRadius: 16,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  addTaskGradient: {
    padding: 20,
  },
  addTaskHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
  },
  addTaskTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#FFFFFF",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  closeButton: {
    padding: 4,
  },
  inputWrapper: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(0, 0, 0, 0.5)",
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
    fontWeight: "500",
  },
  placeholder: {
    color: "#888",
  },
  addCategoryContainer: {
    marginBottom: 12,
  },
  addCategoryButtons: {
    flexDirection: "row",
    gap: 8,
    marginTop: 8,
  },
  addCategoryButton: {
    backgroundColor: "#1DE9B6",
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    flex: 1,
    alignItems: "center",
  },
  cancelButton: {
    backgroundColor: "#FF5252",
  },
  addCategoryButtonText: {
    color: "#000000",
    fontWeight: "600",
    fontSize: 14,
  },
  menuRow: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 16,
  },
  menuButtonWithLabel: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(0, 0, 0, 0.5)",
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    flex: 1,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
    minHeight: 56,
    minWidth: 150,
  },
  menuLabelContainer: {
    flex: 1,
    marginLeft: 7,
    marginRight: 7,
    justifyContent: "center",
  },
  menuLabelText: {
    fontSize: 12,
    color: "#888",
    marginBottom: 2,
    lineHeight: 14,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  menuValueText: {
    fontSize: 17,
    color: "#FFFFFF",
    fontWeight: "600",
    lineHeight: 16,
  },
  reminderSection: {
    minHeight: 160,
    backgroundColor: "rgba(0, 0, 0, 0.5)",
    borderRadius: 12,
    padding: 16,
    marginTop: 28,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  reminderToggle: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  reminderToggleText: {
    fontSize: 14,
    color: "#FFFFFF",
    marginLeft: 8,
    flex: 1,
    fontWeight: "600",
    letterSpacing: 0.5,
    textTransform: "uppercase",
  },
  reminderTimesContainer: {
    marginTop: 16,
  },
  reminderTimesLabel: {
    fontSize: 12,
    // height: 16,
    color: "#888",
    marginBottom: 12,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  reminderTimesRow: {
    flexDirection: "row",
    gap: 12,
  },
  reminderMenuButton: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(26, 26, 26, 0.8)",
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    flex: 1,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
    minHeight: 50,
    minWidth: 140,
  },
  reminderLabelContainer: {
    flex: 1,
    marginLeft: 8,
    // minHeight: 196,
    marginRight: 8,
    justifyContent: "center",
  },
  reminderLabelText: {
    fontSize: 12,
    color: "#888",
    marginBottom: 2,
    lineHeight: 14,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  reminderValueContainer: {
    flexDirection: "row",
    alignItems: "center",
  },
  reminderValueIcon: {
    marginRight: 6,
  },
  reminderValueText: {
    fontSize: 14,
    color: "#FFFFFF",
    fontWeight: "600",
    lineHeight: 16,
  },
  menu: {
    backgroundColor: "rgba(26, 26, 26, 0.95)",
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
    fontWeight: "500",
  },
  menuItemTextSelected: {
    color: "#1DE9B6",
    fontSize: 14,
    fontWeight: "700",
  },
  filterBar: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
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
    fontSize: 14,
    fontWeight: "700",
    color: "#FFFFFF",
    marginLeft: 8,
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  taskListContainer: {
    flex: 1,
  },
  taskListContent: {
    paddingBottom: 100,
  },
  taskItem: {
    marginBottom: 12,
    borderRadius: 16,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
    shadowColor: "#1DE9B6",
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 10,
  },
  taskGradient: {
    padding: 16,
  },
  completedItem: {
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
    textTransform: "uppercase",
    letterSpacing: 0.5,
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
    backgroundColor: "rgba(0, 0, 0, 0.3)",
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.1)",
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
  categoryEmoji: {
    fontSize: 14,
    marginRight: 4,
  },
  infoText: {
    fontSize: 12,
    color: "#888",
    marginLeft: 4,
    fontWeight: "500",
  },
  loadingContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingVertical: 40,
  },
  loadingSpinner: {
    marginBottom: 12,
  },
  loadingText: {
    fontSize: 14,
    color: "#888",
    fontWeight: "600",
    letterSpacing: 1,
    textTransform: "uppercase",
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
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  emptySubtext: {
    fontSize: 14,
    color: "#888",
    textAlign: "center",
    fontWeight: "500",
  },
  fab: {
    position: "absolute",
    bottom: 24,
    right: 24,
    width: 56,
    height: 56,
    borderRadius: 28,
    elevation: 8,
    shadowColor: "#1DE9B6",
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 20,
  },
  fabButton: {
    width: "100%",
    height: "100%",
    borderRadius: 28,
    overflow: "hidden",
  },
  fabGradient: {
    width: "100%",
    height: "100%",
    justifyContent: "center",
    alignItems: "center",
  },
  fabClose: {
    shadowColor: "#FF5252",
  },
  fabSave: {
    shadowColor: "#4CAF50",
  },
});

export default TaskManagementScreen;

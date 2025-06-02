import React, { useEffect, useState, useRef } from "react";
import React, { useEffect, useState, useRef } from "react";
import {
  View,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Dimensions,
  SafeAreaView,
  TouchableOpacity,
  Image,
  Animated,
  TouchableOpacity,
  Image,
  Animated,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Ionicons } from "@expo/vector-icons";
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
import {
  auth,
  db,
  addTask,
  getTaskOverview,
  updateTask,
} from "../services/firebase";
import {
  auth,
  db,
  addTask,
  getTaskOverview,
  updateTask,
} from "../services/firebase";
import moment from "moment";

const { width } = Dimensions.get("window");

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
        >
          <Ionicons
            name={icon}
            size={18}
            color="#2196F3"
            style={styles.menuIcon}
          />
          <Text style={[styles.menuLabel, val && styles.menuLabelSelected]}>
            {val || label}
          </Text>
          <Ionicons name="chevron-down" size={18} color="#2196F3" />
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
          titleStyle={o === val ? styles.menuItemSelected : styles.menuItem}
        />
      ))}
    </Menu>
  );

  const renderTask = ({ item }) => (
    <Card style={[styles.taskCard, item.completed && styles.completedCard]}>
      <Card.Content style={styles.taskContent}>
        <View style={styles.taskHeader}>
          <Text
            style={[styles.taskTitle, item.completed && styles.completedText]}
            numberOfLines={2}
          >
            {item.description}
          </Text>
          <TouchableOpacity onPress={() => toggleCompleted(item)}>
            <Ionicons
              name={item.completed ? "checkmark-circle" : "ellipse-outline"}
              size={24}
              color={item.completed ? "#4CAF50" : "#2196F3"}
            />
          </TouchableOpacity>
        </View>
        {/* <Text style={styles.taskSubtitle}>
          By: {item.createdBy || "Unknown User"}
        </Text> */}
        <View style={styles.taskInfo}>
          <View style={styles.infoItem}>
            <Ionicons name="calendar-outline" size={14} color="#546E7A" />
            <Text style={styles.infoText}>
              {moment(item.deadline).format("DD MMM, hh:mm A")}
            </Text>
          </View>
          <View style={styles.infoItem}>
            <Ionicons name="alert-circle-outline" size={14} color="#546E7A" />
            <Text style={styles.infoText}>{item.priority || "N/A"}</Text>
          </View>
          <View style={styles.infoItem}>
            <Ionicons name="folder-outline" size={14} color="#546E7A" />
            <Text style={styles.infoText}>{item.category || "N/A"}</Text>
          </View>
        </View>
      </Card.Content>
    </Card>
  );

  return (
    <PaperProvider theme={theme}>
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
              <Card style={styles.inputCard}>
                <Card.Content>
                  <Text style={styles.sectionTitle}>Add New Task</Text>
                  <View style={styles.inputRow}>
                    <Ionicons
                      name="create-outline"
                      size={20}
                      color="#2196F3"
                      style={styles.inputIcon}
                    />
                    <TextInput
                      label="Task description"
                      value={task}
                      onChangeText={setTask}
                      mode="flat"
                      style={styles.input}
                      textColor="#212121"
                      placeholderTextColor="#757575"
                      underlineColor="transparent"
                    />
                  </View>
                  <View style={styles.inputRow}>
                    <Ionicons
                      name="calendar-outline"
                      size={20}
                      color="#2196F3"
                      style={styles.inputIcon}
                    />
                    <Button
                      mode="text"
                      onPress={() => setPickerVisible(true)}
                      style={styles.dateButton}
                      labelStyle={
                        deadline
                          ? styles.buttonLabel
                          : styles.buttonLabelPlaceholder
                      }
                    >
                      {deadline
                        ? moment(deadline).format("DD MMM YYYY, hh:mm A")
                        : "Select deadline & time"}
                    </Button>
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
                </Card.Content>
              </Card>
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
            labelStyle={{ color: "white", fontWeight: "620" }}
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
              (v) => setSortPref(v.toLowerCase()),
              "swap-vertical"
            )}
          </View>

          <View style={styles.taskListContainer}>
            {loading ? (
              <ActivityIndicator
                style={styles.loading}
                color="#2196F3"
                size="large"
              />
            ) : tasks.length === 0 ? (
              <View style={styles.emptyContainer}>
                <Image
                  source={{
                    uri: "https://via.placeholder.com/180?text=No+Tasks",
                  }}
                  style={styles.emptyImage}
                />
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

          <View style={[styles.fab, adding && styles.fabDisabled]}>
            <TouchableOpacity onPress={handleFabPress} disabled={adding}>
              {adding ? (
                <ActivityIndicator size="small" color="#FFFFFF" />
              ) : (
                <Ionicons
                  name={
                    showAddTask
                      ? isFormComplete
                        ? "checkmark"
                        : "close"
                      : "add"
                  }
                  size={32}
                  color="#FFFFFF"
                />
              )}
            </TouchableOpacity>
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
};

const theme = {
  ...DefaultTheme,
  roundness: 16,
  colors: {
    ...DefaultTheme.colors,
    primary: "#1976D2",
    accent: "#4CAF50",
    background: "#F4F9FF",
    surface: "#FFFFFF",
    text: "#212121",
    placeholder: "#757575",
    disabled: "#B0BEC5",
    error: "#D32F2F",
  },
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
    padding: 24, // Increased from 16 to match SettingsScreen
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 20,
    marginBottom: 20, // Adjusted to match SettingsScreen
  },
  headerTitle: {
    fontSize: 28, // Reduced from 30 to match SettingsScreen
    fontWeight: "bold", // Changed to "bold" to match
    color: theme.colors.primary,
    textAlign: "center",
  },
  inputCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: 16,
    marginBottom: 16,
    shadowColor: "#000000",
    shadowOpacity: 0.1,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 8,
    elevation: 3,
    borderWidth: 1,
    borderColor: "#ECEFF1",
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: theme.colors.primary,
    marginBottom: 12,
  },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#ECEFF1",
    borderRadius: 8, // Reduced from 12 to match SettingsScreen inputs
    marginBottom: 8,
    paddingHorizontal: 12,
    paddingVertical: 10, // Adjusted to match input padding
  },
  inputIcon: {
    marginRight: 8,
  },
  input: {
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 8,
    marginBottom: 14,
    fontSize: 20,
    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 8,
    elevation: 3,
  },
  addBtn: {
    backgroundColor: "#007AFF",
    borderRadius: 14,
    paddingVertical: 8,
    justifyContent: "center",
    marginTop: 12,
  },
  sortRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginVertical: 18,
    alignItems: "center",
    backgroundColor: "#ECEFF1",
    borderRadius: 8, // Reduced from 10
    paddingVertical: 6,
    paddingHorizontal: 10,
    flex: 1,
  },
  menuLabel: {
    fontSize: 14,
    color: theme.colors.text,
    fontWeight: "600",
    marginRight: 4,
    flex: 1,
  },
  menuLabelSelected: {
    color: theme.colors.primary,
  },
  menu: {
    backgroundColor: theme.colors.surface,
    borderRadius: 12,
    shadowColor: "#000000",
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
    marginTop: 8,
  },
  menuItem: {
    fontSize: 14,
    color: theme.colors.text,
    fontWeight: "500",
  },
  menuItemSelected: {
    fontSize: 14,
    color: theme.colors.primary,
    fontWeight: "600",
  },
  menuIcon: {
    marginRight: 4,
  },
  taskListContainer: {
    flex: 1,
  },
  taskListContent: {
    paddingBottom: 80,
  },
  taskCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: 16,
    marginBottom: 12,
    shadowColor: "#000000",
    shadowOpacity: 0.1,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 8,
    elevation: 3,
    borderWidth: 1,
    borderColor: "#ECEFF1",
  },
  completedCard: {
    backgroundColor: "#ECEFF1",
    borderColor: "#CFD8DC",
  },
  taskContent: {
    padding: 16,
  },
  taskHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: 12,
    paddingBottom: 12,
  },
  info: { fontSize: 16, color: "#6C6C6C" },
  empty: {
    textAlign: "center",
    fontWeight: "500",
  },
  fab: {
    position: "absolute",
    bottom: 24,
    right: 24,
    backgroundColor: theme.colors.accent,
    borderRadius: 32,
    width: 64,
    height: 64,
    justifyContent: "center",
    alignItems: "center",
    shadowColor: "#000000",
    shadowOpacity: 0.3,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 8,
    elevation: 8,
  },
  fabDisabled: {
    backgroundColor: theme.colors.disabled,
  },
  popup: {
    backgroundColor: theme.colors.surface,
    borderRadius: 16,
    padding: 20,
    borderWidth: 2,
    borderColor: theme.colors.primary,
  },
  popupContent: {
    alignItems: "center",
  },
  loading: {
    marginTop: 32,
  },
});
export default TaskManagementScreen;

import React, { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  SafeAreaView,
  StatusBar,
  Dimensions,
  Animated,
} from "react-native";
import { useNavigation, useFocusEffect } from "@react-navigation/native";
import { MaterialIcons, FontAwesome5, Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient"; // Install: npx expo install expo-linear-gradient
import {
  getWifiName,
  getTaskOverview,
  getPeboDevices,
  getUserName,
  db,
} from "../services/firebase";
import { auth } from "../services/firebase";

const { width, height } = Dimensions.get("window");

const DashboardScreen = () => {
  const [wifiDetails, setWifiDetails] = useState({
    wifiSSID: "",
    wifiPassword: "",
  });
  const [userPebos, setUserPebos] = useState([]);
  const [upcomingTasks, setUpcomingTasks] = useState([]);
  const [userName, setUserName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [networkCount, setNetworkCount] = useState(0);
  const navigation = useNavigation();

  // Multiple animations for energetic background
  const pulse1 = React.useRef(new Animated.Value(0)).current;
  const pulse2 = React.useRef(new Animated.Value(0)).current;
  const rotate = React.useRef(new Animated.Value(0)).current;
  const float1 = React.useRef(new Animated.Value(0)).current;
  const float2 = React.useRef(new Animated.Value(0)).current;
  const glow = React.useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Energetic pulsing animation
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulse1, {
          toValue: 1,
          duration: 1500,
          useNativeDriver: true,
        }),
        Animated.timing(pulse1, {
          toValue: 0,
          duration: 1500,
          useNativeDriver: true,
        }),
      ])
    ).start();

    // Secondary pulse with offset
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulse2, {
          toValue: 1,
          duration: 2000,
          useNativeDriver: true,
        }),
        Animated.timing(pulse2, {
          toValue: 0,
          duration: 2000,
          useNativeDriver: true,
        }),
      ])
    ).start();

    // Continuous rotation
    Animated.loop(
      Animated.timing(rotate, {
        toValue: 1,
        duration: 20000,
        useNativeDriver: true,
      })
    ).start();

    // Floating animations
    Animated.loop(
      Animated.sequence([
        Animated.timing(float1, {
          toValue: 1,
          duration: 3000,
          useNativeDriver: true,
        }),
        Animated.timing(float1, {
          toValue: 0,
          duration: 3000,
          useNativeDriver: true,
        }),
      ])
    ).start();

    Animated.loop(
      Animated.sequence([
        Animated.timing(float2, {
          toValue: 1,
          duration: 4000,
          useNativeDriver: true,
        }),
        Animated.timing(float2, {
          toValue: 0,
          duration: 4000,
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

  // Authentication listener
  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((user) => {
      setCurrentUser(user);
      if (user) {
        console.log("User authenticated:", user.uid);
      }
    });
    return unsubscribe;
  }, []);

useFocusEffect(
  useCallback(() => {
    const fetchData = async () => {
      try {
        if (!currentUser) {
          console.log("No authenticated user");
          setUserName("Guest");
          return;
        }

        // Enhanced username fetching with profile image priority
        let fetchedUsername = "";
        try {
          // Priority 0 - Extract username from profile image URL
          try {
            const userId = auth.currentUser?.uid;
            if (userId) {
              // Get profile image URL from Firebase
              const profileImageRef = db.ref(`users/${userId}/profileImage`);

              // Use once() for a single read instead of continuous listener
              const snapshot = await profileImageRef.once("value");
              const imageUrl = snapshot.exists() ? snapshot.val() : null;

              console.log(
                "Firebase profileImage for username extraction:",
                imageUrl
              );

              if (imageUrl) {
                // Extract username from URL like: https://pebo-user-images.s3.amazonaws.com/user_yohan.jpg
                const urlMatch = imageUrl.match(/user_([^.]+)\.jpg$/);
                if (urlMatch && urlMatch[1]) {
                  const extractedUsername = urlMatch[1].replace(/_/g, " ");
                  // Capitalize first letter of each word
                  const formattedUsername = extractedUsername
                    .split(" ")
                    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
                    .join(" ");

                  console.log(
                    "Username extracted from profile image:",
                    formattedUsername
                  );
                  setUserName(formattedUsername);
                  fetchedUsername = formattedUsername;

                  if (formattedUsername && formattedUsername !== "Guest") {
                    console.log("Using username from profile image URL");
                  } else {
                    throw new Error("Invalid username from image URL");
                  }
                } else {
                  throw new Error(
                    "Could not extract username from image URL pattern"
                  );
                }
              } else {
                throw new Error("No profile image URL found in Firebase");
              }
            } else {
              throw new Error("No userId available");
            }
          } catch (imageError) {
            console.log(
              "Profile image username extraction failed:",
              imageError.message
            );

            // Priority 1 - getUserName() from Firebase database
            const name = await getUserName();
            console.log("Fetched username from database:", name);
            if (name && name.trim() && name !== "Guest") {
              setUserName(name);
              fetchedUsername = name;
            } else {
              // Priority 2 - currentUser.displayName from Firebase Auth
              const fallbackName =
                currentUser.displayName ||
                currentUser.email?.split("@")[0] ||
                "User";
              setUserName(fallbackName);
              fetchedUsername = fallbackName;
            }
          }
        } catch (error) {
          console.error("Error in username fetching:", error);
          // Priority 3 - Final fallback
          const finalFallback =
            currentUser.displayName ||
            currentUser.email?.split("@")[0] ||
            "User";
          setUserName(finalFallback);
          fetchedUsername = finalFallback;
        }

        // Rest of your existing code...
        const tasks = await getTaskOverview();
        const today = new Date();
        const upcoming = tasks.filter((task) => {
          if (task.completed || !task.deadline) return false;
          const due = new Date(task.deadline);
          const diffDays = (due - today) / (1000 * 60 * 60 * 24);
          return diffDays >= 0 && diffDays <= 5;
        });
        setUpcomingTasks(upcoming);

        const wifi = await getWifiName();
        setWifiDetails(wifi);

        let count = 0;
        if (wifi.wifiSSID && wifi.wifiSSID.trim()) count++;
        setNetworkCount(count);

        const pebos = await getPeboDevices();
        setUserPebos(pebos);

        console.log("Dashboard data loaded for user:", fetchedUsername);
      } catch (error) {
        console.error("Dashboard Error - fetchData:", error);
        setUserName("Guest");
      }
    };

    fetchData();
  }, [currentUser])
);


  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour >= 5 && hour < 12) return "Good Morning";
    if (hour >= 12 && hour < 17) return "Good Afternoon";
    if (hour >= 17 && hour < 22) return "Good Evening";
    return "Good Night"; // For late night/early morning (22:00 - 04:59)
  };

  const maskPassword = (password) => {
    if (!password) return "Not set";
    return showPassword ? password : "••••••••";
  };

  const rotateInterpolate = rotate.interpolate({
    inputRange: [0, 1],
    outputRange: ["0deg", "360deg"],
  });

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#000000" />

      {/* Futuristic Animated Background */}
      <View style={styles.backgroundContainer}>
        {/* Main rotating ring */}
        <Animated.View
          style={[
            styles.rotatingRing,
            {
              transform: [{ rotate: rotateInterpolate }],
            },
          ]}
        />

        {/* Pulsing orbs */}
        <Animated.View
          style={[
            styles.pulseOrb1,
            {
              opacity: pulse1,
              transform: [
                {
                  scale: pulse1.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0.5, 1.2],
                  }),
                },
              ],
            },
          ]}
        />

        <Animated.View
          style={[
            styles.pulseOrb2,
            {
              opacity: pulse2,
              transform: [
                {
                  scale: pulse2.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0.3, 1],
                  }),
                },
              ],
            },
          ]}
        />

        {/* Floating particles */}
        <Animated.View
          style={[
            styles.floatingParticle1,
            {
              transform: [
                {
                  translateY: float1.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0, -30],
                  }),
                },
                {
                  translateX: float1.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0, 20],
                  }),
                },
              ],
            },
          ]}
        />

        <Animated.View
          style={[
            styles.floatingParticle2,
            {
              transform: [
                {
                  translateY: float2.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0, 25],
                  }),
                },
                {
                  translateX: float2.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0, -15],
                  }),
                },
              ],
            },
          ]}
        />

        {/* Glowing grid lines */}
        <Animated.View
          style={[
            styles.gridLines,
            {
              opacity: glow.interpolate({
                inputRange: [0, 1],
                outputRange: [0.1, 0.4],
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
        <Text style={styles.appName}>PEBO</Text>
        <Text style={styles.appSubtitle}>Desk Companion Dashboard</Text>
      </LinearGradient>

      <FlatList
        data={[1]}
        renderItem={() => (
          <View style={styles.content}>
            {/* Welcome Message with Glow Effect */}
            <Animated.View
              style={[
                styles.welcomeContainer,
                {
                  shadowOpacity: glow.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0.3, 0.8],
                  }),
                },
              ]}
            >
              <Text style={styles.greeting}>{getGreeting()},</Text>
              <Text style={styles.userName}>{userName}!</Text>
              <Text style={styles.welcomeSubtext}>Welcome to the World of PEBO</Text>
            </Animated.View>

            {/* Futuristic Stats Grid */}
            <View style={styles.statsGrid}>
              <LinearGradient
                colors={["rgba(29, 233, 182, 0.2)", "rgba(29, 233, 182, 0.05)"]}
                style={styles.statCard}
              >
                <View style={styles.statIcon}>
                  <Ionicons name="hardware-chip" size={24} color="#1DE9B6" />
                </View>
                <Text style={styles.statNumber}>{userPebos.length}</Text>
                <Text style={styles.statLabel}>DEVICES</Text>
                <View style={styles.statGlow} />
              </LinearGradient>

              <LinearGradient
                colors={["rgba(255, 82, 82, 0.2)", "rgba(255, 82, 82, 0.05)"]}
                style={styles.statCard}
              >
                <View style={styles.statIcon}>
                  <FontAwesome5 name="tasks" size={20} color="#FF5252" />
                </View>
                <Text style={[styles.statNumber, { color: "#FF5252" }]}>
                  {upcomingTasks.length}
                </Text>
                <Text style={styles.statLabel}>TASKS</Text>
                <View
                  style={[styles.statGlow, { backgroundColor: "#FF5252" }]}
                />
              </LinearGradient>

              <LinearGradient
                colors={["rgba(76, 175, 80, 0.2)", "rgba(76, 175, 80, 0.05)"]}
                style={styles.statCard}
              >
                <View style={styles.statIcon}>
                  <MaterialIcons name="wifi" size={24} color="#4CAF50" />
                </View>
                <Text style={[styles.statNumber, { color: "#4CAF50" }]}>
                  {networkCount}
                </Text>
                <Text style={styles.statLabel}>NETWORKS</Text>
                <View
                  style={[styles.statGlow, { backgroundColor: "#4CAF50" }]}
                />
              </LinearGradient>
            </View>

            {/* Active Devices */}
            {userPebos.length > 0 && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>
                  <Ionicons name="radio" size={16} color="#1DE9B6" /> ACTIVE
                  NODES
                </Text>
                {userPebos.map((pebo, index) => (
                  <LinearGradient
                    key={index}
                    colors={["rgba(26, 26, 26, 0.8)", "rgba(26, 26, 26, 0.4)"]}
                    style={styles.deviceCard}
                  >
                    <View style={styles.deviceInfo}>
                      <Text style={styles.deviceName}>{pebo.name}</Text>
                      <Text style={styles.deviceLocation}>{pebo.location}</Text>
                    </View>
                    <View style={styles.deviceStatus}>
                      <Animated.View
                        style={[
                          styles.statusPulse,
                          {
                            backgroundColor: pebo.online
                              ? "#4CAF50"
                              : "#FF5252",
                            opacity: pulse1,
                          },
                        ]}
                      />
                      <View
                        style={[
                          styles.statusDot,
                          {
                            backgroundColor: pebo.online
                              ? "#4CAF50"
                              : "#FF5252",
                          },
                        ]}
                      />
                    </View>
                  </LinearGradient>
                ))}
              </View>
            )}

            {/* Network Matrix */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>
                <Ionicons name="globe" size={16} color="#1DE9B6" /> NETWORK
                MATRIX
              </Text>
              <LinearGradient
                colors={["rgba(26, 26, 26, 0.8)", "rgba(26, 26, 26, 0.4)"]}
                style={styles.networkCard}
              >
                <View style={styles.networkRow}>
                  <Text style={styles.networkLabel}>WiFi Signal</Text>
                  <Text style={styles.networkValue}>
                    {wifiDetails.wifiSSID || "Disconnected"}
                  </Text>
                </View>
                <View style={styles.networkRow}>
                  <Text style={styles.networkLabel}>Access Key</Text>
                  <View style={styles.passwordContainer}>
                    <Text style={styles.networkValue}>
                      {maskPassword(wifiDetails.wifiPassword)}
                    </Text>
                    <TouchableOpacity
                      onPress={() => setShowPassword(!showPassword)}
                      style={styles.eyeButton}
                    >
                      <Ionicons
                        name={showPassword ? "eye-off" : "eye"}
                        size={16}
                        color="#1DE9B6"
                      />
                    </TouchableOpacity>
                  </View>
                </View>
              </LinearGradient>
            </View>

            {/* Mission Queue */}
            {upcomingTasks.length > 0 && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>
                  <Ionicons name="flash" size={16} color="#1DE9B6" /> MISSION
                  QUEUE
                </Text>
                {upcomingTasks.slice(0, 3).map((task, index) => (
                  <LinearGradient
                    key={task.id}
                    colors={["rgba(26, 26, 26, 0.8)", "rgba(26, 26, 26, 0.4)"]}
                    style={styles.taskCard}
                  >
                    <View style={styles.taskHeader}>
                      <Text style={styles.taskTitle}>{task.description}</Text>
                      <View style={styles.taskPriority}>
                        <View style={styles.priorityDot} />
                      </View>
                    </View>
                    <Text style={styles.taskDate}>
                      {new Date(task.deadline).toLocaleDateString()}
                    </Text>
                  </LinearGradient>
                ))}
              </View>
            )}

            {/* Control Panel */}
            <TouchableOpacity
              style={styles.controlPanel}
              onPress={() => navigation.navigate("Settings")}
            >
              <LinearGradient
                colors={["#1DE9B6", "#00BFA5"]}
                style={styles.controlGradient}
              >
                <Ionicons name="settings" size={20} color="#000000" />
                <Text style={styles.controlText}>CONTROL PANEL</Text>
                <Ionicons name="chevron-forward" size={20} color="#000000" />
              </LinearGradient>
            </TouchableOpacity>
          </View>
        )}
        showsVerticalScrollIndicator={false}
      />
    </SafeAreaView>
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
  rotatingRing: {
    position: "absolute",
    top: 100,
    right: 50,
    width: 120,
    height: 120,
    borderRadius: 60,
    borderWidth: 2,
    borderColor: "rgba(29, 233, 182, 0.3)",
    borderStyle: "dashed",
  },
  pulseOrb1: {
    position: "absolute",
    top: 150,
    left: 30,
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: "rgba(29, 233, 182, 0.2)",
  },
  pulseOrb2: {
    position: "absolute",
    top: 300,
    right: 80,
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "rgba(255, 82, 82, 0.2)",
  },
  floatingParticle1: {
    position: "absolute",
    top: 200,
    left: 100,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#1DE9B6",
  },
  floatingParticle2: {
    position: "absolute",
    top: 250,
    right: 120,
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: "#FF5252",
  },
  gridLines: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.1)",
    borderStyle: "dotted",
  },
  header: {
    paddingHorizontal: 24,
    paddingTop: 60,
    paddingBottom: 20,
    zIndex: 1,
  },
  appName: {
    fontSize: 42,
    fontWeight: "900",
    color: "#FFFFFF",
    textAlign: "center",
    letterSpacing: 4,
    textShadowColor: "#1DE9B6",
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 10,
  },
  appSubtitle: {
    fontSize: 14,
    color: "#1DE9B6",
    textAlign: "center",
    marginTop: 4,
    letterSpacing: 2,
    textTransform: "uppercase",
  },
  content: {
    padding: 24,
    zIndex: 1,
  },
  welcomeContainer: {
    marginBottom: 32,
    padding: 20,
    borderRadius: 16,
    backgroundColor: "rgba(26, 26, 26, 0.3)",
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
    shadowColor: "#1DE9B6",
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 20,
  },
  greeting: {
    fontSize: 16,
    color: "#888",
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  userName: {
    fontSize: 32,
    color: "#FFFFFF",
    fontWeight: "bold",
    marginTop: 4,
    textShadowColor: "#1DE9B6",
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 5,
  },
  welcomeSubtext: {
    fontSize: 12,
    color: "#1DE9B6",
    marginTop: 8,
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  statsGrid: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 32,
  },
  statCard: {
    borderRadius: 16,
    padding: 20,
    alignItems: "center",
    flex: 1,
    marginHorizontal: 4,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.3)",
    position: "relative",
    overflow: "hidden",
  },
  statIcon: {
    marginBottom: 12,
  },
  statNumber: {
    fontSize: 28,
    fontWeight: "900",
    color: "#1DE9B6",
    textShadowColor: "#1DE9B6",
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 10,
  },
  statLabel: {
    fontSize: 10,
    color: "#888",
    marginTop: 8,
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  statGlow: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    height: 2,
    backgroundColor: "#1DE9B6",
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: "700",
    color: "#FFFFFF",
    marginBottom: 16,
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  deviceCard: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 8,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  deviceInfo: {
    flex: 1,
  },
  deviceName: {
    fontSize: 16,
    fontWeight: "600",
    color: "#FFFFFF",
  },
  deviceLocation: {
    fontSize: 12,
    color: "#888",
    marginTop: 2,
    textTransform: "uppercase",
  },
  deviceStatus: {
    position: "relative",
  },
  statusPulse: {
    position: "absolute",
    width: 20,
    height: 20,
    borderRadius: 10,
    top: -4,
    left: -4,
  },
  statusDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  networkCard: {
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  networkRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  networkLabel: {
    fontSize: 12,
    color: "#888",
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  networkValue: {
    fontSize: 14,
    color: "#FFFFFF",
    fontWeight: "600",
  },
  passwordContainer: {
    flexDirection: "row",
    alignItems: "center",
  },
  eyeButton: {
    marginLeft: 8,
    padding: 4,
  },
  taskCard: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  taskHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  taskTitle: {
    fontSize: 14,
    color: "#FFFFFF",
    fontWeight: "500",
    flex: 1,
  },
  taskPriority: {
    flexDirection: "row",
    alignItems: "center",
  },
  priorityDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#1DE9B6",
  },
  taskDate: {
    fontSize: 11,
    color: "#888",
    textTransform: "uppercase",
  },
  controlPanel: {
    marginTop: 16,
    borderRadius: 16,
    overflow: "hidden",
  },
  controlGradient: {
    padding: 20,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
  },
  controlText: {
    color: "#000000",
    fontSize: 16,
    fontWeight: "900",
    marginLeft: 12,
    marginRight: 12,
    flex: 1,
    textAlign: "center",
    letterSpacing: 2,
  },
});

export default DashboardScreen;

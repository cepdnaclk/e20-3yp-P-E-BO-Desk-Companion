import React, { useState, useEffect, useCallback, useRef } from "react";
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
import { LinearGradient } from "expo-linear-gradient";
import { Video } from "expo-av";
import { auth, db } from "../services/firebase";
import LoadingScreen from "../components/LoadingScreen";

const { width, height } = Dimensions.get("window");

const DashboardScreen = () => {
  // ... all your useState hooks as before
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
  const [robotGreeting, setRobotGreeting] = useState(false);
  const [showSetupWarning, setShowSetupWarning] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [dataRefreshKey, setDataRefreshKey] = useState(0);
  const [userProfileImage, setUserProfileImage] = useState("");
  const [loadingStep, setLoadingStep] = useState("initializing");
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [isInitialLoad, setIsInitialLoad] = useState(true);

  const [setupStatus, setSetupStatus] = useState({
    hasWifi: false,
    hasPebos: false,
    hasProfileImage: false,
    hasUserName: false,
  });

  const navigation = useNavigation();

  // Refs for animations
  const pulse1 = useRef(new Animated.Value(0)).current;
  const pulse2 = useRef(new Animated.Value(0)).current;
  const rotate = useRef(new Animated.Value(0)).current;
  const float1 = useRef(new Animated.Value(0)).current;
  const float2 = useRef(new Animated.Value(0)).current;
  const glow = useRef(new Animated.Value(0)).current;
  const videoRef = useRef(null);

  // Refs for listeners
  const wifiListenerRef = useRef(null);
  const tasksListenerRef = useRef(null);
  const pebosListenerRef = useRef(null);
  const userListenerRef = useRef(null);

  // === ANIMATION EFFECTS (unchanged) ===
  useEffect(() => {
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
    Animated.loop(
      Animated.timing(rotate, {
        toValue: 1,
        duration: 20000,
        useNativeDriver: true,
      })
    ).start();
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
  // === AUTH LISTENER (unchanged) ===
  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((user) => {
      setCurrentUser(user);
      if (user) {
        setIsLoading(true);
        setDataRefreshKey((prev) => prev + 1);
      } else {
        cleanupListeners();
      }
    });
    return unsubscribe;
  }, []);

  // === CLEANUP LISTENERS (unchanged) ===
  const cleanupListeners = useCallback(() => {
    try {
      if (wifiListenerRef.current && currentUser) {
        db.ref(`users/${currentUser.uid}/settings`).off(
          "value",
          wifiListenerRef.current
        );
        wifiListenerRef.current = null;
      }
      if (tasksListenerRef.current && currentUser) {
        db.ref(`users/${currentUser.uid}/tasks`).off(
          "value",
          tasksListenerRef.current
        );
        tasksListenerRef.current = null;
      }
      if (pebosListenerRef.current && currentUser) {
        db.ref(`users/${currentUser.uid}/peboDevices`).off(
          "value",
          pebosListenerRef.current
        );
        pebosListenerRef.current = null;
      }
      if (userListenerRef.current && currentUser) {
        db.ref(`users/${currentUser.uid}`).off(
          "value",
          userListenerRef.current
        );
        userListenerRef.current = null;
      }
    } catch (error) {}
  }, [currentUser]);

  // Helper function to get time from now
  const getTimeFromNow = (deadline) => {
    const now = new Date();
    const due = new Date(deadline);
    const diffMs = due - now;

    if (diffMs < 0) return "Overdue";

    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor(
      (diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)
    );
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

    if (diffDays > 0) {
      return `${diffDays}d ${diffHours}h`;
    } else if (diffHours > 0) {
      return `${diffHours}h ${diffMinutes}m`;
    } else {
      return `${diffMinutes}m`;
    }
  };

  // Enhanced setup checking with all requirements
  const checkUserSetup = useCallback((wifi, pebos, profileImage, userName) => {
    const hasWifi = wifi && wifi.wifiSSID && wifi.wifiSSID.trim();
    const hasPebos = pebos && pebos.length > 0;
    const hasProfileImage = profileImage && profileImage.trim();
    const hasUserName =
      userName &&
      userName.trim() &&
      userName !== "Guest" &&
      userName !== "User";

    const newSetupStatus = { hasWifi, hasPebos, hasProfileImage, hasUserName };
    setSetupStatus(newSetupStatus);

    // Show warning if any requirement is missing
    const isFullySetup = hasWifi && hasPebos && hasProfileImage && hasUserName;
    setShowSetupWarning(!isFullySetup);
  }, []);
  // Get missing setup items
  const getMissingSetupItems = () => {
    const missing = [];
    if (!setupStatus.hasWifi) missing.push("WiFi Configuration");
    if (!setupStatus.hasPebos) missing.push("PEBO Device");
    if (!setupStatus.hasProfileImage) missing.push("Profile Image");
    if (!setupStatus.hasUserName) missing.push("User Name");
    return missing;
  };

  // Setup Firebase listeners
  // Setup Firebase listeners with progress tracking
  const setupFirebaseListeners = useCallback(async () => {
    if (!currentUser) {
      console.log("No authenticated user for listeners");
      setIsLoading(false);
      setIsInitialLoad(false);
      return;
    }

    const userId = currentUser.uid;
    console.log("Setting up Firebase listeners for user:", userId);

    try {
      // Only show loading screen on initial load
      if (isInitialLoad) {
        setLoadingStep("initializing");
        setLoadingProgress(5);
        cleanupListeners();

        // Step 1: Connecting to Firebase
        setLoadingStep("connecting");
        setLoadingProgress(15);
        await new Promise((resolve) => setTimeout(resolve, 200));
      } else {
        // Just cleanup listeners without loading screen
        cleanupListeners();
      }

      // Step 2: Setup WiFi listener
      if (isInitialLoad) {
        setLoadingStep("wifi");
        setLoadingProgress(30);
      }

      const wifiRef = db.ref(`users/${userId}/settings`);
      wifiListenerRef.current = wifiRef.on("value", (snapshot) => {
        try {
          const data = snapshot && snapshot.exists() ? snapshot.val() : null;
          console.log("WiFi data updated:", data);
          const wifiData = {
            wifiSSID: data?.wifiSSID || "",
            wifiPassword: data?.wifiPassword || "",
          };
          setWifiDetails(wifiData);
          let count = 0;
          if (wifiData.wifiSSID && wifiData.wifiSSID.trim()) count++;
          setNetworkCount(count);
        } catch (error) {
          console.error("WiFi listener error:", error);
          setWifiDetails({ wifiSSID: "", wifiPassword: "" });
          setNetworkCount(0);
        }
      });

      if (isInitialLoad) {
        await new Promise((resolve) => setTimeout(resolve, 300));
      }

      // Step 3: Setup Tasks listener
      if (isInitialLoad) {
        setLoadingStep("tasks");
        setLoadingProgress(50);
      }

      const tasksRef = db.ref(`users/${userId}/tasks`);
      tasksListenerRef.current = tasksRef.on("value", (snapshot) => {
        try {
          const data = snapshot && snapshot.exists() ? snapshot.val() : null;
          console.log("Tasks data updated:", data);
          const tasks = data
            ? Object.keys(data).map((key) => ({
                id: key,
                ...data[key],
              }))
            : [];
          const today = new Date();
          const upcoming = tasks.filter((task) => {
            if (task.completed || !task.deadline) return false;
            try {
              const due = new Date(task.deadline);
              if (isNaN(due.getTime())) return false;
              const diffDays = (due - today) / (1000 * 60 * 60 * 24);
              return diffDays >= 0 && diffDays <= 5;
            } catch (error) {
              console.error("Error processing task deadline:", error);
              return false;
            }
          });
          setUpcomingTasks(upcoming);
        } catch (error) {
          console.error("Tasks listener error:", error);
          setUpcomingTasks([]);
        }
      });

      if (isInitialLoad) {
        await new Promise((resolve) => setTimeout(resolve, 300));
      }

      // Step 4: Setup PEBOs listener
      if (isInitialLoad) {
        setLoadingStep("devices");
        setLoadingProgress(70);
      }

      const pebosRef = db.ref(`users/${userId}/peboDevices`);
      pebosListenerRef.current = pebosRef.on("value", (snapshot) => {
        try {
          const data = snapshot && snapshot.exists() ? snapshot.val() : null;
          console.log("PEBOs data updated:", data);
          const pebos = data
            ? Object.keys(data).map((key) => ({
                id: key,
                name: data[key].name || `Device ${key}`,
                location: data[key].location || "Unknown Location",
                online: data[key].online || false,
                createdAt: data[key].createdAt || null,
                ...data[key],
              }))
            : [];
          setUserPebos(pebos);
          console.log("PEBO devices set:", pebos);
        } catch (error) {
          console.error("PEBOs listener error:", error);
          setUserPebos([]);
        }
      });

      if (isInitialLoad) {
        await new Promise((resolve) => setTimeout(resolve, 300));
      }

      // Step 5: Setup User profile listener
      if (isInitialLoad) {
        setLoadingStep("profile");
        setLoadingProgress(90);
      }

      const userRef = db.ref(`users/${userId}`);
      userListenerRef.current = userRef.on("value", async (snapshot) => {
        try {
          const userData =
            snapshot && snapshot.exists() ? snapshot.val() : null;
          console.log("User data updated:", userData);
          let fetchedUsername = "";
          let profileImage = "";

          // Get profile image
          if (userData?.profileImage) {
            profileImage = userData.profileImage;
            setUserProfileImage(profileImage);
            try {
              const imageUrl = userData.profileImage;
              const urlMatch = imageUrl.match(/user_([^.]+)\.jpg$/);
              if (urlMatch && urlMatch[1]) {
                const extractedUsername = urlMatch[1].replace(/_/g, " ");
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
              }
            } catch (imageError) {
              console.log("Error extracting username from image:", imageError);
            }
          } else {
            setUserProfileImage("");
          }

          // Get username from stored data
          if (!fetchedUsername && userData?.username) {
            setUserName(userData.username);
            fetchedUsername = userData.username;
          }

          // Fallback to auth data
          if (!fetchedUsername) {
            const fallbackName =
              currentUser.displayName ||
              currentUser.email?.split("@")[0] ||
              "User";
            setUserName(fallbackName);
            fetchedUsername = fallbackName;
          }

          console.log("Final username set:", fetchedUsername);
          console.log("Profile image set:", profileImage);
        } catch (error) {
          console.error("User listener error:", error);
          const finalFallback =
            currentUser.displayName ||
            currentUser.email?.split("@")[0] ||
            "User";
          setUserName(finalFallback);
          setUserProfileImage("");
        }
      });

      // Final step: Complete loading (only on initial load)
      if (isInitialLoad) {
        setLoadingStep("complete");
        setLoadingProgress(100);
        await new Promise((resolve) => setTimeout(resolve, 200));
      }

      // Mark initial load as complete
      setIsInitialLoad(false);
      console.log("All Firebase listeners setup successfully");
    } catch (error) {
      console.error("Error setting up Firebase listeners:", error);
      setLoadingStep("error");
      setLoadingProgress(100);
      setIsInitialLoad(false);
    }
  }, [currentUser, cleanupListeners, isInitialLoad]);

  // Navigation cleanup
  useEffect(() => {
    const unsubscribe = navigation.addListener("beforeRemove", (e) => {
      try {
        cleanupListeners();
      } catch (error) {
        console.error("Error during navigation cleanup:", error);
      }
    });

    return unsubscribe;
  }, [navigation, cleanupListeners]);

  // Setup listeners when user changes or component focuses
  // CHANGE your existing useFocusEffect
  useFocusEffect(
    useCallback(() => {
      console.log(
        "Dashboard useFocusEffect triggered, currentUser:",
        !!currentUser
      );

      if (currentUser) {
        // Force loading to show every time
        setIsLoading(true);
        setLoadingStep("initializing");
        setLoadingProgress(0);

        // Add small delay to ensure loading screen renders
        setTimeout(() => {
          setupFirebaseListeners()
            .then(() => {
              console.log("Firebase listeners setup completed");
            })
            .catch((error) => {
              console.error("Error setting up Firebase listeners:", error);
            })
            .finally(() => {
              setIsLoading(false);
            });
        }, 100); // Small delay ensures loading screen appears
      } else {
        setIsLoading(false);
        // ... rest of your existing else logic
      }

      return () => {
        try {
          cleanupListeners();
        } catch (error) {
          console.error("Error during unmount cleanup:", error);
        }
      };
    }, [currentUser, setupFirebaseListeners, cleanupListeners])
  );

  // Check setup status whenever data changes
  useEffect(() => {
    if (currentUser && !isLoading) {
      const timeoutId = setTimeout(() => {
        checkUserSetup(wifiDetails, userPebos, userProfileImage, userName);
      }, 300);

      return () => clearTimeout(timeoutId);
    }
  }, [
    wifiDetails,
    userPebos,
    userProfileImage,
    userName,
    currentUser,
    isLoading,
    checkUserSetup,
  ]);

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour >= 5 && hour < 12) return "Good Morning";
    if (hour >= 12 && hour < 17) return "Good Afternoon";
    if (hour >= 17 && hour < 22) return "Good Evening";
    return "Good Night";
  };

  const maskPassword = (password) => {
    if (!password) return "Not configured";
    return showPassword ? password : "••••••••";
  };

  const getWifiStatus = () => {
    if (wifiDetails.wifiSSID && wifiDetails.wifiSSID.trim()) {
      return "Configured";
    }
    return "Not configured";
  };

  const triggerRobotGreeting = () => {
    setRobotGreeting(true);
    setTimeout(() => setRobotGreeting(false), 3000);
  };

  const rotateInterpolate = rotate.interpolate({
    inputRange: [0, 1],
    outputRange: ["0deg", "360deg"],
  });
  // Helper function to get loading message based on step
  const getLoadingMessage = () => {
    switch (loadingStep) {
      case "initializing":
        return "Initializing PEBO Dashboard...";
      case "connecting":
        return "Connecting to Firebase...";
      case "wifi":
        return "Loading Network Settings...";
      case "tasks":
        return "Syncing Tasks...";
      case "devices":
        return "Discovering PEBO Devices...";
      case "profile":
        return "Loading Profile...";
      case "complete":
        return "Loading Complete!";
      case "error":
        return "Connection Error - Retrying...";
      default:
        return "Loading PEBO Dashboard...";
    }
  };

  // === UI/RENDER ===
  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#000000" />
      {/* Loading screen on initial load */}
      {isLoading && isInitialLoad && (
        <LoadingScreen
          message={getLoadingMessage()}
          loadingStep={loadingStep}
          progress={loadingProgress}
        />
      )}

      {/* Main dashboard content */}
      {(!isLoading || !isInitialLoad) && (
        <>
          {/* Animated/futuristic PEBO robot and background */}
          <View style={styles.backgroundContainer}>
            {/* PEBO Robot Video Animation - Bigger when setup warning is shown */}
            <Animated.View
              style={[
                showSetupWarning
                  ? styles.peboRobotContainerSetupBig
                  : styles.peboRobotContainer,
                {
                  transform: [
                    {
                      scale: robotGreeting
                        ? pulse1.interpolate({
                            inputRange: [0, 1],
                            outputRange: [1.0, 1.3],
                          })
                        : pulse1.interpolate({
                            inputRange: [0, 1],
                            outputRange: [0.8, 1.1],
                          }),
                    },
                  ],
                  opacity: glow.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0.7, 1],
                  }),
                },
              ]}
            >
              <TouchableOpacity
                onPress={triggerRobotGreeting}
                style={styles.robotTouchArea}
              >
                <Video
                  ref={videoRef}
                  source={require("../../assets/peb-video.mp4")}
                  style={styles.peboVideo}
                  shouldPlay={true}
                  isLooping={true}
                  isMuted={true}
                  resizeMode="contain"
                  useNativeControls={false}
                  progressUpdateIntervalMillis={100}
                  positionMillis={0}
                />

                {/* Greeting bubble */}
                {robotGreeting && (
                  <Animated.View
                    style={[
                      styles.greetingBubble,
                      {
                        opacity: pulse2,
                        transform: [
                          {
                            translateY: pulse2.interpolate({
                              inputRange: [0, 1],
                              outputRange: [10, -10],
                            }),
                          },
                        ],
                      },
                    ]}
                  >
                    <Text style={styles.greetingText}>Hi {userName}!</Text>
                  </Animated.View>
                )}
              </TouchableOpacity>
            </Animated.View>

            {/* Background elements - Only show when not in setup mode */}
            {!showSetupWarning && (
              <>
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
              </>
            )}
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
                {/* Setup Warning: THIS BLOCK WILL NOW SHOW IF showSetupWarning == true */}
                {showSetupWarning && currentUser && (
                  <Animated.View
                    style={[styles.warningContainer, { opacity: pulse1 }]}
                  >
                    <View style={styles.warningHeader}>
                      <Ionicons name="warning" size={20} color="#FF5252" />
                      <Text style={styles.warningTitle}>Setup Required</Text>
                    </View>
                    <Text style={styles.warningText}>
                      Complete your PEBO setup to unlock the full dashboard
                      experience.
                    </Text>
                    <View style={styles.setupProgress}>
                      <Text style={styles.setupProgressTitle}>
                        Setup Progress:
                      </Text>
                      <View style={styles.setupItems}>
                        <View style={styles.setupItem}>
                          <Ionicons
                            name={
                              setupStatus.hasWifi
                                ? "checkmark-circle"
                                : "ellipse-outline"
                            }
                            size={16}
                            color={setupStatus.hasWifi ? "#4CAF50" : "#FF5252"}
                          />
                          <Text
                            style={[
                              styles.setupItemText,
                              {
                                color: setupStatus.hasWifi
                                  ? "#4CAF50"
                                  : "#FF5252",
                              },
                            ]}
                          >
                            WiFi Configuration
                          </Text>
                        </View>
                        <View style={styles.setupItem}>
                          <Ionicons
                            name={
                              setupStatus.hasPebos
                                ? "checkmark-circle"
                                : "ellipse-outline"
                            }
                            size={16}
                            color={setupStatus.hasPebos ? "#4CAF50" : "#FF5252"}
                          />
                          <Text
                            style={[
                              styles.setupItemText,
                              {
                                color: setupStatus.hasPebos
                                  ? "#4CAF50"
                                  : "#FF5252",
                              },
                            ]}
                          >
                            Add PEBO Device
                          </Text>
                        </View>
                        <View style={styles.setupItem}>
                          <Ionicons
                            name={
                              setupStatus.hasProfileImage
                                ? "checkmark-circle"
                                : "ellipse-outline"
                            }
                            size={16}
                            color={
                              setupStatus.hasProfileImage
                                ? "#4CAF50"
                                : "#FF5252"
                            }
                          />
                          <Text
                            style={[
                              styles.setupItemText,
                              {
                                color: setupStatus.hasProfileImage
                                  ? "#4CAF50"
                                  : "#FF5252",
                              },
                            ]}
                          >
                            Profile Image
                          </Text>
                        </View>
                        <View style={styles.setupItem}>
                          <Ionicons
                            name={
                              setupStatus.hasUserName
                                ? "checkmark-circle"
                                : "ellipse-outline"
                            }
                            size={16}
                            color={
                              setupStatus.hasUserName ? "#4CAF50" : "#FF5252"
                            }
                          />
                          <Text
                            style={[
                              styles.setupItemText,
                              {
                                color: setupStatus.hasUserName
                                  ? "#4CAF50"
                                  : "#FF5252",
                              },
                            ]}
                          >
                            User Name
                          </Text>
                        </View>
                      </View>
                    </View>
                    <TouchableOpacity
                      style={styles.warningButton}
                      onPress={() => navigation.navigate("Settings")}
                    >
                      <LinearGradient
                        colors={["#FF5252", "#FF1744"]}
                        style={styles.warningButtonGradient}
                      >
                        <Ionicons name="settings" size={16} color="#FFFFFF" />
                        <Text style={styles.warningButtonText}>
                          Complete Setup
                        </Text>
                      </LinearGradient>
                    </TouchableOpacity>
                  </Animated.View>
                )}

                {/* Welcome Message - Hidden during setup warning */}
                {!showSetupWarning && (
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
                    <Text style={styles.welcomeSubtext}>
                      Welcome to the World of PEBO
                    </Text>
                  </Animated.View>
                )}

                {/* Conditional Stats Grid - Moved up when setup warning is shown */}
                <View
                  style={
                    showSetupWarning ? styles.statsGridSetup : styles.statsGrid
                  }
                >
                  <LinearGradient
                    colors={[
                      "rgba(29, 233, 182, 0.2)",
                      "rgba(29, 233, 182, 0.05)",
                    ]}
                    style={
                      showSetupWarning ? styles.statCardSmall : styles.statCard
                    }
                  >
                    <View style={styles.statIcon}>
                      <Ionicons
                        name="hardware-chip"
                        size={showSetupWarning ? 16 : 24}
                        color="#1DE9B6"
                      />
                    </View>
                    <Text
                      style={[
                        styles.statNumber,
                        showSetupWarning && styles.statNumberSmall,
                      ]}
                    >
                      {userPebos.length}
                    </Text>
                    <Text style={styles.statLabel}>DEVICES</Text>
                    <View style={styles.statGlow} />
                  </LinearGradient>

                  <LinearGradient
                    colors={[
                      "rgba(255, 82, 82, 0.2)",
                      "rgba(255, 82, 82, 0.05)",
                    ]}
                    style={
                      showSetupWarning ? styles.statCardSmall : styles.statCard
                    }
                  >
                    <View style={styles.statIcon}>
                      <FontAwesome5
                        name="tasks"
                        size={showSetupWarning ? 14 : 20}
                        color="#FF5252"
                      />
                    </View>
                    <Text
                      style={[
                        styles.statNumber,
                        { color: "#FF5252" },
                        showSetupWarning && styles.statNumberSmall,
                      ]}
                    >
                      {upcomingTasks.length}
                    </Text>
                    <Text style={styles.statLabel}>TASKS</Text>
                    <View
                      style={[styles.statGlow, { backgroundColor: "#FF5252" }]}
                    />
                  </LinearGradient>

                  <LinearGradient
                    colors={[
                      "rgba(76, 175, 80, 0.2)",
                      "rgba(76, 175, 80, 0.05)",
                    ]}
                    style={
                      showSetupWarning ? styles.statCardSmall : styles.statCard
                    }
                  >
                    <View style={styles.statIcon}>
                      <MaterialIcons
                        name="wifi"
                        size={showSetupWarning ? 16 : 24}
                        color="#4CAF50"
                      />
                    </View>
                    <Text
                      style={[
                        styles.stat1Number,
                        { color: "#4CAF50" },
                        showSetupWarning && styles.stat1NumberSmall,
                      ]}
                    >
                      {getWifiStatus()}
                    </Text>
                    <Text style={styles.statLabel}>NETWORKS</Text>
                    <View
                      style={[styles.statGlow, { backgroundColor: "#4CAF50" }]}
                    />
                  </LinearGradient>
                </View>

                {/* Conditional Content - Only show when setup is complete */}
                {!showSetupWarning && (
                  <>
                    {/* Active Devices */}
                    {userPebos.length > 0 && (
                      <View style={styles.section}>
                        <Text style={styles.sectionTitle}>
                          <Ionicons name="radio" size={16} color="#1DE9B6" /> My
                          Devices
                        </Text>
                        {userPebos.map((pebo, index) => (
                          <LinearGradient
                            key={pebo.id || index}
                            colors={[
                              "rgba(26, 26, 26, 0.8)",
                              "rgba(26, 26, 26, 0.4)",
                            ]}
                            style={styles.deviceCard}
                          >
                            <View style={styles.deviceInfo}>
                              <Text style={styles.deviceName}>
                                {pebo.name || `Device ${index + 1}`}
                              </Text>
                              <Text style={styles.deviceLocation}>
                                {pebo.location || "Unknown Location"}
                              </Text>
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
                        <Ionicons name="globe" size={16} color="#1DE9B6" />{" "}
                        NETWORK STATUS
                      </Text>
                      <LinearGradient
                        colors={[
                          "rgba(26, 26, 26, 0.8)",
                          "rgba(26, 26, 26, 0.4)",
                        ]}
                        style={styles.networkCard}
                      >
                        <View style={styles.networkRow}>
                          <Text style={styles.networkLabel}>WiFi Signal</Text>
                          <Text style={styles.networkValue}>
                            {wifiDetails.wifiSSID || "Not configured"}
                          </Text>
                        </View>
                        <View style={styles.networkRow}>
                          <Text style={styles.networkLabel}>Access Key</Text>
                          <View style={styles.passwordContainer}>
                            <Text style={styles.networkValue}>
                              {maskPassword(wifiDetails.wifiPassword)}
                            </Text>
                            {wifiDetails.wifiPassword && (
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
                            )}
                          </View>
                        </View>
                      </LinearGradient>
                    </View>

                    {/* Task Queue */}
                    {upcomingTasks.length > 0 && (
                      <View style={styles.section}>
                        <Text style={styles.sectionTitle}>
                          <Ionicons name="flash" size={16} color="#1DE9B6" />{" "}
                          Tasks Due Soon
                        </Text>
                        {upcomingTasks.slice(0, 3).map((task, index) => (
                          <LinearGradient
                            key={task.id || index}
                            colors={[
                              "rgba(26, 26, 26, 0.8)",
                              "rgba(26, 26, 26, 0.4)",
                            ]}
                            style={styles.taskCard}
                          >
                            <View style={styles.taskHeader}>
                              <Text style={styles.taskTitle}>
                                {task.description ||
                                  task.title ||
                                  "Untitled Task"}
                              </Text>
                              <View style={styles.taskPriority}>
                                <View style={styles.priorityDot} />
                              </View>
                            </View>
                            <View style={styles.taskTimeContainer}>
                              <Text style={styles.taskDate}>
                                {task.deadline
                                  ? new Date(task.deadline).toLocaleDateString()
                                  : "No deadline"}
                              </Text>
                              {task.deadline && (
                                <Text style={styles.taskTimeFromNow}>
                                  Due in {getTimeFromNow(task.deadline)}
                                </Text>
                              )}
                            </View>
                          </LinearGradient>
                        ))}
                      </View>
                    )}

                    {/* Control Panel - Only show when setup is complete */}
                    <TouchableOpacity
                      style={styles.controlPanel}
                      onPress={() => navigation.navigate("Settings")}
                    >
                      <LinearGradient
                        colors={["#00926eff", "#007263ff"]}
                        style={styles.controlGradient}
                      >
                        <Ionicons name="settings" size={20} color="#000000" />
                        <Text style={styles.controlText}>CONTROL PANEL</Text>
                        <Ionicons
                          name="chevron-forward"
                          size={20}
                          color="#000000"
                        />
                      </LinearGradient>
                    </TouchableOpacity>
                  </>
                )}
              </View>
            )}
            showsVerticalScrollIndicator={false}
          />
        </>
      )}
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
  // PEBO Robot Styles - Normal Position
  peboRobotContainer: {
    position: "absolute",
    top: height * 0.15,
    right: width * 0.1,
    width: 150,
    height: 150,
    borderRadius: 75,
    overflow: "hidden",
    borderWidth: 2,
    borderColor: "rgba(29, 233, 182, 0.4)",
    shadowColor: "#1DE9B6",
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 20,
    shadowOpacity: 0.6,
  },
  // PEBO Robot Styles - Setup Position (bigger and centered)
  peboRobotContainerSetupBig: {
    position: "absolute",
    top: height * 0.65,
    left: (width - 240) / 2,
    width: 240,
    height: 240,
    borderRadius: 140,
    overflow: "hidden",
    borderWidth: 4,
    borderColor: "rgba(29, 233, 182, 0.8)",
    shadowColor: "#1DE9B6",
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 40,
    shadowOpacity: 1,
  },
  robotTouchArea: {
    width: "100%",
    height: "100%",
    position: "relative",
  },
  peboVideo: {
    width: "100%",
    height: "100%",
    backgroundColor: "transparent",
  },
  greetingBubble: {
    position: "absolute",
    top: -40,
    left: -20,
    backgroundColor: "rgba(29, 233, 182, 0.9)",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 15,
    borderTopLeftRadius: 3,
  },
  greetingText: {
    color: "#000000",
    fontSize: 12,
    fontWeight: "600",
    textAlign: "center",
  },
  // Warning styles
  warningContainer: {
    marginBottom: 20,
    padding: 20,
    borderRadius: 16,
    backgroundColor: "rgba(255, 82, 82, 0.1)",
    borderWidth: 1,
    borderColor: "rgba(255, 82, 82, 0.3)",
    zIndex: 10, // Ensures it's above background
    position: "relative", // Or 'absolute' if you need to stack
  },

  warningHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 12,
  },
  warningTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#FF5252",
    marginLeft: 8,
  },
  warningText: {
    fontSize: 14,
    color: "#FFFFFF",
    marginBottom: 16,
    lineHeight: 20,
  },
  setupProgress: {
    marginBottom: 20,
  },
  setupProgressTitle: {
    fontSize: 14,
    fontWeight: "600",
    color: "#FFFFFF",
    marginBottom: 12,
  },
  setupItems: {
    gap: 8,
  },
  setupItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  setupItemText: {
    fontSize: 14,
    fontWeight: "500",
  },
  warningButton: {
    borderRadius: 12,
    overflow: "hidden",
  },
  warningButtonGradient: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 14,
    paddingHorizontal: 20,
  },
  warningButtonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
    marginLeft: 8,
  },
  // Background elements
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
  // Normal Stats Grid
  statsGrid: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 32,
  },
  // Setup Stats Grid - Moved up and more compact
  statsGridSetup: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 15,
    marginTop: 5,
  },
  // Normal Stat Card
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
  // Small Stat Card for Setup Warning
  statCardSmall: {
    borderRadius: 12,
    padding: 10,
    alignItems: "center",
    flex: 1,
    marginHorizontal: 2,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.3)",
    position: "relative",
    overflow: "hidden",
  },
  statIcon: {
    marginBottom: 8,
  },
  statNumber: {
    fontSize: 28,
    fontWeight: "900",
    color: "#1DE9B6",
    textShadowColor: "#1DE9B6",
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 10,
  },
  // Small stat number for setup warning
  statNumberSmall: {
    fontSize: 16,
    marginBottom: 2,
  },
  stat1Number: {
    fontSize: 14,
    fontWeight: "900",
    color: "#1DE9B6",
    textShadowColor: "#1DE9B6",
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 10,
    textAlign: "center",
  },
  // Small stat1 number for setup warning
  stat1NumberSmall: {
    fontSize: 9,
    marginBottom: 1,
  },
  statLabel: {
    fontSize: 9,
    color: "#888",
    marginTop: 6,
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
  taskTimeContainer: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  taskDate: {
    fontSize: 11,
    color: "#888",
    textTransform: "uppercase",
  },
  taskTimeFromNow: {
    fontSize: 11,
    color: "#1DE9B6",
    fontWeight: "600",
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

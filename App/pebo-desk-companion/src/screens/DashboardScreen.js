import React, { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  FlatList,
} from "react-native";
import { useNavigation, useFocusEffect } from "@react-navigation/native";
import { MaterialIcons, FontAwesome5, Ionicons } from "@expo/vector-icons";
import {
  getWifiName,
  getTaskOverview,
  getPeboDevices,
} from "../services/firebase";
import { auth } from "../services/firebase";

import { getUserName } from "../services/firebase";
const DashboardScreen = () => {
  const [wifiDetails, setWifiDetails] = useState({
    wifiSSID: "",
    wifiPassword: "",
  });
  const [userPebos, setUserPebos] = useState([]);
  const [upcomingTasks, setUpcomingTasks] = useState([]);
  const navigation = useNavigation();
  // const getUserName = () => {
  //   const user = auth.currentUser;
  //   if (user && user.displayName) {
  //     return user.displayName;
  //   } else {
  //     return "Guest"; // Fallback if the user is not logged in
  //   }
  // };
  useFocusEffect(
    useCallback(() => {
      const fetchData = async () => {
        try {
     
          
          // ✅ Fetch tasks
          const tasks = await getTaskOverview();
          console.log("📅 All tasks fetched:", tasks);

          // ✅ Filter upcoming tasks
          const today = new Date();
          const upcoming = tasks.filter((task) => {
            if (task.completed || !task.deadline) return false;

            let due = new Date(task.deadline);
            if (isNaN(due)) {
              if (typeof task.deadline === "number")
                due = new Date(task.deadline);
              else return false;
            }

            const diffDays = (due - today) / (1000 * 60 * 60 * 24);
            const isUpcoming = diffDays >= 0 && diffDays <= 5;

            if (isUpcoming) return true;

            if (task.frequency) {
              const freq = task.frequency.toLowerCase();
              return (
                freq === "daily" ||
                (freq === "weekly" && today.getDay() === due.getDay()) ||
                (freq === "monthly" && today.getDate() === due.getDate())
              );
            }

            return false;
          });

          setUpcomingTasks(upcoming);

          // ✅ Fetch Wi-Fi details
          const wifi = await getWifiName();
          setWifiDetails(wifi);

          // ✅ Fetch user's PEBO devices
          const pebos = await getPeboDevices();
          setUserPebos(pebos);
        } catch (error) {
          console.error("Dashboard Error - fetchData:", error);
        }
      };

      fetchData();
    }, [])
  );
  
  return (
    <View style={styles.container}>
      <Text style={styles.appName}>PEBO</Text>

      {/* ✅ PEBOs Assigned to Current User */}
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Ionicons name="home-outline" size={20} color="#007AFF" />
          <Text style={styles.cardLabel}>Your PEBOs</Text>
        </View>
        {userPebos.length === 0 ? (
          <Text style={styles.empty}>No PEBOs assigned to you</Text>
        ) : (
          userPebos.map((pebo, index) => (
            <View key={index}>
              <Text style={styles.cardValue}>
                {pebo.name} ({pebo.location || "No location"})
              </Text>
            </View>
          ))
        )}
      </View>

      {/* ✅ Wi-Fi Details */}
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <MaterialIcons name="wifi" size={20} color="#007AFF" />
          <Text style={styles.cardLabel}>Wi-Fi Details</Text>
        </View>
        <Text style={styles.cardValue}>SSID: {wifiDetails.wifiSSID}</Text>
        <Text style={styles.cardValue}>
          Password: {wifiDetails.wifiPassword}
        </Text>
      </View>

      {/* ✅ Upcoming Tasks */}
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <FontAwesome5 name="tasks" size={18} color="#007AFF" />
          <Text style={styles.cardLabel}>Tasks Due Soon</Text>
        </View>
        {upcomingTasks.length === 0 ? (
          <Text style={styles.empty}>No tasks due in next few days</Text>
        ) : (
          <FlatList
            data={upcomingTasks}
            keyExtractor={(item) => item.id}
            renderItem={({ item }) => (
              <View style={styles.taskItem}>
                <Text style={styles.taskTitle}>
                  {item.description}{" "}
                  {item.frequency ? `(${item.frequency})` : ""}
                </Text>
                <Text style={styles.taskDate}>
                  {new Date(item.deadline).toLocaleString()}
                </Text>
              </View>
            )}
          />
        )}
      </View>

      {/* ✅ Navigate to Task Management */}
      <TouchableOpacity
        style={styles.button}
        onPress={() => navigation.navigate("Settings")}
      >
        <View style={styles.buttonContent}>
          <Ionicons
            name="settings-outline"
            size={24}
            color="white"
            style={styles.icon}
          />
          <Text style={styles.buttonText}>Change Settings of PEBO</Text>
        </View>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F4F9FF",
    padding: 24,
    paddingTop: 50,
  },
  button: {
    flexDirection: "row", // Aligns the icon and text horizontally
    alignItems: "center", // Vertically centers them
    padding: 10,
    backgroundColor: "#3498db", // Button background color
    borderRadius: 5,
    margin: 10, // Adds some margin to the button
  },
  buttonContent: {
    flexDirection: "row", // Aligns icon and text in a row
    alignItems: "center", // Vertically aligns the icon and text
  },
  icon: {
    marginRight: 10, // Adds space between the icon and text
  },
  buttonText: {
    color: "white", // Text color
    fontSize: 16,
    fontWeight: "600",
  },
  appName: {
    fontSize: 32,
    fontWeight: "bold",
    color: "#007AFF",
    alignSelf: "center",
    marginBottom: 30,
    letterSpacing: 1.5,
  },
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
    shadowColor: "#000000",
    shadowOpacity: 0.05,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 10,
  },
  cardLabel: {
    fontSize: 16,
    color: "#007AFF",
    fontWeight: "600",
    marginLeft: 8,
  },
  cardValue: {
    fontSize: 16,
    fontWeight: "500",
    color: "#222222",
    marginBottom: 6,
  },
  empty: {
    color: "#999999",
    fontStyle: "italic",
  },
  taskItem: {
    marginTop: 10,
    padding: 12,
    backgroundColor: "#EAF2FC",
    borderRadius: 10,
  },
  taskTitle: {
    fontSize: 16,
    fontWeight: "500",
    color: "#1C1C1E",
  },
  taskDate: {
    fontSize: 14,
    color: "#636366",
    marginTop: 4,
  },
  button: {
    backgroundColor: "#007AFF",
    paddingVertical: 14,
    borderRadius: 14,
    alignItems: "center",
    marginTop: 24,
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "600",
  },
});

export default DashboardScreen;

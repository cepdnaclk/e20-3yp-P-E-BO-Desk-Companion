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

  useFocusEffect(
    useCallback(() => {
      const fetchData = async () => {
        try {
          // Fetch tasks
          const tasks = await getTaskOverview();
          console.log("📅 All tasks fetched:", tasks);

          // Filter upcoming tasks
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

          // Fetch Wi-Fi details
          const wifi = await getWifiName();
          setWifiDetails(wifi);

          // Fetch user's PEBO devices
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
      <Text style={styles.appName}>PEBO Dashboard</Text>

      {/* PEBOs Assigned to Current User */}
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Ionicons name="home-outline" size={20} color="#1976D2" />
          <Text style={styles.cardLabel}>My PEBOs</Text>
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

      {/* Wi-Fi Details */}
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <MaterialIcons name="wifi" size={20} color="#1976D2" />
          <Text style={styles.cardLabel}>Wi-Fi Details</Text>
        </View>
        <Text style={styles.cardValue}>SSID: {wifiDetails.wifiSSID}</Text>
        <Text style={styles.cardValue}>
          Password: {wifiDetails.wifiPassword}
        </Text>
      </View>

      {/* Upcoming Tasks */}
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <FontAwesome5 name="tasks" size={18} color="#1976D2" />
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

      {/* Navigate to Task Management */}
      <TouchableOpacity
        style={styles.button}
        onPress={() => navigation.navigate("Settings")}
      >
        <View style={styles.buttonContent}>
          <Ionicons
            name="settings-outline"
            size={24}
            color="#FFFFFF"
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
    flexDirection: "row",
    alignItems: "center",
    padding: 10,
    backgroundColor: "#1976D2",
    borderRadius: 5,
    margin: 10,
  },
  buttonContent: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    flex: 1,
  },
  icon: {
    marginRight: 10,
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "600",
  },
  appName: {
    fontSize: 32,
    fontWeight: "bold",
    color: "#1976D2",
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
    color: "#1976D2",
    fontWeight: "600",
    marginLeft: 8,
  },
  cardValue: {
    fontSize: 16,
    fontWeight: "500",
    color: "#212121",
    marginBottom: 6,
  },
  empty: {
    color: "#757575",
    fontStyle: "italic",
    backgroundColor: "#F5F5F5",
  },
  taskItem: {
    marginTop: 10,
    padding: 12,
    backgroundColor: "#ECEFF1",
    borderRadius: 10,
  },
  taskTitle: {
    fontSize: 16,
    fontWeight: "500",
    color: "#212121",
  },
  taskDate: {
    fontSize: 14,
    color: "#757575",
    marginTop: 4,
  },
});

export default DashboardScreen;

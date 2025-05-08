import React, { useState, useEffect } from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { getAuth } from "firebase/auth";
import { getDeviceStatus, getTaskOverview } from "../services/firebase";


const DashboardScreen = () => {
  const [deviceStatus, setDeviceStatus] = useState("");
  const [taskOverview, setTaskOverview] = useState([]);
  const navigation = useNavigation();

  useEffect(() => {
    const fetchData = async () => {
      const device = await getDeviceStatus();
      const tasks = await getTaskOverview();
      setDeviceStatus(device);
      setTaskOverview(tasks);
    };
    fetchData();
  }, []);

const handleLogout = async () => {
  await getAuth().signOut();
  // Don't manually navigate — MainNavigator will render AuthNavigator based on user == null
};


  return (
    <View style={styles.container}>
      <Text style={styles.title}>Dashboard</Text>

      <View style={styles.card}>
        <Text style={styles.label}>Device Status</Text>
        <Text style={styles.value}>{deviceStatus || "Loading..."}</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.label}>Upcoming Tasks</Text>
        <Text style={styles.value}>{taskOverview.length}</Text>
      </View>

      <TouchableOpacity
        style={styles.button}
        onPress={() => navigation.navigate("Tasks")}
      >
        <Text style={styles.buttonText}>Go to Task Management</Text>
      </TouchableOpacity>

      {/* <TouchableOpacity
        style={[styles.button, styles.logoutButton]}
        onPress={handleLogout}
      >
        <Text style={styles.buttonText}>Logout</Text>
      </TouchableOpacity> */}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F5F7FA",
    padding: 20,
    justifyContent: "center",
    alignItems: "center",
  },
  title: {
    fontSize: 28,
    fontWeight: "bold",
    color: "#333333",
    marginBottom: 30,
  },
  card: {
    backgroundColor: "#FFFFFF",
    width: "100%",
    padding: 20,
    borderRadius: 12,
    marginBottom: 20,
    shadowColor: "#000",
    shadowOpacity: 0.1,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 3,
  },
  label: {
    fontSize: 16,
    color: "#666666",
  },
  value: {
    fontSize: 20,
    fontWeight: "bold",
    color: "#222222",
    marginTop: 6,
  },
  button: {
    backgroundColor: "#3F51B5",
    paddingVertical: 14,
    paddingHorizontal: 30,
    borderRadius: 10,
    marginTop: 20,
    width: "100%",
    alignItems: "center",
  },
  logoutButton: {
    backgroundColor: "#E53935",
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "600",
  },
});

export default DashboardScreen;

import React, { useState, useEffect, useContext } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
} from "react-native";
import { useNavigation } from "@react-navigation/native";
import { Ionicons } from "@expo/vector-icons"; // ✅ Correct Expo-safe import
import { auth, db } from "../services/firebase";
import { ref, get, update } from "firebase/database";
import { signOut } from "firebase/auth";
import { AuthContext } from "../context/AuthContext";
import PopupModal from "../components/PopupModal";

const SettingsScreen = () => {
  const navigation = useNavigation();
  const { setUser } = useContext(AuthContext);
  const [peboName, setPeboName] = useState("");
  const [wifiSSID, setWifiSSID] = useState("");
  const [wifiPassword, setWifiPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const user = auth.currentUser;

  const [modalVisible, setModalVisible] = useState(false);
  const [modalContent, setModalContent] = useState({
    title: "",
    message: "",
    icon: "",
  });

  const showModal = (title, message, icon, onClose = null) => {
    setModalContent({ title, message, icon, onClose });
    setModalVisible(true);
  };

  useEffect(() => {
    if (user) {
      const userSettingsRef = ref(db, `users/${user.uid}/settings`);
      get(userSettingsRef)
        .then((snapshot) => {
          if (snapshot.exists()) {
            const data = snapshot.val();
            setPeboName(data.peboName || "");
            setWifiSSID(data.wifiSSID || "");
            setWifiPassword(data.wifiPassword || "");
          }
        })
        .catch((error) => {
          console.error("Error fetching settings: ", error);
        });
    }
  }, []);

  const saveSettingsToFirebase = () => {
    // Input validation
    if (!peboName.trim() || !wifiSSID.trim() || !wifiPassword.trim()) {
      showModal(
        "Warning",
        "All fields must be filled out.",
        "alert-circle-outline"
      );
      return;
    }

    if (!user) return;

    const settingsRef = ref(db, `users/${user.uid}/settings`);
    update(settingsRef, { peboName, wifiSSID, wifiPassword })
      .then(() =>
        showModal(
          "Saved",
          "Settings updated successfully!",
          "checkmark-circle-outline"
        )
      )
      .catch((error) => {
        console.error("Error saving settings: ", error);
        showModal(
          "❌ Error",
          "Failed to update settings.",
          "close-circle-outline"
        );
      });
  };

  const handleLogout = async () => {
    try {
      await signOut(auth);
      setUser(null);
      showModal(
        "Logged Out",
        "You have been logged out successfully.",
        "log-out-outline",
        () => navigation.replace("Login")
      );
    } catch (error) {
      console.error("Logout failed", error);
      showModal(
        "❌ Error",
        "Failed to log out. Try again.",
        "close-circle-outline"
      );
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.titleContainer}>
        <Text style={styles.title}>
          <Ionicons name="settings-outline" size={24} color="#00796b" /> PEBO
          Settings
        </Text>
      </View>

      {/* Device Settings */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>
          <Ionicons name="hardware-chip-outline" size={20} color="#666" />{" "}
          Device Name
        </Text>
        <TextInput
          style={styles.input}
          placeholder="Enter device name"
          value={peboName}
          onChangeText={setPeboName}
        />
      </View>

      {/* Wi-Fi Settings */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>
          <Ionicons name="wifi-outline" size={20} color="#666" /> Wi-Fi SSID
        </Text>
        <TextInput
          style={styles.input}
          placeholder="Wi-Fi SSID"
          value={wifiSSID}
          onChangeText={setWifiSSID}
        />
        <View style={styles.passwordContainer}>
          <TextInput
            style={styles.input}
            placeholder="Wi-Fi Password"
            value={wifiPassword}
            onChangeText={setWifiPassword}
            secureTextEntry={!showPassword}
          />
          <TouchableOpacity
            style={styles.eyeIcon}
            onPress={() => setShowPassword(!showPassword)}
            accessibilityRole="button"
            accessibilityLabel="Toggle password visibility"
          >
            <Ionicons
              name={showPassword ? "eye-off" : "eye"}
              size={24}
              color="#666"
            />
          </TouchableOpacity>
        </View>
      </View>

      {/* Save Button */}
      <TouchableOpacity style={styles.saveBtn} onPress={saveSettingsToFirebase}>
        <Ionicons name="save-outline" size={20} color="#fff" />
        <Text style={styles.saveBtnText}>Save Settings</Text>
      </TouchableOpacity>

      {/* Logout Button */}
      <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
        <Ionicons name="log-out-outline" size={20} color="#fff" />
        <Text style={styles.logoutBtnText}>Log Out</Text>
      </TouchableOpacity>

      {/* Footer */}
      <Text style={styles.footerText}>
        <Ionicons name="warning-outline" size={16} color="#888" /> More features
        coming soon!
      </Text>

      {/* Popup Modal */}
      <PopupModal
        visible={modalVisible}
        title={modalContent.title}
        message={modalContent.message}
        icon={modalContent.icon}
        onClose={() => {
          setModalVisible(false);
          if (modalContent.onClose) modalContent.onClose();
        }}
      />
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#f9f9f9",
    flex: 1,
  },
  content: {
    padding: 20,
    paddingBottom: 40,
  },
  titleContainer: {
    backgroundColor: "#e0f7fa",
    padding: 15,
    borderRadius: 12,
    marginBottom: 30,
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  title: {
    fontSize: 26,
    fontWeight: "700",
    color: "#00796b",
  },
  section: {
    marginBottom: 25,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: "#666",
    marginBottom: 10,
  },
  input: {
    backgroundColor: "#fff",
    borderRadius: 10,
    borderColor: "#ddd",
    borderWidth: 1,
    padding: 12,
    fontSize: 16,
    marginBottom: 10,
  },
  passwordContainer: {
    position: "relative",
  },
  eyeIcon: {
    position: "absolute",
    right: 16,
    top: 12,
  },
  saveBtn: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#4CAF50",
    padding: 15,
    borderRadius: 10,
    justifyContent: "center",
    marginTop: 10,
  },
  saveBtnText: {
    color: "#fff",
    fontSize: 16,
    marginLeft: 8,
  },
  logoutBtn: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#e53935",
    padding: 15,
    borderRadius: 10,
    justifyContent: "center",
    marginTop: 20,
  },
  logoutBtnText: {
    color: "#fff",
    fontSize: 16,
    marginLeft: 8,
  },
  footerText: {
    textAlign: "center",
    marginTop: 30,
    fontStyle: "italic",
    color: "#888",
  },
});

export default SettingsScreen;

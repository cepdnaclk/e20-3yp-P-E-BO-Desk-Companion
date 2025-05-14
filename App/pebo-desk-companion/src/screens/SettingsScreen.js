import React, { useState, useEffect } from "react";
import {
  ScrollView,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  TextInput,
  Alert,
  Pressable,
  ActivityIndicator,
  Image,
  Platform,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import { MaterialIcons, Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
// Import initialized Firebase compat services
import {
  auth,
  db,
  getWifiName,
  saveWifiSettings,
  addPeboDevice,
  getPeboDevices,
} from "../services/firebase";
import PopupModal from "../components/PopupModal";
// AWS S3 Configuration (to be used with fetch-based upload)

const SettingsScreen = () => {
  const navigation = useNavigation();
  // Wi-Fi state
  const [wifiSSID, setWifiSSID] = useState("");
  const [wifiPassword, setWifiPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSavingWifi, setIsSavingWifi] = useState(false);
  // PEBO management
  const [peboName, setPeboName] = useState("");
  const [peboLocation, setPeboLocation] = useState("");
  const [peboDevices, setPeboDevices] = useState([]);
  // User photo state
  const [userImage, setUserImage] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  // Modals & popups
  const [modalVisible, setModalVisible] = useState(false);
  const [logoutModalVisible, setLogoutModalVisible] = useState(false);
  const [popupVisible, setPopupVisible] = useState(false);
  const [popupContent, setPopupContent] = useState({
    title: "",
    message: "",
    icon: "checkmark-circle",
  });
  // Username state
  const [username, setUsername] = useState("");
  const [usernameModalVisible, setUsernameModalVisible] = useState(false);

  const showPopup = (title, message, icon = "checkmark-circle") => {
    setPopupContent({ title, message, icon });
    setPopupVisible(true);
  };
  // Fetch PEBO devices once
  useEffect(() => {
    (async () => {
      try {
        const devices = await getPeboDevices();
        setPeboDevices(devices);
      } catch (err) {
        console.warn("Error fetching PEBOs:", err);
      }
    })();
  }, []);
  // Fetch Wi-Fi settings once
  useEffect(() => {
    (async () => {
      try {
        const { wifiSSID, wifiPassword } = await getWifiName();
        setWifiSSID(wifiSSID);
        setWifiPassword(wifiPassword);
      } catch (err) {
        console.warn("Error fetching Wi-Fi:", err);
      }
    })();
  }, []);

  // User image capture and upload
  const captureUserImage = async () => {
    setUsernameModalVisible(true);
  };

  // Launch camera after username is entered
  const launchCamera = async () => {
    // Ask for camera permission
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== "granted") {
      showPopup("Error", "Camera permission denied", "alert-circle");
      return;
    }
    // Launch camera
    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      quality: 0.8,
      aspect: [1, 1], // Square aspect ratio for profile pictures
    });
    if (!result.canceled && result.assets?.[0]?.uri) {
      setUserImage(result.assets[0].uri);
      showPopup(
        "Success",
        "Image captured successfully. Please upload it.",
        "camera"
      );
    }
  };

  // Upload user image to S3
  const uploadUserImage = async () => {
    if (!userImage || !username.trim()) {
      showPopup("Error", "Image or username missing", "alert-circle");
      return;
    }

    setIsUploading(true);

    try {
      // Request pre-signed URL from your backend
      const presignResponse = await fetch(
        "https://123339d6-a240-49e2-af25-f54694244a3d-00-6zd2xqyqvgq5.sisko.replit.dev/get-upload-url",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username }),
        }
      );
      const { uploadURL, imageUrl } = await presignResponse.json();

      // Convert image to blob
      const imageResponse = await fetch(userImage);
      const blob = await imageResponse.blob();

      // Upload to S3 using pre-signed URL
      const uploadResult = await fetch(uploadURL, {
        method: "PUT",
        body: blob,
        headers: {
          "Content-Type": "image/jpeg",
        },
      });

      if (uploadResult.ok) {
        showPopup("Success", "Image uploaded successfully", "checkmark-circle");

        // Save image URL to Firebase
        const userId = auth.currentUser?.uid;
        if (userId) {
          await db.ref(`users/${userId}/profileImage`).set(imageUrl);
        }
      } else {
        throw new Error("Upload to S3 failed");
      }
    } catch (error) {
      console.error("Upload error:", error);
      showPopup("Error", "Failed to upload image", "alert-circle");
    } finally {
      setIsUploading(false);
    }
  };
  
  // Save Wi-Fi settings
  const handleSaveWifi = async () => {
    const ssid = wifiSSID.trim();
    const pwd = wifiPassword.trim();
    if (!ssid || !pwd)
      return showPopup("Error", "Enter both SSID and password", "alert-circle");
    if (pwd.length < 6)
      return showPopup(
        "Error",
        "Password must be at least 6 chars",
        "alert-circle"
      );
    setIsSavingWifi(true);
    try {
      await saveWifiSettings({
        peboName: peboName.trim(),
        wifiSSID: ssid,
        wifiPassword: pwd,
      });
      showPopup("Success", "Wi-Fi settings saved", "wifi");
    } catch (err) {
      showPopup("Error", err.message, "alert-circle");
    } finally {
      setIsSavingWifi(false);
    }
  };
  // Add new PEBO device
  const handleAddPebo = async () => {
    const name = peboName.trim();
    const loc = peboLocation.trim();
    if (!name || !loc)
      return showPopup("Error", "Enter PEBO name and location", "alert-circle");
    try {
      await addPeboDevice({ name, location: loc });
      const updated = await getPeboDevices();
      setPeboDevices(updated);
      setModalVisible(false);
      setPeboName("");
      setPeboLocation("");
      showPopup("Success", "New PEBO added!", "add-circle");
    } catch (err) {
      showPopup("Error", err.message, "alert-circle");
    }
  };
  // Logout
  const handleLogout = async () => {
    try {
      await auth.signOut();
      navigation.reset({ index: 0, routes: [{ name: "Login" }] });
    } catch (err) {
      Alert.alert("Logout Error", err.message);
    }
  };

  // We'll remove the UsernameInputModal component declaration and directly render the modal in the return JSX

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Settings</Text>
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* User Image Section */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Ionicons name="person-circle" size={20} color="#007AFF" />
            <Text style={styles.cardLabel}>User Photo</Text>
          </View>
          <View style={{ alignItems: "center", marginVertical: 15 }}>
            {userImage ? (
              <Image
                source={{ uri: userImage }}
                style={{
                  width: 150,
                  height: 150,
                  borderRadius: 75,
                  marginBottom: 10,
                }}
              />
            ) : (
              <View style={styles.placeholderImage}>
                <Ionicons name="person" size={80} color="#ccc" />
              </View>
            )}
            <TouchableOpacity
              onPress={captureUserImage}
              style={styles.photoButton}
            >
              <Ionicons name="camera" size={20} color="#fff" />
              <Text style={styles.photoButtonText}>Capture Your Image</Text>
            </TouchableOpacity>
            {userImage && (
              <TouchableOpacity
                onPress={uploadUserImage}
                style={[
                  styles.uploadButton,
                  isUploading && styles.processingButton,
                ]}
                disabled={isUploading}
              >
                {isUploading ? (
                  <>
                    <ActivityIndicator size="small" color="#fff" />
                    <Text style={styles.photoButtonText}>Uploading...</Text>
                  </>
                ) : (
                  <>
                    <Ionicons name="cloud-upload" size={20} color="#fff" />
                    <Text style={styles.photoButtonText}>Upload to S3</Text>
                  </>
                )}
              </TouchableOpacity>
            )}
          </View>
        </View>
        {/* Wi-Fi Configuration */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <MaterialIcons name="wifi" size={20} color="#007AFF" />
            <Text style={styles.cardLabel}>Wi-Fi Configuration</Text>
          </View>
          <TextInput
            placeholder="SSID"
            style={[styles.input, !wifiSSID.trim() && styles.inputError]}
            value={wifiSSID}
            onChangeText={setWifiSSID}
            placeholderTextColor="#999"
          />
          <View style={{ position: "relative" }}>
            <TextInput
              placeholder="Password"
              style={[
                styles.input,
                (!wifiPassword.trim() || wifiPassword.length < 6) &&
                  styles.inputError,
              ]}
              secureTextEntry={!showPassword}
              value={wifiPassword}
              onChangeText={setWifiPassword}
              placeholderTextColor="#999"
            />
            <TouchableOpacity
              onPress={() => setShowPassword((v) => !v)}
              style={{ position: "absolute", right: 12, top: 12 }}
            >
              <Ionicons
                name={showPassword ? "eye-off" : "eye"}
                size={22}
                color="#999"
              />
            </TouchableOpacity>
          </View>
          <TouchableOpacity
            style={[
              styles.saveButton,
              isSavingWifi && { backgroundColor: "#ddd" },
            ]}
            onPress={handleSaveWifi}
            disabled={isSavingWifi}
          >
            {isSavingWifi ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <>
                <Ionicons name="wifi" size={20} color="#fff" />
                <Text style={styles.saveButtonText}>Save Wi-Fi</Text>
              </>
            )}
          </TouchableOpacity>
        </View>
        {/* Add PEBO */}
        <TouchableOpacity
          style={styles.addButton}
          onPress={() => setModalVisible(true)}
        >
          <Ionicons name="add-circle-outline" size={22} color="#fff" />
          <Text style={styles.addButtonText}>Add New PEBO</Text>
        </TouchableOpacity>
        {/* PEBO Devices List */}
        <View style={{ marginTop: 30 }}>
          <Text style={styles.sectionTitle}>Your PEBO Devices</Text>
          {peboDevices.length === 0 ? (
            <Text style={styles.emptyText}>No PEBO devices found.</Text>
          ) : (
            peboDevices.map((pebo) => (
              <View key={pebo.id} style={styles.peboCard}>
                <View style={styles.peboHeader}>
                  <Ionicons
                    name="hardware-chip-outline"
                    size={24}
                    color="#007AFF"
                  />
                  <View style={styles.peboInfo}>
                    <Text style={styles.peboName}>{pebo.name}</Text>
                    <Text style={styles.peboLocation}>
                      Location: {pebo.location}
                    </Text>
                  </View>
                </View>
              </View>
            ))
          )}
        </View>
        {/* Logout Button */}
        <TouchableOpacity
          style={[
            styles.addButton,
            { backgroundColor: "#FF3B30", marginVertical: 20 },
          ]}
          onPress={() => setLogoutModalVisible(true)}
        >
          <Ionicons name="log-out-outline" size={22} color="#fff" />
          <Text style={styles.addButtonText}>Logout</Text>
        </TouchableOpacity>
      </ScrollView>
      {/* Add PEBO Modal */}
      <Modal
        transparent
        visible={modalVisible}
        animationType="slide"
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Add New PEBO</Text>
            <TextInput
              placeholder="PEBO Name"
              value={peboName}
              onChangeText={setPeboName}
              style={styles.input}
              placeholderTextColor="#999"
            />
            <TextInput
              placeholder="Location (e.g., Kitchen)"
              value={peboLocation}
              onChangeText={setPeboLocation}
              style={styles.input}
              placeholderTextColor="#999"
            />
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={[styles.modalButton, { backgroundColor: "#007AFF" }]}
                onPress={handleAddPebo}
              >
                <Text style={styles.modalButtonText}>Add PEBO</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalButton, { backgroundColor: "#ccc" }]}
                onPress={() => setModalVisible(false)}
              >
                <Text style={[styles.modalButtonText, { color: "#333" }]}>
                  Cancel
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
      {/* Logout Confirmation Modal */}
      <Modal
        transparent
        visible={logoutModalVisible}
        animationType="fade"
        onRequestClose={() => setLogoutModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>
              Are you sure you want to log out?
            </Text>
            <View style={styles.modalButtons}>
              <Pressable
                style={[styles.modalButton, { backgroundColor: "#FF3B30" }]}
                onPress={handleLogout}
              >
                <Text style={styles.modalButtonText}>Logout</Text>
              </Pressable>
              <Pressable
                style={[styles.modalButton, { backgroundColor: "#ccc" }]}
                onPress={() => setLogoutModalVisible(false)}
              >
                <Text style={[styles.modalButtonText, { color: "#333" }]}>
                  Cancel
                </Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
      {/* Username Input Modal */}
      <Modal
        transparent
        visible={usernameModalVisible}
        animationType="fade"
        onRequestClose={() => setUsernameModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Enter Your Name</Text>
            <TextInput
              placeholder="Your name"
              value={username}
              onChangeText={setUsername}
              style={styles.input}
              placeholderTextColor="#999"
              autoCapitalize="words"
            />
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={[styles.modalButton, { backgroundColor: "#007AFF" }]}
                onPress={() => {
                  if (username.trim()) {
                    setUsernameModalVisible(false);
                    launchCamera();
                  } else {
                    showPopup(
                      "Error",
                      "Please enter your name",
                      "alert-circle"
                    );
                  }
                }}
              >
                <Text style={styles.modalButtonText}>Continue</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalButton, { backgroundColor: "#ccc" }]}
                onPress={() => setUsernameModalVisible(false)}
              >
                <Text style={[styles.modalButtonText, { color: "#333" }]}>
                  Cancel
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
      {/* Popup for Success/Error */}
      <PopupModal
        visible={popupVisible}
        onClose={() => setPopupVisible(false)}
        title={popupContent.title}
        message={popupContent.message}
        icon={popupContent.icon}
      />
    </View>
  );
};
export default SettingsScreen;
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F4F9FF",
    padding: 24,
    paddingTop: 50,
  },
  header: {
    fontSize: 28,
    fontWeight: "bold",
    color: "#007AFF",
    marginBottom: 20,
    alignSelf: "center",
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: "700",
    marginBottom: 14,
    color: "#007AFF",
  },
  card: {
    backgroundColor: "#FFF",
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
    shadowColor: "#000",
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 6,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 16,
  },
  cardLabel: {
    fontSize: 16,
    fontWeight: "600",
    marginLeft: 8,
    color: "#007AFF",
  },
  input: {
    backgroundColor: "#F0F4F8",
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
    fontSize: 16,
    color: "#1C1C1E",
  },
  inputError: {
    borderColor: "#FF3B30",
    borderWidth: 1,
  },
  saveButton: {
    backgroundColor: "#007AFF",
    paddingVertical: 12,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 10,
    flexDirection: "row",
    gap: 8,
  },
  saveButtonText: {
    color: "#FFF",
    fontSize: 17,
    fontWeight: "600",
  },
  addButton: {
    flexDirection: "row",
    backgroundColor: "#007AFF",
    borderRadius: 14,
    padding: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  addButtonText: {
    color: "#FFF",
    fontSize: 16,
    fontWeight: "600",
    marginLeft: 10,
  },
  placeholderImage: {
    width: 150,
    height: 150,
    borderRadius: 75,
    backgroundColor: "#F0F4F8",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 10,
  },
  emptyText: {
    color: "#666",
    fontSize: 16,
    marginTop: 10,
    textAlign: "center",
    backgroundColor: "#f0f0f0",
    padding: 20,
    borderRadius: 10,
  },
  peboCard: {
    backgroundColor: "#FFF",
    borderRadius: 14,
    padding: 16,
    marginBottom: 16,
    shadowColor: "#000",
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  peboHeader: {
    flexDirection: "row",
    alignItems: "center",
  },
  peboInfo: {
    marginLeft: 12,
    flex: 1,
  },
  peboName: {
    fontSize: 17,
    fontWeight: "600",
    color: "#1C1C1E",
  },
  peboLocation: {
    fontSize: 13,
    color: "#999",
    marginTop: 2,
  },
  photoButton: {
    flexDirection: "row",
    backgroundColor: "#34C759",
    padding: 12,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    width: "80%",
    marginTop: 10,
  },
  processingButton: {
    backgroundColor: "#999",
  },
  uploadButton: {
    flexDirection: "row",
    backgroundColor: "#00b894",
    padding: 12,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    width: "80%",
    marginTop: 10,
  },
  photoButtonText: {
    color: "#FFF",
    marginLeft: 6,
    fontWeight: "600",
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.4)",
    justifyContent: "center",
    alignItems: "center",
  },
  modalContent: {
    width: "85%",
    backgroundColor: "#FFF",
    borderRadius: 20,
    padding: 24,
    alignItems: "center",
    elevation: 10,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: "600",
    marginBottom: 20,
    textAlign: "center",
    color: "#007AFF",
  },
  modalButtons: {
    flexDirection: "row",
    justifyContent: "space-between",
    width: "100%",
  },
  modalButton: {
    flex: 1,
    padding: 12,
    borderRadius: 10,
    marginHorizontal: 5,
    alignItems: "center",
    backgroundColor: "#007AFF",
  },
  modalButtonText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#FFF",
  },
  usernameInput: {
    backgroundColor: "#F0F4F8",
    borderRadius: 10,
    padding: 12,
    marginBottom: 20,
    fontSize: 16,
    color: "#1C1C1E",
    width: "100%",
  },
});

import React, { useState, useEffect } from "react";
import { ScrollView } from "react-native";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  TextInput,
  Alert,
  Pressable,
} from "react-native";
import { MaterialIcons, Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import {
  auth,
  getWifiName,
  setWifiName,
  addPeboDevice,
  saveWifiSettings,
  getPeboDevices,
  triggerCameraCapture,
} from "../services/firebase";
import { getDatabase, ref, set, onValue } from "firebase/database";
import { Image } from "react-native";
import PopupModal from "../components/PopupModal";
import { ActivityIndicator } from "react-native";
import S3ConfigSection from "../components/S3ConfigSection";
import PeboImageHistory from "../components/PeboImageHistory";

const SettingsScreen = () => {
  const navigation = useNavigation();
  const [wifiSSID, setWifiSSID] = useState("");
  const [wifiPassword, setWifiPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [peboName, setPeboName] = useState("");
  const [modalVisible, setModalVisible] = useState(false);
  const [logoutModalVisible, setLogoutModalVisible] = useState(false);
  const [popupVisible, setPopupVisible] = useState(false);
  const [popupContent, setPopupContent] = useState({
    title: "",
    message: "",
    icon: "checkmark-circle",
  });
  const [isSavingWifi, setIsSavingWifi] = useState(false);
  const [peboLocation, setPeboLocation] = useState("");
  const [peboDevices, setPeboDevices] = useState([]);
  const [selectedPebo, setSelectedPebo] = useState(null);
  const [imageHistoryVisible, setImageHistoryVisible] = useState(false);

  const showPopup = (title, message, icon = "checkmark-circle") => {
    setPopupContent({ title, message, icon });
    setPopupVisible(true);
  };

  const [photoUrlMap, setPhotoUrlMap] = useState({});
  const [processingCamera, setProcessingCamera] = useState({});

useEffect(() => {
  const db = getDatabase();
  const user = auth.currentUser;
  if (!user || peboDevices.length === 0) return;

  const listeners = [];

  peboDevices.forEach((pebo) => {
    const photoRef = ref(db, `peboPhotos/${pebo.id}`);
    const unsubscribe = onValue(photoRef, (snap) => {
      const url = snap.val();
      setPhotoUrlMap((prev) => ({
        ...prev,
        [pebo.id]: url,
      }));
    });

    listeners.push(() => unsubscribe());
  });

  return () => {
    listeners.forEach((unsubscribe) => unsubscribe());
  };
}, [peboDevices]);


  useEffect(() => {
    const fetchPeboDevices = async () => {
      try {
        const pebos = await getPeboDevices();
        setPeboDevices(pebos); // Set the fetched devices in state
      } catch (error) {
        console.log("Error fetching PEBOs:", error.message);
      }
    };
    fetchPeboDevices();
  }, []);

  useEffect(() => {
    const fetchWifi = async () => {
      try {
        const wifi = await getWifiName();
        setWifiSSID(wifi.wifiSSID || "");
        setWifiPassword(wifi.wifiPassword || "");
      } catch (error) {
        console.log("Error fetching Wi-Fi info:", error.message);
      }
    };
    fetchWifi();
  }, []);

  const handleSaveWifi = async () => {
    const trimmedSSID = wifiSSID.trim(); // Trimmed inputs
    const trimmedPassword = wifiPassword.trim();
    if (!trimmedSSID || !trimmedPassword) {
      showPopup(
        "Error",
        "Please enter both Wi-Fi SSID and Password",
        "alert-circle"
      );
      return;
    }
    if (trimmedPassword.length < 6) {
      showPopup(
        "Error",
        "Password must be at least 6 characters long",
        "alert-circle"
      );
      return;
    }
    setIsSavingWifi(true);
    try {
      await saveWifiSettings({
        peboName: peboName.trim(),
        wifiSSID: trimmedSSID,
        wifiPassword: trimmedPassword,
      });
      showPopup("Success", "Wi-Fi info updated for all PEBOs", "wifi");
    } catch (error) {
      showPopup("Error", error.message);
    } finally {
      setIsSavingWifi(false);
    }
  };

  const handleAddPebo = async () => {
    const trimmedName = peboName.trim();
    const trimmedLocation = peboLocation.trim(); // Trimmed location
    if (!trimmedName || !trimmedLocation) {
      showPopup(
        "Error",
        "Please enter both PEBO name and location",
        "alert-circle"
      );
      return;
    }
    try {
      await addPeboDevice({ name: trimmedName, location: trimmedLocation }); // Include location
      const updatedPeboList = await getPeboDevices(); // Fetch updated list
      setPeboDevices(updatedPeboList); // Update state
      setModalVisible(false);
      setPeboName("");
      setPeboLocation(""); // Clear location input
      showPopup("Success", "New PEBO added!", "add-circle");
    } catch (error) {
      showPopup(
        "Error",
        error.message || "Something went wrong",
        "alert-circle"
      );
    }
  };

  const handleCapture = async (peboId) => {
    try {
      setProcessingCamera((prev) => ({ ...prev, [peboId]: true }));
      await triggerCameraCapture(peboId);
      showPopup("📸", "Capturing image...", "camera");
    } catch (error) {
      setProcessingCamera((prev) => ({ ...prev, [peboId]: false }));
      showPopup(
        "Error",
        error.message || "Failed to capture image",
        "alert-circle"
      );
    }
  };

  const handleViewImageHistory = (pebo) => {
    setSelectedPebo(pebo);
    setImageHistoryVisible(true);
  };

  const handleLogout = async () => {
    try {
      await auth.signOut();
      navigation.reset({
        index: 0,
        routes: [{ name: "Login" }],
      });
    } catch (error) {
      Alert.alert("Logout Error", error.message);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Settings</Text>

      <ScrollView showsVerticalScrollIndicator={false}>
        {/* S3 Configuration Section */}
        <S3ConfigSection
          onConfigSaved={() =>
            showPopup("Success", "S3 configuration saved", "cloud-upload")
          }
        />

        {/* Wi-Fi Config */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <MaterialIcons name="wifi" size={20} color="#007AFF" />
            <Text style={styles.cardLabel}>Wi-Fi Configuration</Text>
          </View>
          <TextInput
            placeholder="SSID"
            style={[
              styles.input,
              !wifiSSID.trim() && styles.inputError, // Show error style if empty
            ]}
            value={wifiSSID}
            onChangeText={setWifiSSID}
            placeholderTextColor="#999"
            accessibilityLabel="Wi-Fi SSID"
          />
          <View style={{ position: "relative" }}>
            <TextInput
              placeholder="Password"
              style={[
                styles.input,
                (!wifiPassword.trim() || wifiPassword.length < 6) &&
                  styles.inputError, // Error visual
              ]}
              secureTextEntry={!showPassword}
              value={wifiPassword}
              onChangeText={setWifiPassword}
              placeholderTextColor="#999"
              accessibilityLabel="Wi-Fi Password"
            />
            <TouchableOpacity
              onPress={() => setShowPassword(!showPassword)}
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
          <Ionicons name="add-circle-outline" size={22} color="white" />
          <Text style={styles.addButtonText}>Add New PEBO</Text>
        </TouchableOpacity>

        {/* PEBO Devices */}
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

                {/* Camera controls */}
                <View style={styles.peboControls}>
                  <TouchableOpacity
                    style={[
                      styles.photoButton,
                      processingCamera[pebo.id] && styles.processingButton,
                    ]}
                    onPress={() => handleCapture(pebo.id)}
                    disabled={processingCamera[pebo.id]}
                  >
                    {processingCamera[pebo.id] ? (
                      <>
                        <ActivityIndicator size="small" color="#fff" />
                        <Text style={styles.photoButtonText}>
                          Processing...
                        </Text>
                      </>
                    ) : (
                      <>
                        <Ionicons name="camera" size={20} color="#fff" />
                        <Text style={styles.photoButtonText}>
                          Capture Photo
                        </Text>
                      </>
                    )}
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={styles.historyButton}
                    onPress={() => handleViewImageHistory(pebo)}
                  >
                    <Ionicons name="images-outline" size={20} color="#fff" />
                    <Text style={styles.photoButtonText}>View History</Text>
                  </TouchableOpacity>
                </View>

                {/* Display current image */}
                {photoUrlMap[pebo.id] && (
                  <View style={styles.imageContainer}>
                    <Text style={styles.latestImageText}>Latest Image:</Text>
                    <Image
                      source={{ uri: photoUrlMap[pebo.id] }}
                      style={styles.thumbnail}
                    />
                  </View>
                )}
              </View>
            ))
          )}
        </View>

        {/* Logout */}
        <TouchableOpacity
          style={[
            styles.addButton,
            { backgroundColor: "#FF3B30" },
            { marginVertical: 20 },
          ]}
          onPress={() => setLogoutModalVisible(true)}
        >
          <Ionicons name="log-out-outline" size={22} color="white" />
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
            {/* PEBO Name Input */}
            <TextInput
              placeholder="Enter PEBO Name"
              value={peboName}
              onChangeText={setPeboName}
              style={styles.input}
              placeholderTextColor="#999"
            />
            {/* PEBO Location Input */}
            <TextInput
              placeholder="Enter Location (e.g., Kitchen)"
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

      {/* Image History Modal */}
      <Modal
        transparent
        visible={imageHistoryVisible}
        animationType="slide"
        onRequestClose={() => setImageHistoryVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, styles.historyModal]}>
            <View style={styles.historyModalHeader}>
              <Text style={styles.modalTitle}>Image History</Text>
              <TouchableOpacity
                style={styles.closeModalButton}
                onPress={() => setImageHistoryVisible(false)}
              >
                <Ionicons name="close" size={24} color="#007AFF" />
              </TouchableOpacity>
            </View>

            {selectedPebo && (
              <PeboImageHistory
                peboId={selectedPebo.id}
                peboName={selectedPebo.name}
              />
            )}
          </View>
        </View>
      </Modal>

      {/* Logout Modal */}
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
    backgroundColor: "#FFFFFF",
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
    color: "#FFFFFF",
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
    color: "white",
    fontSize: 16,
    fontWeight: "600",
    marginLeft: 10,
  },
  peboCard: {
    backgroundColor: "#fff",
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
    marginBottom: 12,
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
  peboControls: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 10,
  },
  photoButton: {
    flexDirection: "row",
    backgroundColor: "#34C759",
    padding: 10,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    flex: 1,
    marginRight: 8,
  },
  processingButton: {
    backgroundColor: "#999",
  },
  historyButton: {
    flexDirection: "row",
    backgroundColor: "#5856D6",
    padding: 10,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    flex: 1,
    marginLeft: 8,
  },
  photoButtonText: {
    color: "#fff",
    marginLeft: 6,
    fontWeight: "600",
  },
  imageContainer: {
    marginTop: 10,
  },
  latestImageText: {
    fontSize: 14,
    color: "#666",
    marginBottom: 6,
  },
  thumbnail: {
    width: "100%",
    height: 180,
    borderRadius: 8,
    resizeMode: "cover",
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
  historyModal: {
    width: "90%",
    maxHeight: "80%",
  },
  historyModalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    width: "100%",
    marginBottom: 15,
  },
  closeModalButton: {
    padding: 5,
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
  },
  modalButtonText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#FFF",
  },
});

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
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import { MaterialIcons, Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import QRCode from "react-native-qrcode-svg"; // Added for QR code generation
import {
  auth,
  db,
  getWifiName,
  saveWifiSettings,
  addPeboDevice,
  getPeboDevices,
} from "../services/firebase";
import PopupModal from "../components/PopupModal";

const SettingsScreen = () => {
  const navigation = useNavigation();
  const [wifiSSID, setWifiSSID] = useState("");
  const [wifiPassword, setWifiPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSavingWifi, setIsSavingWifi] = useState(false);
  const [peboName, setPeboName] = useState("");
  const [peboLocation, setPeboLocation] = useState("");
  const [peboDevices, setPeboDevices] = useState([]);
  const [userImage, setUserImage] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [logoutModalVisible, setLogoutModalVisible] = useState(false);
  const [qrModalVisible, setQrModalVisible] = useState(false); // Added for QR code modal
  const [popupVisible, setPopupVisible] = useState(false);
  const [popupContent, setPopupContent] = useState({
    title: "",
    message: "",
    icon: "checkmark-circle",
  });
  const [username, setUsername] = useState("");
  const [usernameModalVisible, setUsernameModalVisible] = useState(false);

  const BUCKET_NAME = "pebo-user-images";
  const API_GATEWAY_URL =
    "https://aw8yn9cbj1.execute-api.us-east-1.amazonaws.com/prod/presigned";

  const showPopup = (title, message, icon = "checkmark-circle") => {
    setPopupContent({ title, message, icon });
    setPopupVisible(true);
  };

  useEffect(() => {
    const fetchPeboDevices = async () => {
      try {
        const devices = await getPeboDevices();
        setPeboDevices(devices);
      } catch (err) {
        console.warn("Error fetching PEBOs:", err);
      }
    };

    const fetchWifiSettings = async () => {
      try {
        const { wifiSSID, wifiPassword } = await getWifiName();
        setWifiSSID(wifiSSID);
        setWifiPassword(wifiPassword);
      } catch (err) {
        console.warn("Error fetching Wi-Fi:", err);
      }
    };

    const userId = auth.currentUser?.uid;
    let unsubscribe;
    if (userId) {
      const profileImageRef = db.ref(`users/${userId}/profileImage`);
      unsubscribe = profileImageRef.on(
        "value",
        (snapshot) => {
          if (snapshot) {
            const imageUrl = snapshot.exists() ? snapshot.val() : null;
            console.log("Firebase profileImage:", imageUrl);
            setUserImage(imageUrl);
          } else {
            console.warn("Snapshot is undefined");
            setUserImage(null);
          }
        },
        (error) => {
          console.error("Firebase listener error:", error);
          setUserImage(null);
        }
      );
    } else {
      console.warn("No userId available, skipping profile image listener");
      setUserImage(null);
    }

    fetchPeboDevices();
    fetchWifiSettings();

    return () => {
      if (unsubscribe) {
        unsubscribe();
      }
    };
  }, []);

  const captureAndUploadImage = async () => {
    if (!username.trim()) {
      showPopup("Error", "How PEBO Should call you? ", "alert-circle");
      return;
    }

    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== "granted") {
      showPopup("Error", "Camera permission denied", "alert-circle");
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      quality: 0.6,
      aspect: [1, 1],
    });

    if (result.canceled || !result.assets?.[0]?.uri) {
      setUsernameModalVisible(false);
      return;
    }

    setIsProcessing(true);
    setUsernameModalVisible(false);
    const imageUri = result.assets[0].uri;

    try {
      const sanitizedUsername = username
        .toLowerCase()
        .replace(/[^a-z0-9]/g, "_");
      const objectName = `user_${sanitizedUsername}.jpg`;

      const response = await fetch(
        `${API_GATEWAY_URL}?username=${encodeURIComponent(sanitizedUsername)}`
      );

      if (!response.ok) {
        throw new Error(
          `API request failed: ${response.status} ${response.statusText}`
        );
      }

      const data = await response.json();
      let presignedUrl;
      if (data.body) {
        const body =
          typeof data.body === "string" ? JSON.parse(data.body) : data.body;
        presignedUrl = body.presignedUrl;
      } else if (data.presignedUrl) {
        presignedUrl = data.presignedUrl;
      } else {
        throw new Error(
          "Pre-signed URL not found in response: " + JSON.stringify(data)
        );
      }

      if (!presignedUrl) {
        throw new Error("Pre-signed URL is missing or invalid");
      }

      const imageResponse = await fetch(imageUri);
      const blob = await imageResponse.blob();
      const uploadResponse = await fetch(presignedUrl, {
        method: "PUT",
        body: blob,
        headers: { "Content-Type": "image/jpeg" },
      });

      if (!uploadResponse.ok) {
        throw new Error(`S3 upload failed: ${response.statusText}`);
      }

      const s3Url = `https://${BUCKET_NAME}.s3.amazonaws.com/${objectName}`;
      console.log("S3 URL:", s3Url);
      const userId = auth.currentUser?.uid;
      if (userId) {
        await db.ref(`users/${userId}/profileImage`).set(s3Url);
        await db.ref(`users/${userId}/imageHistory`).push({
          url: s3Url,
          timestamp: new Date().toISOString(),
          path: objectName,
        });
      }

      setUserImage(s3Url);
      showPopup(
        "Success",
        "Image captured and uploaded successfully",
        "checkmark-circle"
      );
      setUsername("");
    } catch (error) {
      console.error("Upload error:", error);
      showPopup(
        "Error",
        `Failed to process image: ${error.message}`,
        "alert-circle"
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSaveWifi = async () => {
    const ssid = wifiSSID.trim();
    const pwd = wifiPassword.trim();
    if (!ssid || !pwd) {
      showPopup("Error", "Enter both SSID and password", "alert-circle");
      return;
    }
    if (pwd.length < 6) {
      showPopup(
        "Error",
        "Password must be at least 6 characters",
        "alert-circle"
      );
      return;
    }
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

  const handleShowQrCode = () => {
    if (!wifiSSID.trim() || !wifiPassword.trim()) {
      showPopup(
        "Error",
        "Please save valid Wi-Fi settings first",
        "alert-circle"
      );
      return;
    }
    setQrModalVisible(true);
  };

  const generateQrCodeValue = () => {
    const credentials = {
      ssid: wifiSSID.trim(),
      password: wifiPassword.trim(),
    };
    return JSON.stringify(credentials);
  };

  const handleAddPebo = async () => {
    const name = peboName.trim();
    const loc = peboLocation.trim();
    if (!name || !loc) {
      showPopup("Error", "Enter PEBO name and location", "alert-circle");
      return;
    }
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

  const handleLogout = async () => {
    try {
      await auth.signOut();
      navigation.reset({ index: 0, routes: [{ name: "Login" }] });
    } catch (err) {
      Alert.alert("Logout Error", err.message);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Seeeeeettings</Text>
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Ionicons name="person-circle" size={20} color="#007AFF" />
            <Text style={styles.cardLabel}>User Photo</Text>
          </View>
          <View style={{ alignItems: "center", marginVertical: 15 }}>
            {userImage && userImage !== "" ? (
              <Image
                source={{
                  uri: `${userImage}?t=${Date.now()}`,
                  cache: "reload",
                }}
                style={{
                  width: 150,
                  height: 150,
                  borderRadius: 75,
                  marginBottom: 10,
                }}
                onError={(e) =>
                  console.log("Image load error:", e.nativeEvent.error)
                }
              />
            ) : (
              <View style={styles.placeholderImage}>
                <Ionicons name="person" size={80} color="#ccc" />
                <Text style={styles.placeholderText}>No Image</Text>
              </View>
            )}
            <TouchableOpacity
              onPress={() => setUsernameModalVisible(true)}
              style={[
                styles.photoButton,
                isProcessing && styles.processingButton,
              ]}
              disabled={isProcessing}
            >
              {isProcessing ? (
                <>
                  <ActivityIndicator size="small" color="#fff" />
                  <Text style={styles.photoButtonText}>Processing...</Text>
                </>
              ) : (
                <>
                  <Ionicons name="camera" size={20} color="#fff" />
                  <Text style={styles.photoButtonText}>Capture New Image</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        </View>
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
          <TouchableOpacity
            style={[styles.saveButton, { backgroundColor: "#34C759" }]}
            onPress={handleShowQrCode}
            disabled={!wifiSSID.trim() || !wifiPassword.trim()}
          >
            <Ionicons name="qr-code" size={20} color="#fff" />
            <Text style={styles.saveButtonText}>Show QR Code</Text>
          </TouchableOpacity>
        </View>
        <TouchableOpacity
          style={styles.addButton}
          onPress={() => setModalVisible(true)}
        >
          <Ionicons name="add-circle-outline" size={22} color="#fff" />
          <Text style={styles.addButtonText}>Add New PEBO</Text>
        </TouchableOpacity>
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
                onPress={captureAndUploadImage}
              >
                <Text style={styles.modalButtonText}>Capture & Save</Text>
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
      <Modal
        transparent
        visible={qrModalVisible}
        animationType="fade"
        onRequestClose={() => setQrModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Wi-Fi QR Code</Text>
            <Text style={styles.modalSubtitle}>
              Show this QR code to PEBO's camera to configure Wi-Fi
            </Text>
            <View style={styles.qrCodeContainer}>
              <QRCode
                value={generateQrCodeValue()}
                size={200}
                backgroundColor="#FFF"
                color="#000"
              />
            </View>
            <TouchableOpacity
              style={[styles.modalButton, { backgroundColor: "#ccc" }]}
              onPress={() => setQrModalVisible(false)}
            >
              <Text style={[styles.modalButtonText, { color: "#333" }]}>
                Close
              </Text>
            </TouchableOpacity>
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
    borderWidth: 1,
    borderColor: "#ccc",
  },
  placeholderText: {
    color: "#999",
    fontSize: 14,
    marginTop: 5,
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
    marginBottom: 15,
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
  modalSubtitle: {
    fontSize: 14,
    color: "#666",
    marginBottom: 20,
    textAlign: "center",
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
  qrCodeContainer: {
    backgroundColor: "#FFF",
    padding: 20,
    borderRadius: 10,
    marginBottom: 20,
  },
});
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
  StatusBar,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import { MaterialIcons, Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import QRCode from "react-native-qrcode-svg";
import {
  auth,
  db,
  getWifiName,
  saveWifiSettings,
  addPeboDevice,
  getPeboDevices,
  updatePeboDevice,
  removePeboDevice,
} from "../services/firebase";
import PopupModal from "../components/PopupModal";

const SettingsScreen = () => {
  const navigation = useNavigation();
  const [wifiSSID, setWifiSSID] = useState("");
  const [wifiPassword, setWifiPassword] = useState("");
  const [originalWifiSSID, setOriginalWifiSSID] = useState("");
  const [originalWifiPassword, setOriginalWifiPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSavingWifi, setIsSavingWifi] = useState(false);
  const [peboName, setPeboName] = useState("");
  const [peboLocation, setPeboLocation] = useState("");
  const [peboDevices, setPeboDevices] = useState([]);
  const [userImage, setUserImage] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [logoutModalVisible, setLogoutModalVisible] = useState(false);
  const [qrModalVisible, setQrModalVisible] = useState(false);
  const [editPeboModalVisible, setEditPeboModalVisible] = useState(false);
  const [selectedPebo, setSelectedPebo] = useState(null);
  const [editPeboName, setEditPeboName] = useState("");
  const [editPeboLocation, setEditPeboLocation] = useState("");
  const [isUpdatingPebo, setIsUpdatingPebo] = useState(false);
  const [isRemovingPebo, setIsRemovingPebo] = useState(false);
  const [popupVisible, setPopupVisible] = useState(false);
  const [removeModalVisible, setRemoveModalVisible] = useState(false);
  const [popupContent, setPopupContent] = useState({
    title: "",
    message: "",
    icon: "checkmark-circle",
  });
  const [username, setUsername] = useState("");
  const [usernameModalVisible, setUsernameModalVisible] = useState(false);
  const [imageTimestamp, setImageTimestamp] = useState(Date.now());

  const BUCKET_NAME = "pebo-user-images";
  const API_GATEWAY_URL =
    "https://aw8yn9cbj1.execute-api.us-east-1.amazonaws.com/prod/presigned";

  const showPopup = (title, message, icon = "checkmark-circle") => {
    setPopupContent({ title, message, icon });
    setPopupVisible(true);
  };

  // Check if WiFi settings have changed
  const hasWifiChanged = () => {
    return wifiSSID.trim() !== originalWifiSSID.trim() || 
           wifiPassword.trim() !== originalWifiPassword.trim();
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
        setOriginalWifiSSID(wifiSSID);
        setOriginalWifiPassword(wifiPassword);
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
            setImageTimestamp(Date.now());
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
      
      // Update original values after successful save
      setOriginalWifiSSID(ssid);
      setOriginalWifiPassword(pwd);
      
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

  const handleEditPebo = (pebo) => {
    setSelectedPebo(pebo);
    setEditPeboName(pebo.name);
    setEditPeboLocation(pebo.location);
    setEditPeboModalVisible(true);
  };

  const handleUpdatePebo = async () => {
    const name = editPeboName.trim();
    const loc = editPeboLocation.trim();

    if (!name || !loc) {
      showPopup("Error", "Enter PEBO name and location", "alert-circle");
      return;
    }

    setIsUpdatingPebo(true);
    try {
      await updatePeboDevice(selectedPebo.id, { name, location: loc });
      const updated = await getPeboDevices();
      setPeboDevices(updated);
      setEditPeboModalVisible(false);
      setSelectedPebo(null);
      setEditPeboName("");
      setEditPeboLocation("");
      showPopup("Success", "PEBO updated successfully!", "checkmark-circle");
    } catch (err) {
      showPopup("Error", err.message, "alert-circle");
    } finally {
      setIsUpdatingPebo(false);
    }
  };

 const handleRemovePebo = async () => {
   setRemoveModalVisible(true);
 };

 const confirmRemovePebo = async () => {
   setIsRemovingPebo(true);
   try {
     await removePeboDevice(selectedPebo.id);
     const updated = await getPeboDevices();
     setPeboDevices(updated);
     setEditPeboModalVisible(false);
     setRemoveModalVisible(false);
     setSelectedPebo(null);
     setEditPeboName("");
     setEditPeboLocation("");
     showPopup("Success", "PEBO removed successfully!", "checkmark-circle");
   } catch (err) {
     showPopup("Error", err.message, "alert-circle");
   } finally {
     setIsRemovingPebo(false);
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
    <>
      <StatusBar barStyle="light-content" backgroundColor="#0A0A0A" />
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Settings</Text>
          <TouchableOpacity
            style={styles.logoutButton}
            onPress={() => setLogoutModalVisible(true)}
          >
            <Ionicons name="log-out-outline" size={24} color="#1DE9B6" />
          </TouchableOpacity>
        </View>

        <ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.scrollContent}
        >
          {/* Profile Section */}
          <View style={styles.profileSection}>
            <View style={styles.profileImageContainer}>
              {userImage && userImage !== "" ? (
                <Image
                  source={{
                    uri: `${userImage}?t=${imageTimestamp}`,
                    cache: "reload",
                  }}
                  style={styles.profileImage}
                  onError={(e) =>
                    console.log("Image load error:", e.nativeEvent.error)
                  }
                />
              ) : (
                <View style={styles.placeholderImage}>
                  <Ionicons name="person" size={60} color="#555" />
                </View>
              )}
              <View style={styles.profileImageOverlay}>
                <TouchableOpacity
                  onPress={() => setUsernameModalVisible(true)}
                  style={styles.cameraButton}
                  disabled={isProcessing}
                >
                  {isProcessing ? (
                    <ActivityIndicator size="small" color="#1DE9B6" />
                  ) : (
                    <Ionicons name="camera" size={20} color="#1DE9B6" />
                  )}
                </TouchableOpacity>
              </View>
            </View>
            <Text style={styles.profileText}>Profile Photo</Text>
          </View>

          {/* Wi-Fi Configuration */}
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <MaterialIcons name="wifi" size={24} color="#1DE9B6" />
              <Text style={styles.sectionTitle}>Wi-Fi Configuration</Text>
              {hasWifiChanged() && (
                <Pressable
                  style={[
                    styles.saveButton,
                    styles.compactSaveButton,
                    isSavingWifi && styles.saveButtonDisabled,
                  ]}
                  onPress={handleSaveWifi}
                  disabled={isSavingWifi}
                >
                  {isSavingWifi ? (
                    <ActivityIndicator color="#0A0A0A" size="small" />
                  ) : (
                    <>
                      <Ionicons name="save-outline" size={18} color="#0A0A0A" />
                      <Text style={styles.compactSaveButtonText}>Save</Text>
                    </>
                  )}
                </Pressable>
              )}
            </View>

            <View style={styles.inputContainer}>
              <View style={styles.inputWrapper}>
                <Ionicons name="wifi-outline" size={20} color="#888" />
                <TextInput
                  placeholder="Network SSID"
                  style={styles.input}
                  value={wifiSSID}
                  onChangeText={setWifiSSID}
                  placeholderTextColor="#888"
                />
              </View>
              <View style={styles.inputWrapper}>
                <Ionicons name="lock-closed-outline" size={20} color="#888" />
                <TextInput
                  placeholder="Password"
                  style={[styles.input, { flex: 1 }]}
                  secureTextEntry={!showPassword}
                  value={wifiPassword}
                  onChangeText={setWifiPassword}
                  placeholderTextColor="#888"
                />
                <Pressable
                  onPress={() => setShowPassword((v) => !v)}
                  style={styles.eyeButton}
                >
                  <Ionicons
                    name={showPassword ? "eye-off" : "eye"}
                    size={20}
                    color="#888"
                  />
                </Pressable>
              </View>
            </View>

            <View style={styles.buttonRow}>
              <Pressable
                style={[
                  styles.actionButton,
                  styles.qrButton,
                  (!wifiSSID.trim() || !wifiPassword.trim()) &&
                    styles.qrButtonDisabled,
                ]}
                onPress={handleShowQrCode}
                disabled={!wifiSSID.trim() || !wifiPassword.trim()}
              >
                <Ionicons name="qr-code-outline" size={20} color="#1DE9B6" />
                <Text style={styles.qrButtonText}>QR Code</Text>
              </Pressable>
            </View>
          </View>

          {/* PEBO Devices */}
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Ionicons
                name="hardware-chip-outline"
                size={24}
                color="#1DE9B6"
              />
              <Text style={styles.sectionTitle}>PEBO Devices</Text>
              <TouchableOpacity
                style={styles.addDeviceButton}
                onPress={() => setModalVisible(true)}
              >
                <Ionicons name="add" size={20} color="#1DE9B6" />
              </TouchableOpacity>
            </View>

            {peboDevices.length === 0 ? (
              <View style={styles.emptyState}>
                <Ionicons name="hardware-chip-outline" size={48} color="#555" />
                <Text style={styles.emptyStateText}>No PEBO devices found</Text>
                <Text style={styles.emptyStateSubtext}>
                  Add your first device to get started
                </Text>
              </View>
            ) : (
              <View style={styles.devicesList}>
                {peboDevices.map((pebo, index) => (
                  <Pressable
                    key={pebo.id}
                    style={styles.deviceCard}
                    onPress={() => handleEditPebo(pebo)}
                  >
                    <View style={styles.deviceIcon}>
                      <Ionicons
                        name="hardware-chip"
                        size={24}
                        color="#1DE9B6"
                      />
                    </View>
                    <View style={styles.deviceInfo}>
                      <Text style={styles.deviceName}>{pebo.name}</Text>
                      <Text style={styles.deviceLocation}>{pebo.location}</Text>
                    </View>
                    <View style={styles.deviceActions}>
                      <View style={styles.deviceStatus}>
                        <View style={styles.statusDot} />
                        <Text style={styles.statusText}>Online</Text>
                      </View>
                      <Ionicons name="chevron-forward" size={20} color="#888" />
                    </View>
                  </Pressable>
                ))}
              </View>
            )}
          </View>
        </ScrollView>

        {/* Add PEBO Modal */}
        <Modal
          transparent
          visible={modalVisible}
          animationType="fade"
          onRequestClose={() => setModalVisible(false)}
        >
          <View style={styles.modalOverlay}>
            <View style={styles.modalContent}>
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>Add New PEBO</Text>
                <TouchableOpacity
                  onPress={() => setModalVisible(false)}
                  style={styles.closeButton}
                >
                  <Ionicons name="close" size={24} color="#888" />
                </TouchableOpacity>
              </View>

              <View style={styles.modalInputContainer}>
                <View style={styles.inputWrapper}>
                  <Ionicons
                    name="hardware-chip-outline"
                    size={20}
                    color="#888"
                  />
                  <TextInput
                    placeholder="Device Name"
                    value={peboName}
                    onChangeText={setPeboName}
                    style={styles.input}
                    placeholderTextColor="#888"
                  />
                </View>
                <View style={styles.inputWrapper}>
                  <Ionicons name="location-outline" size={20} color="#888" />
                  <TextInput
                    placeholder="Location (e.g., Kitchen)"
                    value={peboLocation}
                    onChangeText={setPeboLocation}
                    style={styles.input}
                    placeholderTextColor="#888"
                  />
                </View>
              </View>

              <TouchableOpacity
                style={[
                  styles.actionButton,
                  styles.saveButton,
                  { width: "100%" },
                ]}
                onPress={handleAddPebo}
              >
                <Ionicons name="add" size={20} color="#0A0A0A" />
                <Text style={styles.saveButtonText}>Add Device</Text>
              </TouchableOpacity>
            </View>
          </View>
        </Modal>

        {/* Edit PEBO Modal */}
        <Modal
          transparent
          visible={editPeboModalVisible}
          animationType="fade"
          onRequestClose={() => setEditPeboModalVisible(false)}
        >
          <View style={styles.modalOverlay}>
            <View style={styles.modalContent}>
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>Edit PEBO Device</Text>
                <TouchableOpacity
                  onPress={() => setEditPeboModalVisible(false)}
                  style={styles.closeButton}
                >
                  <Ionicons name="close" size={24} color="#888" />
                </TouchableOpacity>
              </View>

              <View style={styles.modalInputContainer}>
                <View style={styles.inputWrapper}>
                  <Ionicons
                    name="hardware-chip-outline"
                    size={20}
                    color="#888"
                  />
                  <TextInput
                    placeholder="Device Name"
                    value={editPeboName}
                    onChangeText={setEditPeboName}
                    style={styles.input}
                    placeholderTextColor="#888"
                  />
                </View>
                <View style={styles.inputWrapper}>
                  <Ionicons name="location-outline" size={20} color="#888" />
                  <TextInput
                    placeholder="Location (e.g., Kitchen)"
                    value={editPeboLocation}
                    onChangeText={setEditPeboLocation}
                    style={styles.input}
                    placeholderTextColor="#888"
                  />
                </View>
              </View>
              {/* Remove PEBO Confirmation Modal */}
              <Modal
                transparent
                visible={removeModalVisible}
                animationType="fade"
                onRequestClose={() => setRemoveModalVisible(false)}
              >
                <View style={styles.modalOverlay}>
                  <View style={styles.modalContent}>
                    <View style={styles.modalHeader}>
                      <Text style={styles.modalTitle}>Remove PEBO</Text>
                      <TouchableOpacity
                        onPress={() => setRemoveModalVisible(false)}
                        style={styles.closeButton}
                      >
                        <Ionicons name="close" size={24} color="#888" />
                      </TouchableOpacity>
                    </View>
                    <Text style={styles.confirmationText}>
                      Are you sure you want to remove "{selectedPebo?.name}"?
                    </Text>
                    <Text style={styles.confirmationSubtext}>
                      This action cannot be undone.
                    </Text>
                    <View style={styles.buttonRow}>
                      <TouchableOpacity
                        style={[styles.actionButton, styles.cancelButton]}
                        onPress={() => setRemoveModalVisible(false)}
                      >
                        <Text style={styles.cancelButtonText}>Cancel</Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={[styles.actionButton, styles.removeButton]}
                        onPress={confirmRemovePebo}
                        disabled={isRemovingPebo}
                      >
                        {isRemovingPebo ? (
                          <ActivityIndicator color="#FFFFFF" size="small" />
                        ) : (
                          <>
                            <Ionicons
                              name="trash-outline"
                              size={20}
                              color="#FFFFFF"
                            />
                            <Text style={styles.removeButtonText}>Remove</Text>
                          </>
                        )}
                      </TouchableOpacity>
                    </View>
                  </View>
                </View>
              </Modal>
              <View style={styles.modalButtonRow}>
                <TouchableOpacity
                  style={[styles.actionButton, styles.removeButton]}
                  onPress={handleRemovePebo}
                  disabled={isRemovingPebo}
                >
                  {isRemovingPebo ? (
                    <ActivityIndicator color="#FFFFFF" size="small" />
                  ) : (
                    <>
                      <Ionicons
                        name="trash-outline"
                        size={20}
                        color="#FFFFFF"
                      />
                      <Text style={styles.removeButtonText}>Remove</Text>
                    </>
                  )}
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.actionButton, styles.saveButton]}
                  onPress={handleUpdatePebo}
                  disabled={isUpdatingPebo}
                >
                  {isUpdatingPebo ? (
                    <ActivityIndicator color="#0A0A0A" size="small" />
                  ) : (
                    <>
                      <Ionicons name="save-outline" size={20} color="#0A0A0A" />
                      <Text style={styles.saveButtonText}>Update</Text>
                    </>
                  )}
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </Modal>

        {/* Username Modal */}
        <Modal
          transparent
          visible={usernameModalVisible}
          animationType="fade"
          onRequestClose={() => setUsernameModalVisible(false)}
        >
          <View style={styles.modalOverlay}>
            <View style={styles.modalContent}>
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>How PEBO Should Call You!</Text>
                <TouchableOpacity
                  onPress={() => setUsernameModalVisible(false)}
                  style={styles.closeButton}
                >
                  <Ionicons name="close" size={24} color="#888" />
                </TouchableOpacity>
              </View>

              <View style={styles.modalInputContainer}>
                <View style={styles.inputWrapper}>
                  <Ionicons name="person-outline" size={20} color="#888" />
                  <TextInput
                    placeholder="Preferred name"
                    value={username}
                    onChangeText={setUsername}
                    style={styles.input}
                    placeholderTextColor="#888"
                    autoCapitalize="words"
                  />
                </View>
              </View>

              <TouchableOpacity
                style={[
                  styles.actionButton,
                  styles.saveButton,
                  { width: "100%" },
                ]}
                onPress={captureAndUploadImage}
              >
                <Ionicons name="camera" size={20} color="#0A0A0A" />
                <Text style={styles.saveButtonText}>Capture & Save</Text>
              </TouchableOpacity>
            </View>
          </View>
        </Modal>

        {/* QR Code Modal */}
        <Modal
          transparent
          visible={qrModalVisible}
          animationType="fade"
          onRequestClose={() => setQrModalVisible(false)}
        >
          <View style={styles.modalOverlay}>
            <View style={styles.modalContent}>
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>Wi-Fi QR Code</Text>
                <TouchableOpacity
                  onPress={() => setQrModalVisible(false)}
                  style={styles.closeButton}
                >
                  <Ionicons name="close" size={24} color="#888" />
                </TouchableOpacity>
              </View>

              <Text style={styles.qrSubtitle}>
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
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>Logout</Text>
                <TouchableOpacity
                  onPress={() => setLogoutModalVisible(false)}
                  style={styles.closeButton}
                >
                  <Ionicons name="close" size={24} color="#888" />
                </TouchableOpacity>
              </View>

              <Text style={styles.logoutText}>
                Are you sure you want to log out?
              </Text>

              <View style={styles.buttonRow}>
                <TouchableOpacity
                  style={[styles.actionButton, styles.cancelButton]}
                  onPress={() => setLogoutModalVisible(false)}
                >
                  <Text style={styles.cancelButtonText}>Cancel</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.actionButton, styles.logoutConfirmButton]}
                  onPress={handleLogout}
                >
                  <Text style={styles.logoutConfirmButtonText}>Logout</Text>
                </TouchableOpacity>
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
    </>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0A0A0A",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 24,
    paddingTop: 60,
    paddingBottom: 20,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(29, 233, 182, 0.1)",
  },
  headerTitle: {
    fontSize: 32,
    fontWeight: "bold",
    color: "#FFFFFF",
  },
  logoutButton: {
    padding: 8,
    borderRadius: 12,
    backgroundColor: "rgba(29, 233, 182, 0.1)",
  },
  scrollContent: {
    padding: 24,
  },
  profileSection: {
    alignItems: "center",
    marginBottom: 32,
  },
  profileImageContainer: {
    position: "relative",
    marginBottom: 16,
  },
  profileImage: {
    width: 120,
    height: 120,
    borderRadius: 60,
    borderWidth: 3,
    borderColor: "#1DE9B6",
  },
  placeholderImage: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: "#1A1A1A",
    borderWidth: 3,
    borderColor: "#1DE9B6",
    justifyContent: "center",
    alignItems: "center",
  },
  profileImageOverlay: {
    position: "absolute",
    bottom: 0,
    right: 0,
    backgroundColor: "#0A0A0A",
    borderRadius: 20,
    padding: 8,
    borderWidth: 2,
    borderColor: "#1DE9B6",
  },
  cameraButton: {
    width: 30,
    height: 30,
    borderRadius: 20,
    backgroundColor: "rgba(29, 233, 182, 0.1)",
    justifyContent: "center",
    alignItems: "center",
  },
  profileText: {
    fontSize: 16,
    color: "#888",
    textAlign: "center",
  },
  section: {
    marginBottom: 32,
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: "600",
    color: "#FFFFFF",
    marginLeft: 12,
    flex: 1,
  },
  compactSaveButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: "#1DE9B6",
    borderRadius: 8,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  compactSaveButtonText: {
    color: "#0A0A0A",
    fontSize: 14,
    fontWeight: "600",
  },
  saveButtonDisabled: {
    backgroundColor: "#333",
    opacity: 0.6,
  },
  inputContainer: {
    marginBottom: 16,
  },
  inputWrapper: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#1A1A1A",
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 6,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  input: {
    flex: 1,
    color: "#FFFFFF",
    fontSize: 16,
    marginLeft: 12,
  },
  eyeButton: {
    padding: 4,
    marginLeft: 8,
  },
  buttonRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 12,
  },
  actionButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 12,
    gap: 8,
  },
  qrButton: {
    backgroundColor: "rgba(29, 233, 182, 0.1)",
    borderWidth: 1,
    borderColor: "#1DE9B6",
    flex: 1,
  },
  qrButtonDisabled: {
    backgroundColor: "#333",
    borderColor: "#555",
    opacity: 0.6,
  },
  qrButtonText: {
    color: "#1DE9B6",
    fontSize: 16,
    fontWeight: "600",
  },
  saveButton: {
    backgroundColor: "#1DE9B6",
  },
  saveButtonText: {
    color: "#0A0A0A",
    fontSize: 16,
    fontWeight: "600",
  },
  addDeviceButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "rgba(29, 233, 182, 0.1)",
    justifyContent: "center",
    alignItems: "center",
  },
  emptyState: {
    alignItems: "center",
    paddingVertical: 40,
  },
  emptyStateText: {
    fontSize: 18,
    color: "#FFFFFF",
    marginTop: 16,
    marginBottom: 8,
  },
  emptyStateSubtext: {
    fontSize: 14,
    color: "#888",
    textAlign: "center",
  },
  devicesList: {
    gap: 12,
  },
  deviceCard: {
    backgroundColor: "#1A1A1A",
    borderRadius: 16,
    padding: 16,
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  deviceIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: "rgba(29, 233, 182, 0.1)",
    justifyContent: "center",
    alignItems: "center",
    marginRight: 16,
  },
  deviceInfo: {
    flex: 1,
  },
  deviceName: {
    fontSize: 18,
    fontWeight: "600",
    color: "#FFFFFF",
    marginBottom: 4,
  },
  deviceLocation: {
    fontSize: 14,
    color: "#888",
  },
  deviceActions: {
    alignItems: "flex-end",
  },
  deviceStatus: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#1DE9B6",
    marginRight: 6,
  },
  statusText: {
    fontSize: 12,
    color: "#1DE9B6",
    fontWeight: "500",
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.8)",
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 20,
  },
  modalContent: {
    backgroundColor: "#1A1A1A",
    borderRadius: 20,
    padding: 24,
    width: "100%",
    maxWidth: 400,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
    // alignItems: "center",
  },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 20,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: "600",
    color: "#FFFFFF",
  },
  closeButton: {
    padding: 4,
  },
  modalInputContainer: {
    marginBottom: 20,
  },
  modalButtonRow: {
    flexDirection: "row",
    gap: 12,
  },
  removeButton: {
    backgroundColor: "#FF5252",
    flex: 1,
  },
  removeButtonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "600",
  },
  qrSubtitle: {
    fontSize: 14,
    color: "#888",
    textAlign: "center",
    marginBottom: 24,
    lineHeight: 20,
  },
  qrCodeContainer: {
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    marginBottom: 16,
    marginLeft: "010%",
    height: 260,
    width: 260,
  },
  logoutText: {
    fontSize: 16,
    color: "#888",
    textAlign: "center",
    marginBottom: 24,
    lineHeight: 22,
  },
  cancelButton: {
    backgroundColor: "rgba(255, 255, 255, 0.1)",
    flex: 1,
  },
  cancelButtonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "600",
  },
  logoutConfirmButton: {
    backgroundColor: "#FF5252",
    flex: 1,
  },
  logoutConfirmButtonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "600",
  },
  confirmationText: {
    fontSize: 16,
    color: "#FFFFFF",
    textAlign: "center",
    marginBottom: 8,
    lineHeight: 22,
  },
  confirmationSubtext: {
    fontSize: 14,
    color: "#888",
    textAlign: "center",
    marginBottom: 24,
    lineHeight: 20,
  },
});
export default SettingsScreen;
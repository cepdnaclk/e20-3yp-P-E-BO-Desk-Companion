import React, { useState, useEffect, useRef } from "react";
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
  Animated,
  SafeAreaView,
  FlatList,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import { MaterialIcons, Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import { LinearGradient } from "expo-linear-gradient";
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
  const [deviceSelectionModalVisible, setDeviceSelectionModalVisible] =
    useState(false);
  const [editPeboModalVisible, setEditPeboModalVisible] = useState(false);
  const [selectedPebo, setSelectedPebo] = useState(null);
  const [selectedDeviceForQR, setSelectedDeviceForQR] = useState(null);
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

  // Animation refs for futuristic effects
  const pulse = useRef(new Animated.Value(0)).current;
  const glow = useRef(new Animated.Value(0)).current;

  const BUCKET_NAME = "pebo-user-images";
  const API_GATEWAY_URL =
    "https://aw8yn9cbj1.execute-api.us-east-1.amazonaws.com/prod/presigned";

  // Futuristic animations
  useEffect(() => {
    // Pulsing animation for interactive elements
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1,
          duration: 2000,
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 0,
          duration: 2000,
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

  const showPopup = (title, message, icon = "checkmark-circle") => {
    setPopupContent({ title, message, icon });
    setPopupVisible(true);
  };

  // Check if WiFi settings have changed
  const hasWifiChanged = () => {
    return (
      wifiSSID.trim() !== originalWifiSSID.trim() ||
      wifiPassword.trim() !== originalWifiPassword.trim()
    );
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

    if (peboDevices.length === 0) {
      showPopup(
        "Error",
        "No PEBO devices found. Please add a device first.",
        "alert-circle"
      );
      return;
    }

    setDeviceSelectionModalVisible(true);
  };

  const handleDeviceSelection = (device) => {
    setSelectedDeviceForQR(device);
    setDeviceSelectionModalVisible(false);
    setQrModalVisible(true);
  };

  const generateQrCodeValue = () => {
    if (!selectedDeviceForQR) return "";

    const credentials = {
      ssid: wifiSSID.trim(),
      password: wifiPassword.trim(),
      deviceId: selectedDeviceForQR.id,
      userId: auth.currentUser?.uid || "",
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

  const renderDeviceItem = ({ item }) => (
    <Animated.View
      style={[
        styles.deviceSelectionCard,
        {
          shadowOpacity: pulse.interpolate({
            inputRange: [0, 1],
            outputRange: [0.1, 0.3],
          }),
        },
      ]}
    >
      <Pressable
        style={styles.deviceSelectionCardInner}
        onPress={() => handleDeviceSelection(item)}
      >
        <View style={styles.deviceIcon}>
          <Ionicons name="hardware-chip" size={24} color="#1DE9B6" />
        </View>
        <View style={styles.deviceInfo}>
          <Text style={styles.deviceName}>{item.name}</Text>
          <Text style={styles.deviceLocation}>{item.location}</Text>
        </View>
        <Ionicons name="chevron-forward" size={20} color="#1DE9B6" />
      </Pressable>
    </Animated.View>
  );

  return (
    <>
      <StatusBar barStyle="light-content" backgroundColor="#000000" />
      <SafeAreaView style={styles.container}>
        {/* Futuristic Background Effects */}
        <View style={styles.backgroundContainer}>
          <Animated.View
            style={[
              styles.backgroundOrb1,
              {
                opacity: glow.interpolate({
                  inputRange: [0, 1],
                  outputRange: [0.1, 0.3],
                }),
              },
            ]}
          />
          <Animated.View
            style={[
              styles.backgroundOrb2,
              {
                opacity: pulse.interpolate({
                  inputRange: [0, 1],
                  outputRange: [0.05, 0.2],
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
          <View style={styles.headerContent}>
            <Text style={styles.headerTitle}>SETTINGS</Text>
            <Text style={styles.headerSubtitle}>
              System Configuration Center
            </Text>
          </View>
          <Animated.View
            style={[
              styles.logoutButton,
              {
                shadowOpacity: glow.interpolate({
                  inputRange: [0, 1],
                  outputRange: [0.3, 0.8],
                }),
              },
            ]}
          >
            <TouchableOpacity
              style={styles.logoutButtonInner}
              onPress={() => setLogoutModalVisible(true)}
            >
              <Ionicons name="log-out-outline" size={24} color="#1DE9B6" />
            </TouchableOpacity>
          </Animated.View>
        </LinearGradient>

        <ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.scrollContent}
        >
          {/* Profile Section */}
          <View style={styles.profileSection}>
            <Animated.View
              style={[
                styles.profileImageContainer,
                {
                  shadowOpacity: pulse.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0.3, 0.8],
                  }),
                },
              ]}
            >
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
            </Animated.View>
            <Text style={styles.profileText}>PROFILE PHOTO</Text>
          </View>

          {/* Wi-Fi Configuration */}
          <View style={styles.section}>
            <LinearGradient
              colors={["rgba(26, 26, 26, 0.8)", "rgba(26, 26, 26, 0.4)"]}
              style={styles.sectionContainer}
            >
              <View style={styles.sectionHeader}>
                <Ionicons name="wifi" size={24} color="#1DE9B6" />
                <Text style={styles.sectionTitle}>WI-FI CONFIGURATION</Text>
                {hasWifiChanged() && (
                  <Animated.View
                    style={[
                      styles.compactSaveButton,
                      {
                        shadowOpacity: glow.interpolate({
                          inputRange: [0, 1],
                          outputRange: [0.3, 0.8],
                        }),
                      },
                    ]}
                  >
                    <Pressable
                      style={[
                        styles.compactSaveButtonInner,
                        isSavingWifi && styles.saveButtonDisabled,
                      ]}
                      onPress={handleSaveWifi}
                      disabled={isSavingWifi}
                    >
                      {isSavingWifi ? (
                        <ActivityIndicator color="#000000" size="small" />
                      ) : (
                        <>
                          <Ionicons
                            name="save-outline"
                            size={18}
                            color="#000000"
                          />
                          <Text style={styles.compactSaveButtonText}>SAVE</Text>
                        </>
                      )}
                    </Pressable>
                  </Animated.View>
                )}
              </View>

              <View style={styles.inputContainer}>
                <View style={styles.inputWrapper}>
                  <Ionicons name="wifi-outline" size={20} color="#1DE9B6" />
                  <TextInput
                    placeholder="Network SSID"
                    style={styles.input}
                    value={wifiSSID}
                    onChangeText={setWifiSSID}
                    placeholderTextColor="#888"
                  />
                </View>
                <View style={styles.inputWrapper}>
                  <Ionicons
                    name="lock-closed-outline"
                    size={20}
                    color="#1DE9B6"
                  />
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
                      color="#1DE9B6"
                    />
                  </Pressable>
                </View>
              </View>

              <View style={styles.buttonRow}>
                <Pressable
                  style={[
                    styles.actionButton,
                    styles.qrButton,
                    (!wifiSSID.trim() ||
                      !wifiPassword.trim() ||
                      peboDevices.length === 0) &&
                      styles.qrButtonDisabled,
                  ]}
                  onPress={handleShowQrCode}
                  disabled={
                    !wifiSSID.trim() ||
                    !wifiPassword.trim() ||
                    peboDevices.length === 0
                  }
                >
                  <Ionicons name="qr-code-outline" size={20} color="#1DE9B6" />
                  <Text style={styles.qrButtonText}>QR CODE</Text>
                </Pressable>
              </View>
            </LinearGradient>
          </View>

          {/* PEBO Devices */}
          <View style={styles.section}>
            <LinearGradient
              colors={["rgba(26, 26, 26, 0.8)", "rgba(26, 26, 26, 0.4)"]}
              style={styles.sectionContainer}
            >
              <View style={styles.sectionHeader}>
                <Ionicons
                  name="hardware-chip-outline"
                  size={24}
                  color="#1DE9B6"
                />
                <Text style={styles.sectionTitle}>PEBO DEVICES</Text>
                <Animated.View
                  style={[
                    styles.addDeviceButton,
                    {
                      shadowOpacity: pulse.interpolate({
                        inputRange: [0, 1],
                        outputRange: [0.3, 0.8],
                      }),
                    },
                  ]}
                >
                  <TouchableOpacity
                    style={styles.addDeviceButtonInner}
                    onPress={() => setModalVisible(true)}
                  >
                    <Ionicons name="add" size={20} color="#1DE9B6" />
                  </TouchableOpacity>
                </Animated.View>
              </View>

              {peboDevices.length === 0 ? (
                <View style={styles.emptyState}>
                  <Ionicons
                    name="hardware-chip-outline"
                    size={48}
                    color="#555"
                  />
                  <Text style={styles.emptyStateText}>
                    NO PEBO DEVICES FOUND
                  </Text>
                  <Text style={styles.emptyStateSubtext}>
                    Add your first device to get started
                  </Text>
                </View>
              ) : (
                <View style={styles.devicesList}>
                  {peboDevices.map((pebo, index) => (
                    <Animated.View
                      key={pebo.id}
                      style={[
                        styles.deviceCard,
                        {
                          shadowOpacity: pulse.interpolate({
                            inputRange: [0, 1],
                            outputRange: [0.1, 0.3],
                          }),
                        },
                      ]}
                    >
                      <Pressable
                        style={styles.deviceCardInner}
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
                          <Text style={styles.deviceLocation}>
                            {pebo.location}
                          </Text>
                        </View>
                        <View style={styles.deviceActions}>
                          <View style={styles.deviceStatus}>
                            <Animated.View
                              style={[
                                styles.statusDot,
                                {
                                  opacity: pulse.interpolate({
                                    inputRange: [0, 1],
                                    outputRange: [0.7, 1],
                                  }),
                                },
                              ]}
                            />
                            <Text style={styles.statusText}>ONLINE</Text>
                          </View>
                          <Ionicons
                            name="chevron-forward"
                            size={20}
                            color="#888"
                          />
                        </View>
                      </Pressable>
                    </Animated.View>
                  ))}
                </View>
              )}
            </LinearGradient>
          </View>
        </ScrollView>

        {/* Device Selection Modal */}
        <Modal
          transparent
          visible={deviceSelectionModalVisible}
          animationType="fade"
          onRequestClose={() => setDeviceSelectionModalVisible(false)}
        >
          <View style={styles.modalOverlay}>
            <LinearGradient
              colors={["rgba(26, 26, 26, 0.95)", "rgba(26, 26, 26, 0.8)"]}
              style={styles.modalContent}
            >
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>SELECT PEBO DEVICE</Text>
                <TouchableOpacity
                  onPress={() => setDeviceSelectionModalVisible(false)}
                  style={styles.closeButton}
                >
                  <Ionicons name="close" size={24} color="#888" />
                </TouchableOpacity>
              </View>

              <Text style={styles.deviceSelectionSubtitle}>
                Choose which PEBO device to generate QR code for:
              </Text>

              <FlatList
                data={peboDevices}
                renderItem={renderDeviceItem}
                keyExtractor={(item) => item.id}
                style={styles.deviceSelectionList}
                showsVerticalScrollIndicator={false}
              />
            </LinearGradient>
          </View>
        </Modal>

        {/* Add PEBO Modal */}
        <Modal
          transparent
          visible={modalVisible}
          animationType="fade"
          onRequestClose={() => setModalVisible(false)}
        >
          <View style={styles.modalOverlay}>
            <LinearGradient
              colors={["rgba(26, 26, 26, 0.95)", "rgba(26, 26, 26, 0.8)"]}
              style={styles.modalContent}
            >
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>ADD NEW PEBO</Text>
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
                    color="#1DE9B6"
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
                  <Ionicons name="location-outline" size={20} color="#1DE9B6" />
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
                <LinearGradient
                  colors={["#1DE9B6", "#00BFA5"]}
                  style={styles.saveButtonGradient}
                >
                  <Ionicons name="add" size={20} color="#000000" />
                  <Text style={styles.saveButtonText}>ADD DEVICE</Text>
                </LinearGradient>
              </TouchableOpacity>
            </LinearGradient>
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
            <LinearGradient
              colors={["rgba(26, 26, 26, 0.95)", "rgba(26, 26, 26, 0.8)"]}
              style={styles.modalContent}
            >
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>EDIT PEBO DEVICE</Text>
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
                    color="#1DE9B6"
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
                  <Ionicons name="location-outline" size={20} color="#1DE9B6" />
                  <TextInput
                    placeholder="Location (e.g., Kitchen)"
                    value={editPeboLocation}
                    onChangeText={setEditPeboLocation}
                    style={styles.input}
                    placeholderTextColor="#888"
                  />
                </View>
              </View>

              <View style={styles.modalButtonRow}>
                <TouchableOpacity
                  style={[styles.actionButton, styles.removeButton]}
                  onPress={handleRemovePebo}
                  disabled={isRemovingPebo}
                >
                  <LinearGradient
                    colors={["#FF5252", "#F44336"]}
                    style={styles.removeButtonGradient}
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
                        <Text style={styles.removeButtonText}>REMOVE</Text>
                      </>
                    )}
                  </LinearGradient>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.actionButton, styles.saveButton]}
                  onPress={handleUpdatePebo}
                  disabled={isUpdatingPebo}
                >
                  <LinearGradient
                    colors={["#1DE9B6", "#00BFA5"]}
                    style={styles.saveButtonGradient}
                  >
                    {isUpdatingPebo ? (
                      <ActivityIndicator color="#000000" size="small" />
                    ) : (
                      <>
                        <Ionicons
                          name="save-outline"
                          size={20}
                          color="#000000"
                        />
                        <Text style={styles.saveButtonText}>UPDATE</Text>
                      </>
                    )}
                  </LinearGradient>
                </TouchableOpacity>
              </View>
            </LinearGradient>
          </View>
        </Modal>

        {/* Remove PEBO Confirmation Modal */}
        <Modal
          transparent
          visible={removeModalVisible}
          animationType="fade"
          onRequestClose={() => setRemoveModalVisible(false)}
        >
          <View style={styles.modalOverlay}>
            <LinearGradient
              colors={["rgba(26, 26, 26, 0.95)", "rgba(26, 26, 26, 0.8)"]}
              style={styles.modalContent}
            >
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>REMOVE PEBO</Text>
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
                  <Text style={styles.cancelButtonText}>CANCEL</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.actionButton, styles.removeButton]}
                  onPress={confirmRemovePebo}
                  disabled={isRemovingPebo}
                >
                  <LinearGradient
                    colors={["#FF5252", "#F44336"]}
                    style={styles.removeButtonGradient}
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
                        <Text style={styles.removeButtonText}>REMOVE</Text>
                      </>
                    )}
                  </LinearGradient>
                </TouchableOpacity>
              </View>
            </LinearGradient>
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
            <LinearGradient
              colors={["rgba(26, 26, 26, 0.95)", "rgba(26, 26, 26, 0.8)"]}
              style={styles.modalContent}
            >
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>HOW PEBO SHOULD CALL YOU!</Text>
                <TouchableOpacity
                  onPress={() => setUsernameModalVisible(false)}
                  style={styles.closeButton}
                >
                  <Ionicons name="close" size={24} color="#888" />
                </TouchableOpacity>
              </View>

              <View style={styles.modalInputContainer}>
                <View style={styles.inputWrapper}>
                  <Ionicons name="person-outline" size={20} color="#1DE9B6" />
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
                <LinearGradient
                  colors={["#1DE9B6", "#00BFA5"]}
                  style={styles.saveButtonGradient}
                >
                  <Ionicons name="camera" size={20} color="#000000" />
                  <Text style={styles.saveButtonText}>CAPTURE & SAVE</Text>
                </LinearGradient>
              </TouchableOpacity>
            </LinearGradient>
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
            <LinearGradient
              colors={["rgba(26, 26, 26, 0.95)", "rgba(26, 26, 26, 0.8)"]}
              style={styles.modalContent}
            >
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>WI-FI QR CODE</Text>
                <TouchableOpacity
                  onPress={() => setQrModalVisible(false)}
                  style={styles.closeButton}
                >
                  <Ionicons name="close" size={24} color="#888" />
                </TouchableOpacity>
              </View>

              {selectedDeviceForQR && (
                <View style={styles.selectedDeviceInfo}>
                  <Text style={styles.selectedDeviceTitle}>
                    Selected Device:
                  </Text>
                  <Text style={styles.selectedDeviceName}>
                    {selectedDeviceForQR.name}
                  </Text>
                  <Text style={styles.selectedDeviceLocation}>
                    {selectedDeviceForQR.location}
                  </Text>
                </View>
              )}

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
            </LinearGradient>
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
            <LinearGradient
              colors={["rgba(26, 26, 26, 0.95)", "rgba(26, 26, 26, 0.8)"]}
              style={styles.modalContent}
            >
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>LOGOUT</Text>
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
                  <Text style={styles.cancelButtonText}>CANCEL</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.actionButton, styles.logoutConfirmButton]}
                  onPress={handleLogout}
                >
                  <LinearGradient
                    colors={["#FF5252", "#F44336"]}
                    style={styles.logoutConfirmButtonGradient}
                  >
                    <Text style={styles.logoutConfirmButtonText}>LOGOUT</Text>
                  </LinearGradient>
                </TouchableOpacity>
              </View>
            </LinearGradient>
          </View>
        </Modal>

        <PopupModal
          visible={popupVisible}
          onClose={() => setPopupVisible(false)}
          title={popupContent.title}
          message={popupContent.message}
          icon={popupContent.icon}
        />
      </SafeAreaView>
    </>
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
  backgroundOrb1: {
    position: "absolute",
    top: 100,
    left: 50,
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: "rgba(29, 233, 182, 0.1)",
  },
  backgroundOrb2: {
    position: "absolute",
    top: 300,
    right: 30,
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: "rgba(255, 82, 82, 0.1)",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 24,
    paddingTop: 60,
    paddingBottom: 20,
    zIndex: 1,
  },
  headerContent: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 32,
    fontWeight: "900",
    color: "#FFFFFF",
    letterSpacing: 2,
    textShadowColor: "#1DE9B6",
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 10,
  },
  headerSubtitle: {
    fontSize: 12,
    color: "#1DE9B6",
    marginTop: 4,
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  logoutButton: {
    shadowColor: "#1DE9B6",
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 10,
  },
  logoutButtonInner: {
    padding: 12,
    borderRadius: 12,
    backgroundColor: "rgba(29, 233, 182, 0.1)",
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  scrollContent: {
    padding: 24,
    zIndex: 1,
  },
  profileSection: {
    alignItems: "center",
    marginBottom: 32,
  },
  profileImageContainer: {
    position: "relative",
    marginBottom: 16,
    shadowColor: "#1DE9B6",
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 20,
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
    backgroundColor: "rgba(26, 26, 26, 0.8)",
    borderWidth: 3,
    borderColor: "#1DE9B6",
    justifyContent: "center",
    alignItems: "center",
  },
  profileImageOverlay: {
    position: "absolute",
    bottom: 0,
    right: 0,
    backgroundColor: "#000000",
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
    fontSize: 14,
    color: "#888",
    textAlign: "center",
    fontWeight: "600",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  section: {
    marginBottom: 32,
  },
  sectionContainer: {
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#FFFFFF",
    marginLeft: 12,
    flex: 1,
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  compactSaveButton: {
    shadowColor: "#1DE9B6",
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 10,
  },
  compactSaveButtonInner: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: "#1DE9B6",
    borderRadius: 8,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  compactSaveButtonText: {
    color: "#000000",
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
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
    backgroundColor: "rgba(0, 0, 0, 0.5)",
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  input: {
    flex: 1,
    color: "#FFFFFF",
    fontSize: 16,
    marginLeft: 12,
    fontWeight: "500",
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
    overflow: "hidden",
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
    fontSize: 14,
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  saveButton: {
    backgroundColor: "transparent",
  },
  saveButtonGradient: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 12,
    gap: 8,
  },
  saveButtonText: {
    color: "#000000",
    fontSize: 14,
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  addDeviceButton: {
    shadowColor: "#1DE9B6",
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 10,
  },
  addDeviceButtonInner: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "rgba(29, 233, 182, 0.1)",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  emptyState: {
    alignItems: "center",
    paddingVertical: 40,
  },
  emptyStateText: {
    fontSize: 16,
    color: "#FFFFFF",
    marginTop: 16,
    marginBottom: 8,
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  emptyStateSubtext: {
    fontSize: 14,
    color: "#888",
    textAlign: "center",
    fontWeight: "500",
  },
  devicesList: {
    gap: 12,
  },
  deviceCard: {
    borderRadius: 16,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
    shadowColor: "#1DE9B6",
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 10,
  },
  deviceCardInner: {
    backgroundColor: "rgba(26, 26, 26, 0.8)",
    padding: 16,
    flexDirection: "row",
    alignItems: "center",
  },
  deviceIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: "rgba(29, 233, 182, 0.1)",
    justifyContent: "center",
    alignItems: "center",
    marginRight: 16,
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
    marginBottom: 4,
    letterSpacing: 0.5,
  },
  deviceLocation: {
    fontSize: 12,
    color: "#888",
    textTransform: "uppercase",
    letterSpacing: 0.5,
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
    fontSize: 10,
    color: "#1DE9B6",
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.9)",
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 20,
  },
  modalContent: {
    borderRadius: 20,
    padding: 24,
    width: "100%",
    maxWidth: 400,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 20,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#FFFFFF",
    letterSpacing: 1,
    textTransform: "uppercase",
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
    backgroundColor: "transparent",
    flex: 1,
  },
  removeButtonGradient: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 12,
    gap: 8,
  },
  removeButtonText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  qrSubtitle: {
    fontSize: 14,
    color: "#888",
    textAlign: "center",
    marginBottom: 24,
    lineHeight: 20,
    fontWeight: "500",
  },
  qrCodeContainer: {
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    marginBottom: 16,
    alignSelf: "center",
    height: 260,
    width: 260,
  },
  logoutText: {
    fontSize: 16,
    color: "#888",
    textAlign: "center",
    marginBottom: 24,
    lineHeight: 22,
    fontWeight: "500",
  },
  buttonRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 12,
  },

  cancelButton: {
    backgroundColor: "rgba(255, 255, 255, 0.1)",
    flex: 1, // Equal width with other buttons
    paddingHorizontal: 20, // Match other button padding
    paddingVertical: 12,
    borderRadius: 12,
    maxHeight: 48,
    alignItems: "center",
    justifyContent: "center",
  },

  cancelButtonText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
  },

  cancelButtonText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  logoutConfirmButton: {
    backgroundColor: "transparent",
    flex: 1,
  },
  logoutConfirmButtonGradient: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 12,
    gap: 8,
  },
  logoutConfirmButtonText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  confirmationText: {
    fontSize: 16,
    color: "#FFFFFF",
    textAlign: "center",
    marginBottom: 8,
    lineHeight: 22,
    fontWeight: "500",
  },
  confirmationSubtext: {
    fontSize: 14,
    color: "#888",
    textAlign: "center",
    marginBottom: 24,
    lineHeight: 20,
    fontWeight: "500",
  },
  // Device Selection Modal Styles
  deviceSelectionSubtitle: {
    fontSize: 14,
    color: "#888",
    textAlign: "center",
    marginBottom: 20,
    lineHeight: 20,
    fontWeight: "500",
  },
  deviceSelectionList: {
    maxHeight: 300,
  },
  deviceSelectionCard: {
    borderRadius: 12,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
    marginBottom: 12,
    shadowColor: "#1DE9B6",
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 10,
  },
  deviceSelectionCardInner: {
    backgroundColor: "rgba(0, 0, 0, 0.5)",
    padding: 16,
    flexDirection: "row",
    alignItems: "center",
  },
  selectedDeviceInfo: {
    backgroundColor: "rgba(29, 233, 182, 0.1)",
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: "rgba(29, 233, 182, 0.2)",
  },
  selectedDeviceTitle: {
    fontSize: 12,
    color: "#1DE9B6",
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
    marginBottom: 8,
  },
  selectedDeviceName: {
    fontSize: 16,
    color: "#FFFFFF",
    fontWeight: "600",
    marginBottom: 4,
  },
  selectedDeviceLocation: {
    fontSize: 12,
    color: "#888",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
});

export default SettingsScreen;

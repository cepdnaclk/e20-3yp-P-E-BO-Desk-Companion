<<<<<<< Updated upstream
<<<<<<< Updated upstream
import React, { useState, useEffect } from "react";
=======
import React, { useState, useEffect, memo } from "react";
>>>>>>> Stashed changes
=======
import React, { useState, useEffect, memo } from "react";
>>>>>>> Stashed changes
import {
  ScrollView,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  TextInput,
  ActivityIndicator,
  Image,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import { MaterialIcons, Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
<<<<<<< Updated upstream
import QRCode from "react-native-qrcode-svg"; // Added for QR code generation
=======
import QRCode from "react-native-qrcode-svg";
import { Picker } from "@react-native-picker/picker";
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
import {
  auth,
  db,
  getWifiName,
  saveWifiSettings,
  addPeboDevice,
  getPeboDevices,
  getUserName,
  getUserName,
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
  const [selectedDeviceId, setSelectedDeviceId] = useState(null);
  const [selectedDeviceId, setSelectedDeviceId] = useState(null);
  const [userImage, setUserImage] = useState(null);
  const [imageCacheBuster, setImageCacheBuster] = useState(Date.now());
  const [imageCacheBuster, setImageCacheBuster] = useState(Date.now());
  const [isProcessing, setIsProcessing] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [logoutModalVisible, setLogoutModalVisible] = useState(false);
<<<<<<< Updated upstream
  const [qrModalVisible, setQrModalVisible] = useState(false); // Added for QR code modal
=======
  const [qrModalVisible, setQrModalVisible] = useState(false);
  const [deviceSelectModalVisible, setDeviceSelectModalVisible] = useState(false);
  const [usernameModalVisible, setUsernameModalVisible] = useState(false);
  const [tempUsername, setTempUsername] = useState("");
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
  const [popupVisible, setPopupVisible] = useState(false);
  const [popupContent, setPopupContent] = useState({
    title: "",
    message: "",
    icon: "checkmark-circle",
    icon: "checkmark-circle",
  });
  const [username, setUsername] = useState("");
  const [currentUser, setCurrentUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const BUCKET_NAME = "pebo-user-images";
  const API_GATEWAY_URL =
    "https://aw8yn9cbj1.execute-api.us-east-1.amazonaws.com/prod/presigned";

  const showPopup = (title, message, icon = "checkmark-circle") => {
    setPopupContent({ title, message, icon });
    setPopupContent({ title, message, icon });
    setPopupVisible(true);
  };

  useEffect(() => {
    let unsubscribeAuth;
    unsubscribeAuth = auth.onAuthStateChanged((user) => {
      console.log("Auth state changed:", user ? user.uid : null);
      setCurrentUser(user);
      setIsLoading(false);
    });

    let unsubscribeAuth;
    unsubscribeAuth = auth.onAuthStateChanged((user) => {
      console.log("Auth state changed:", user ? user.uid : null);
      setCurrentUser(user);
      setIsLoading(false);
    });

    const fetchPeboDevices = async () => {
      try {
        const devices = await getPeboDevices();
        console.log("Fetched PEBO devices:", devices);
        console.log("Fetched PEBO devices:", devices);
        setPeboDevices(devices);
        if (devices.length > 0) {
          setSelectedDeviceId(devices[0].id);
        }
        if (devices.length > 0) {
          setSelectedDeviceId(devices[0].id);
        }
      } catch (err) {
        console.warn("Error fetching PEBOs:", err);
        showPopup("Error", "Failed to fetch devices", "alert-circle");
        showPopup("Error", "Failed to fetch devices", "alert-circle");
      }
    };

    const fetchWifiSettings = async () => {
      try {
        const { wifiSSID, wifiPassword } = await getWifiName();
<<<<<<< Updated upstream
<<<<<<< Updated upstream
        setWifiSSID(wifiSSID);
        setWifiPassword(wifiPassword);
=======
=======
>>>>>>> Stashed changes
        console.log("Fetched Wi-Fi settings:", { wifiSSID, wifiPassword });
        setWifiSSID(wifiSSID || "");
        setWifiPassword(wifiPassword || "");
>>>>>>> Stashed changes
      } catch (err) {
        console.warn("Error fetching Wi-Fi:", err);
        showPopup("Error", "Failed to fetch Wi-Fi settings", "alert-circle");
        showPopup("Error", "Failed to fetch Wi-Fi settings", "alert-circle");
      }
    };

<<<<<<< Updated upstream
<<<<<<< Updated upstream
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
            showPopup("Error", "Failed to fetch profile image", "alert-circle");
          }
        },
        (error) => {
          console.error("Firebase listener error:", error);
          setUserImage(null);
          showPopup("Error", "Failed to fetch profile image", "alert-circle");
        }
      );
    } else {
      console.warn("No userId available, skipping profile image listener");
      setUserImage(null);
    }

=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    fetchPeboDevices();
    fetchWifiSettings();

    return () => {
      if (unsubscribeAuth) unsubscribeAuth();
    };
  }, []);

<<<<<<< Updated upstream
<<<<<<< Updated upstream
  const captureAndUploadImage = async () => {
    if (!username.trim()) {
      showPopup("Error", "How PEBO Should call you? ", "alert-circle");
=======
  useEffect(() => {
    let unsubscribeProfile;
    let unsubscribeUsername;
    if (currentUser?.uid) {
      const profileImageRef = db.ref(`users/${currentUser.uid}/profileImage`);
      unsubscribeProfile = profileImageRef.on(
        "value",
        (snapshot) => {
          try {
            const imageUrl = snapshot?.exists() ? snapshot.val() : null;
            if (imageUrl !== userImage) {
              console.log("Firebase profileImage:", imageUrl);
              setUserImage(imageUrl);
            }
          } catch (error) {
            console.error("Error processing Firebase snapshot:", error);
            setUserImage(null);
            showPopup("Error", "Failed to fetch profile image", "alert-circle");
          }
        },
        (error) => {
          console.error("Firebase listener error:", error);
          setUserImage(null);
          showPopup("Error", "Failed to fetch profile image", "alert-circle");
        }
      );

      const usernameRef = db.ref(`users/${currentUser.uid}/username`);
      unsubscribeUsername = usernameRef.on(
        "value",
        (snapshot) => {
          try {
            const fetchedUsername = snapshot?.exists() ? snapshot.val() : null;
            console.log("Firebase username:", fetchedUsername);
            setUsername(
              fetchedUsername || `user_${currentUser.uid.slice(0, 8)}`
            );
          } catch (error) {
            console.error("Error fetching username:", error);
            setUsername(`user_${currentUser.uid.slice(0, 8)}`);
            showPopup("Error", "Failed to fetch username", "alert-circle");
          }
        },
        (error) => {
          console.error("Firebase username listener error:", error);
          setUsername(`user_${currentUser.uid.slice(0, 8)}`);
          showPopup("Error", "Failed to fetch username", "alert-circle");
        }
      );
    }
    return () => {
      if (unsubscribeProfile) unsubscribeProfile();
      if (unsubscribeUsername) unsubscribeUsername();
    };
  }, [currentUser]);

  const captureAndUploadImage = async () => {
=======
  useEffect(() => {
    let unsubscribeProfile;
    let unsubscribeUsername;
    if (currentUser?.uid) {
      const profileImageRef = db.ref(`users/${currentUser.uid}/profileImage`);
      unsubscribeProfile = profileImageRef.on(
        "value",
        (snapshot) => {
          try {
            const imageUrl = snapshot?.exists() ? snapshot.val() : null;
            if (imageUrl !== userImage) {
              console.log("Firebase profileImage:", imageUrl);
              setUserImage(imageUrl);
            }
          } catch (error) {
            console.error("Error processing Firebase snapshot:", error);
            setUserImage(null);
            showPopup("Error", "Failed to fetch profile image", "alert-circle");
          }
        },
        (error) => {
          console.error("Firebase listener error:", error);
          setUserImage(null);
          showPopup("Error", "Failed to fetch profile image", "alert-circle");
        }
      );

      const usernameRef = db.ref(`users/${currentUser.uid}/username`);
      unsubscribeUsername = usernameRef.on(
        "value",
        (snapshot) => {
          try {
            const fetchedUsername = snapshot?.exists() ? snapshot.val() : null;
            console.log("Firebase username:", fetchedUsername);
            setUsername(
              fetchedUsername || `user_${currentUser.uid.slice(0, 8)}`
            );
          } catch (error) {
            console.error("Error fetching username:", error);
            setUsername(`user_${currentUser.uid.slice(0, 8)}`);
            showPopup("Error", "Failed to fetch username", "alert-circle");
          }
        },
        (error) => {
          console.error("Firebase username listener error:", error);
          setUsername(`user_${currentUser.uid.slice(0, 8)}`);
          showPopup("Error", "Failed to fetch username", "alert-circle");
        }
      );
    }
    return () => {
      if (unsubscribeProfile) unsubscribeProfile();
      if (unsubscribeUsername) unsubscribeUsername();
    };
  }, [currentUser]);

  const captureAndUploadImage = async () => {
>>>>>>> Stashed changes
    // Show username prompt modal
    setTempUsername(username || "");
    setUsernameModalVisible(true);
  };

  const handleUsernameSubmit = async () => {
    const enteredUsername = tempUsername.trim();
    if (!enteredUsername) {
      showPopup("Error", "Please enter a username.", "alert-circle");
      setUsernameModalVisible(false);
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
      return;
    }

    // Validate username
    const sanitizedUsername = enteredUsername.toLowerCase().replace(/[^a-z0-9]/g, "");
    if (!sanitizedUsername) {
      showPopup("Error", "Invalid username. Use alphanumeric characters only.", "alert-circle");
      setUsernameModalVisible(false);
      return;
    }

    // Close the username modal
    setUsernameModalVisible(false);

    // Request camera permissions
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== "granted") {
      showPopup("Error", "Camera permission denied", "alert-circle");
      return;
    }

    // Launch camera
    // Launch camera
    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      quality: 0.95,
      quality: 0.95,
      aspect: [1, 1],
    });

    if (result.canceled || !result.assets?.[0]?.uri) {
      return;
    }

    setIsProcessing(true);
    const imageUri = result.assets[0].uri;

    try {
      // Construct S3 object name with user_USERNAME format
      // Construct S3 object name with user_USERNAME format
      const objectName = `user_${sanitizedUsername}.jpg`;

      // Get presigned URL
      // Get presigned URL
      const response = await fetch(
        `${API_GATEWAY_URL}?username=${encodeURIComponent(sanitizedUsername)}`
      );

      if (!response.ok) {
        throw new Error(`API request failed: ${response.status} ${response.statusText}`);
        throw new Error(`API request failed: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      let presignedUrl;
      if (data.body) {
        const body = typeof data.body === "object" ? data.body : JSON.parse(data.body);
        const body = typeof data.body === "object" ? data.body : JSON.parse(data.body);
        presignedUrl = body.presignedUrl;
      } else if (data.presignedUrl) {
        presignedUrl = data.presignedUrl;
      } else {
        throw new Error("Pre-signed URL not found in response: " + JSON.stringify(data));
        throw new Error("Pre-signed URL not found in response: " + JSON.stringify(data));
      }

      if (!presignedUrl) {
        throw new Error("Pre-signed URL is missing or invalid");
      }

      // Upload image to S3
      // Upload image to S3
      const imageResponse = await fetch(imageUri);
      const blob = await imageResponse.blob();
      const uploadResponse = await fetch(presignedUrl, {
        method: "PUT",
        body: blob,
        headers: { "Content-Type": "image/jpeg" },
      });

      if (!uploadResponse.ok) {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
        throw new Error(`S3 upload failed: ${response.statusText}`);
=======
        throw new Error(`S3 upload: ${uploadResponse.statusText}`);
>>>>>>> Stashed changes
=======
        throw new Error(`S3 upload: ${uploadResponse.statusText}`);
>>>>>>> Stashed changes
      }

      // Construct S3 URL
      // Construct S3 URL
      const s3Url = `https://${BUCKET_NAME}.s3.amazonaws.com/${objectName}`;
      console.log("S3 URL:", s3Url);

      // Save to Firebase if user is authenticated
      if (currentUser?.uid) {
        await db.ref(`users/${currentUser.uid}/profileImage`).set(s3Url);
        await db.ref(`users/${currentUser.uid}/imageHistory`).push({

      // Save to Firebase if user is authenticated
      if (currentUser?.uid) {
        await db.ref(`users/${currentUser.uid}/profileImage`).set(s3Url);
        await db.ref(`users/${currentUser.uid}/imageHistory`).push({
          url: s3Url,
          timestamp: new Date().toISOString(),
          path: objectName,
        });
        // Update username in Firebase
        await db.ref(`users/${currentUser.uid}/username`).set(enteredUsername);
        setUsername(enteredUsername);
        // Update username in Firebase
        await db.ref(`users/${currentUser.uid}/username`).set(enteredUsername);
        setUsername(enteredUsername);
      }

      setUserImage(s3Url);
      setImageCacheBuster(Date.now());
      showPopup("Success", "Image captured and uploaded successfully!", "checkmark-circle");
      setImageCacheBuster(Date.now());
      showPopup("Success", "Image captured and uploaded successfully!", "checkmark-circle");
    } catch (error) {
      console.error("Upload error:", error);
      showPopup("Error", `Failed to upload image: ${error.message}`, "alert-circle");
      showPopup("Error", `Failed to upload image: ${error.message}`, "alert-circle");
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
    if (pwd.length < 8) {
    if (pwd.length < 8) {
      showPopup(
        "Error",
        "Password must be at least 8 characters",
        "Password must be at least 8 characters",
        "alert-circle"
      );
      return;
    }
    setIsSavingWifi(true);
    try {
      await saveWifiSettings({
        wifiSSID: ssid,
        wifiPassword: pwd,
      });
      showPopup(
        "Success",
        "Wi-Fi settings saved successfully!",
        "checkmark-circle"
      );
      showPopup(
        "Success",
        "Wi-Fi settings saved successfully!",
        "checkmark-circle"
      );
    } catch (err) {
      showPopup(
        "Error",
        `Failed to save Wi-Fi settings: ${err.message}`,
        "alert-circle"
      );
      showPopup(
        "Error",
        `Failed to save Wi-Fi settings: ${err.message}`,
        "alert-circle"
      );
    } finally {
      setIsSavingWifi(false);
    }
  };

  const handleShowQrCode = () => {
    if (!wifiSSID.trim() || !wifiPassword.trim()) {
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
        "No PEBO devices available. Please add a device first.",
        "alert-circle"
      );
      return;
    }
    if (!currentUser?.uid) {
      showPopup(
        "Error",
        "User not authenticated. Please log in again.",
        "alert-circle"
      );
      return;
    }
    setDeviceSelectModalVisible(true);
  };

  const handleSelectDevice = (deviceId) => {
    console.log("Selected device ID:", deviceId);
    setSelectedDeviceId(deviceId);
    setDeviceSelectModalVisible(false);
    if (peboDevices.length === 0) {
      showPopup(
        "Error",
        "No PEBO devices available. Please add a device first.",
        "alert-circle"
      );
      return;
    }
    if (!currentUser?.uid) {
      showPopup(
        "Error",
        "User not authenticated. Please log in again.",
        "alert-circle"
      );
      return;
    }
    setDeviceSelectModalVisible(true);
  };

  const handleSelectDevice = (deviceId) => {
    console.log("Selected device ID:", deviceId);
    setSelectedDeviceId(deviceId);
    setDeviceSelectModalVisible(false);
    setQrModalVisible(true);
  };

  const generateQrCodeValue = () => {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    const credentials = {
      ssid: wifiSSID.trim(),
      password: wifiPassword.trim(),
    };
    return JSON.stringify(credentials);
=======
=======
>>>>>>> Stashed changes
    if (
      !wifiSSID.trim() ||
      !wifiPassword.trim() ||
      !selectedDeviceId ||
      !currentUser?.uid
    ) {
      console.warn("Invalid QR code data:", {
        wifiSSID,
        wifiPassword,
        selectedDeviceId,
        userId: currentUser?.uid,
      });
      return "";
    }
    const credentials = {
      ssid: wifiSSID.trim(),
      password: wifiPassword.trim(),
      deviceId: selectedDeviceId,
      userId: currentUser.uid,
    };
    const qrValue = JSON.stringify(credentials);
    console.log("Generated QR code value:", qrValue);
    return qrValue;
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
  };

  const handleAddPebo = async () => {
    const name = peboName.trim();
    const loc = peboLocation.trim();
    if (!name || !loc) {
      showPopup(
        "Error",
        "Please enter both a PEBO name and a location.",
        "alert-circle"
      );
      showPopup(
        "Error",
        "Please enter both a PEBO name and a location.",
        "alert-circle"
      );
      return;
    }
    try {
      await addPeboDevice({ name, location: loc });
      const updated = await getPeboDevices();
      setPeboDevices(updated);
      if (updated.length > 0 && !selectedDeviceId) {
        setSelectedDeviceId(updated[0].id);
      }
      if (updated.length > 0 && !selectedDeviceId) {
        setSelectedDeviceId(updated[0].id);
      }
      setModalVisible(false);
      setPeboName("");
      setPeboLocation("");
      showPopup(
        "Success",
        "New PEBO device added successfully!",
        "checkmark-circle"
      );
      showPopup(
        "Success",
        "New PEBO device added successfully!",
        "checkmark-circle"
      );
    } catch (err) {
      showPopup("Error", `Failed to add PEBO: ${err.message}`, "alert-circle");
      showPopup("Error", `Failed to add PEBO: ${err.message}`, "alert-circle");
    }
  };

  const handleLogout = async () => {
    try {
      await auth.signOut();
      navigation.reset({ index: 0, routes: [{ name: "Login" }] });
    } catch (err) {
      showPopup("Error", `Logout failed: ${err.message}`, "alert-circle");
      showPopup("Error", `Logout failed: ${err.message}`, "alert-circle");
    }
  };

  if (isLoading) {
    return (
      <View style={styles.container}>
        <ActivityIndicator
          size="large"
          color="#1976D2"
          style={{ marginTop: 20 }}
        />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Seeeeeettings</Text>
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Ionicons
              name="person-circle"
              size={styles.personCircleSize}
              color={styles.primaryColor}
            />
            <Text style={styles.cardLabel}>My Photo</Text>
            <Ionicons
              name="person-circle"
              size={styles.personCircleSize}
              color={styles.primaryColor}
            />
            <Text style={styles.cardLabel}>My Photo</Text>
          </View>
          <View style={styles.userSection}>
          <View style={styles.userSection}>
            {userImage && userImage !== "" ? (
              <Image
                source={{
                  uri: `${userImage}?t=${imageCacheBuster}`,
                  uri: `${userImage}?t=${imageCacheBuster}`,
                }}
                style={styles.userImage}
                style={styles.userImage}
                onError={(e) =>
                  console.log("Image load error:", e.nativeEvent.error)
                }
              />
            ) : (
              <View style={styles.placeholderImage}>
                <Ionicons name="person" size={styles.personIcon} color="#ccc" />
                <Ionicons name="person" size={styles.personIcon} color="#ccc" />
                <Text style={styles.placeholderText}>No Image</Text>
              </View>
            )}
            <TouchableOpacity
              accessibilityLabel="Capture new image"
              accessibilityRole="button"
              onPress={captureAndUploadImage}
              accessibilityLabel="Capture new image"
              accessibilityRole="button"
              onPress={captureAndUploadImage}
              style={[
                styles.photoButton,
                isProcessing ? styles.processingButton : null,
                isProcessing ? styles.processingButton : null,
              ]}
              disabled={isProcessing}
            >
              {isProcessing ? (
                <>
                  <ActivityIndicator size="small" color="#fff" />
                  <Text style={styles.buttonText}>Processing...</Text>
                  <Text style={styles.buttonText}>Processing...</Text>
                </>
              ) : (
                <>
                  <Ionicons name="camera" size={styles.camera} color="#fff" />
                  <Text style={styles.cameraButtonText}>Capture New Image</Text>
                  <Ionicons name="camera" size={styles.camera} color="#fff" />
                  <Text style={styles.cameraButtonText}>Capture New Image</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        </View>
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <MaterialIcons
              name="wifi"
              size={styles.wifiIcon}
              color={styles.wifiColor}
            />
            <MaterialIcons
              name="wifi"
              size={styles.wifiIcon}
              color={styles.wifiColor}
            />
            <Text style={styles.cardLabel}>Wi-Fi Configuration</Text>
          </View>
          <TextInput
            placeholder="SSID"
            style={[styles.input, !wifiSSID.trim() && styles.inputError]}
            value={wifiSSID}
            onChangeText={setWifiSSID}
            placeholderTextColor="#999"
            accessibilityLabel="Wi-Fi SSID"
            accessibilityLabel="Wi-Fi SSID"
          />
          <View style={styles.inputContainer}>
          <View style={styles.inputContainer}>
            <TextInput
              placeholder="Password"
              style={[
                styles.input,
                (!wifiPassword.trim() || wifiPassword.length < 8) &&
                (!wifiPassword.trim() || wifiPassword.length < 8) &&
                  styles.inputError,
              ]}
              secureTextEntry={!showPassword}
              value={wifiPassword}
              onChangeText={setWifiPassword}
              placeholderTextColor="#999"
              accessibilityLabel="Wi-Fi Password"
              accessibilityLabel="Wi-Fi Password"
            />
            <TouchableOpacity
              onPress={() => setShowPassword((v) => !v)}
              style={styles.eyeIconContainer}
              accessibilityLabel={
                showPassword ? "Hide password" : "Show password"
              }
              style={styles.eyeIconContainer}
              accessibilityLabel={
                showPassword ? "Hide password" : "Show password"
              }
            >
              <Ionicons
                name={showPassword ? "eye-off" : "eye"}
                size={styles.eyeIcon}
                size={styles.eyeIcon}
                color="#999"
              />
            </TouchableOpacity>
          </View>
          <TouchableOpacity
            accessibilityLabel="Save Wi-Fi settings"
            accessibilityLabel="Save Wi-Fi settings"
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
                <Ionicons name="wifi" size={styles.wifiIconSize} color="#fff" />
                <Ionicons name="wifi" size={styles.wifiIconSize} color="#fff" />
                <Text style={styles.saveButtonText}>Save Wi-Fi</Text>
              </>
            )}
          </TouchableOpacity>
          <TouchableOpacity
            accessibilityLabel="Show Wi-Fi QR code"
            style={[
              styles.qrButton,
              (!wifiSSID.trim() || !wifiPassword.trim()) && {
                backgroundColor: "#ddd",
              },
            ]}
            accessibilityLabel="Show Wi-Fi QR code"
            style={[
              styles.qrButton,
              (!wifiSSID.trim() || !wifiPassword.trim()) && {
                backgroundColor: "#ddd",
              },
            ]}
            onPress={handleShowQrCode}
            disabled={!wifiSSID.trim() || !wifiPassword.trim()}
          >
            <Ionicons name="qr-code" size={styles.qrIconSize} color="#fff" />
            <Text style={styles.qrButtonText}>Show QR Code</Text>
            <Ionicons name="qr-code" size={styles.qrIconSize} color="#fff" />
            <Text style={styles.qrButtonText}>Show QR Code</Text>
          </TouchableOpacity>
        </View>
        <TouchableOpacity
          accessibilityLabel="Add new device"
          accessibilityLabel="Add new device"
          style={styles.addButton}
          onPress={() => setModalVisible(true)}
        >
          <Ionicons
            name="add-circle-outline"
            size={styles.addIcon}
            color="#fff"
          />
          <Text style={styles.addButtonText}>Add New Device</Text>
          <Ionicons
            name="add-circle-outline"
            size={styles.addIcon}
            color="#fff"
          />
          <Text style={styles.addButtonText}>Add New Device</Text>
        </TouchableOpacity>
        <View style={styles.deviceContainer}>
          <Text style={styles.sectionTitle}>My Devices</Text>
        <View style={styles.deviceContainer}>
          <Text style={styles.sectionTitle}>My Devices</Text>
          {peboDevices.length === 0 ? (
            <Text style={styles.emptyText}>No devices found.</Text>
            <Text style={styles.emptyText}>No devices found.</Text>
          ) : (
            peboDevices.map((pebo) => (
              <View key={pebo.id} style={styles.peboCard}>
                <View style={styles.peboHeader}>
                  <Ionicons
                    name="hardware-chip-outline"
                    size={styles.chipIcon}
                    size={styles.chipIcon}
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
          accessibilityLabel="Log out"
          style={styles.logoutButton}
          accessibilityLabel="Log out"
          style={styles.logoutButton}
          onPress={() => setLogoutModalVisible(true)}
        >
          <Ionicons
            name="log-out-outline"
            size={styles.logoutIcon}
            color="#fff"
          />
          <Text style={styles.logoutText}>Logout</Text>
          <Ionicons
            name="log-out-outline"
            size={styles.logoutIcon}
            color="#fff"
          />
          <Text style={styles.logoutText}>Logout</Text>
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
            <Text style={styles.modalTitle}>Add New Device</Text>
            <Text style={styles.modalTitle}>Add New Device</Text>
            <TextInput
              placeholder="Device Name"
              placeholder="Device Name"
              value={peboName}
              onChangeText={setPeboName}
              style={styles.input}
              placeholderTextColor="#999"
              accessibilityLabel="Device name"
              accessibilityLabel="Device name"
            />
            <TextInput
              placeholder="Location (e.g., Kitchen)"
              value={peboLocation}
              onChangeText={setPeboLocation}
              style={styles.input}
              placeholderTextColor="#999"
              accessibilityLabel="Device location"
              accessibilityLabel="Device location"
            />
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={styles.modalButton}
                style={styles.modalButton}
                onPress={handleAddPebo}
                accessibilityLabel="Add device"
                accessibilityLabel="Add device"
              >
                <Text style={styles.modalButtonText}>Add Device</Text>
                <Text style={styles.modalButtonText}>Add Device</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.cancelButton}
                style={styles.cancelButton}
                onPress={() => setModalVisible(false)}
                accessibilityLabel="Cancel"
                accessibilityLabel="Cancel"
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
                <Text style={styles.cancelButtonText}>Cancel</Text>
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
              <TouchableOpacity
                style={styles.logoutConfirmButton}
              <TouchableOpacity
                style={styles.logoutConfirmButton}
                onPress={handleLogout}
                accessibilityLabel="Confirm logout"
                accessibilityLabel="Confirm logout"
              >
                <Text style={styles.modalButtonText}>Logout</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.cancelConfirmButton}
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.cancelConfirmButton}
                onPress={() => setLogoutModalVisible(false)}
                accessibilityLabel="Cancel logout"
                accessibilityLabel="Cancel logout"
              >
                <Text style={styles.modalButtonText}>Cancel</Text>
              </TouchableOpacity>
                <Text style={styles.modalButtonText}>Cancel</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
      <Modal
        transparent
        visible={deviceSelectModalVisible}
        visible={deviceSelectModalVisible}
        animationType="fade"
        onRequestClose={() => setDeviceSelectModalVisible(false)}
        onRequestClose={() => setDeviceSelectModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Select Device</Text>
            <View style={styles.pickerContainer}>
              <Ionicons
                name="hardware-chip-outline"
                style={styles.pickerIcon}
              />
              <Picker
                selectedValue={selectedDeviceId}
                onValueChange={(value) => setSelectedDeviceId(value)}
                style={styles.picker}
                itemStyle={styles.pickerItem}
                accessibilityLabel="Select device"
              >
                <Picker.Item
                  label="Select a device..."
                  value={null}
                  style={styles.pickerPlaceholder}
                />
                {peboDevices.map((device) => (
                  <Picker.Item
                    key={device.id}
                    label={`${device.name} (${device.location})`}
                    value={device.id}
                    style={[
                      styles.pickerItem,
                      selectedDeviceId === device.id &&
                        styles.pickerItemSelected,
                    ]}
                  />
                ))}
              </Picker>
            </View>
            <Text style={styles.modalTitle}>Select Device</Text>
            <View style={styles.pickerContainer}>
              <Ionicons
                name="hardware-chip-outline"
                style={styles.pickerIcon}
              />
              <Picker
                selectedValue={selectedDeviceId}
                onValueChange={(value) => setSelectedDeviceId(value)}
                style={styles.picker}
                itemStyle={styles.pickerItem}
                accessibilityLabel="Select device"
              >
                <Picker.Item
                  label="Select a device..."
                  value={null}
                  style={styles.pickerPlaceholder}
                />
                {peboDevices.map((device) => (
                  <Picker.Item
                    key={device.id}
                    label={`${device.name} (${device.location})`}
                    value={device.id}
                    style={[
                      styles.pickerItem,
                      selectedDeviceId === device.id &&
                        styles.pickerItemSelected,
                    ]}
                  />
                ))}
              </Picker>
            </View>
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={styles.selectDeviceButton}
                onPress={() => handleSelectDevice(selectedDeviceId)}
                disabled={!selectedDeviceId}
                accessibilityLabel="Select device and show QR code"
                style={styles.selectDeviceButton}
                onPress={() => handleSelectDevice(selectedDeviceId)}
                disabled={!selectedDeviceId}
                accessibilityLabel="Select device and show QR code"
              >
                <Text style={styles.modalButtonText}>Select & Show QR</Text>
                <Text style={styles.modalButtonText}>Select & Show QR</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.cancelDeviceButton}
                onPress={() => setDeviceSelectModalVisible(false)}
                accessibilityLabel="Cancel device selection"
                style={styles.cancelDeviceButton}
                onPress={() => setDeviceSelectModalVisible(false)}
                accessibilityLabel="Cancel device selection"
              >
                <Text style={styles.modalButtonText}>Cancel</Text>
                <Text style={styles.modalButtonText}>Cancel</Text>
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
              Show this QR code to the device's camera to configure Wi-Fi.
              Show this QR code to the device's camera to configure Wi-Fi.
            </Text>
<<<<<<< Updated upstream
<<<<<<< Updated upstream
            <View style={styles.qrCodeContainer}>
              <QRCode
                value={generateQrCodeValue()}
                size={200}
                backgroundColor="#FFF"
                color="#000"
              />
            </View>
            <TouchableOpacity
              style={styles.closeQrModalButton}
              onPress={() => setQrModalVisible(false)}
              accessibilityLabel="Close QR code modal"
            >
              <Text style={[styles.modalButtonText, { color: "#333" }]}>
                Close
=======
=======
>>>>>>> Stashed changes
            {generateQrCodeValue() ? (
              <View style={styles.qrCodeContainer}>
                <QRCode
                  value={generateQrCodeValue()}
                  size={280}
                  color="#000"
                  backgroundColor="#FFF"
                />
              </View>
            ) : (
              <Text style={styles.errorText}>
                Unable to generate QR code. Please ensure Wi-Fi settings and
                device are selected.
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
              </Text>
            )}
            <TouchableOpacity
              style={styles.closeQrModalButton}
              onPress={() => setQrModalVisible(false)}
              accessibilityLabel="Close QR code modal"
            >
              <Text style={styles.modalButtonText}>Close</Text>
            </TouchableOpacity>
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
            <Text style={styles.modalTitle}>Enter Username</Text>
            <TextInput
              placeholder="Username"
              value={tempUsername}
              onChangeText={setTempUsername}
              style={styles.input}
              placeholderTextColor="#999"
              accessibilityLabel="Username input"
            />
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={styles.modalButton}
                onPress={handleUsernameSubmit}
                accessibilityLabel="Submit username"
              >
                <Text style={styles.modalButtonText}>Submit</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.cancelButton}
                onPress={() => setUsernameModalVisible(false)}
                accessibilityLabel="Cancel username input"
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>
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
            <Text style={styles.modalTitle}>Enter Username</Text>
            <TextInput
              placeholder="Username"
              value={tempUsername}
              onChangeText={setTempUsername}
              style={styles.input}
              placeholderTextColor="#999"
              accessibilityLabel="Username input"
            />
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={styles.modalButton}
                onPress={handleUsernameSubmit}
                accessibilityLabel="Submit username"
              >
                <Text style={styles.modalButtonText}>Submit</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.cancelButton}
                onPress={() => setUsernameModalVisible(false)}
                accessibilityLabel="Cancel username input"
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
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
        icon={popupContent.icon}
      />
    </View>
  );
};

<<<<<<< Updated upstream
<<<<<<< Updated upstream
export default SettingsScreen;

=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F4F9FF",
    padding: 24,
  },
  header: {
    fontSize: 28,
    fontWeight: "bold",
    marginTop: 20,
    color: "#1976D2",
    marginTop: 20,
    color: "#1976D2",
    marginBottom: 20,
    alignSelf: "center",
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: "700",
    marginBottom: 14,
    color: "#1976D2",
    color: "#1976D2",
  },
  card: {
    backgroundColor: "#FFFFFF",
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    elevation: 3,
    shadowColor: "#000000",
    marginBottom: 16,
    elevation: 3,
    shadowColor: "#000000",
    shadowOpacity: 0.1,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 12,
    marginBottom: 12,
  },
  cardLabel: {
    fontSize: 16,
    fontWeight: "600",
    marginLeft: 8,
    color: "#1976D2",
  },
  userSection: {
    alignItems: "center",
    marginVertical: 12,
  },
  userImage: {
    width: 120,
    height: 120,
    borderRadius: 60,
    marginBottom: 8,
  },
  placeholderImage: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: "#E0E0E0",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 8,
  },
  placeholderText: {
    color: "#757575",
    fontSize: 12,
    marginTop: 4,
  },
  photoButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#4CAF50",
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    width: "80%",
  },
  processingButton: {
    backgroundColor: "#B0BEC5",
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
    marginLeft: 8,
  },
  cameraButtonText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
    marginLeft: 8,
    color: "#1976D2",
  },
  userSection: {
    alignItems: "center",
    marginVertical: 12,
  },
  userImage: {
    width: 120,
    height: 120,
    borderRadius: 60,
    marginBottom: 8,
  },
  placeholderImage: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: "#E0E0E0",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 8,
  },
  placeholderText: {
    color: "#757575",
    fontSize: 12,
    marginTop: 4,
  },
  photoButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#4CAF50",
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    width: "80%",
  },
  processingButton: {
    backgroundColor: "#B0BEC5",
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
    marginLeft: 8,
  },
  cameraButtonText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
    marginLeft: 8,
  },
  input: {
    backgroundColor: "#ECEFF1",
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 12,
    fontSize: 14,
    color: "#212121",
    marginBottom: 8,
    backgroundColor: "#ECEFF1",
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 12,
    fontSize: 14,
    color: "#212121",
    marginBottom: 8,
  },
  inputError: {
    borderColor: "#D32F2F",
    borderColor: "#D32F2F",
    borderWidth: 1,
  },
  inputContainer: {
    position: "relative",
    marginBottom: 8,
  },
  eyeIconContainer: {
    position: "absolute",
    right: 12,
    top: 12,
  },
  inputContainer: {
    position: "relative",
    marginBottom: 8,
  },
  eyeIconContainer: {
    position: "absolute",
    right: 12,
    top: 12,
  },
  saveButton: {
    backgroundColor: "#1976D2",
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: "#1976D2",
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 8,
    marginTop: 8,
    flexDirection: "row",
  },
  qrButton: {
    backgroundColor: "#34C759",
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 8,
    flexDirection: "row",
  },
  qrButton: {
    backgroundColor: "#34C759",
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 8,
    flexDirection: "row",
  },
  saveButtonText: {
    color: "#FFFFFF",
    fontSize: 14,
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
    marginLeft: 8,
  },
  qrButtonText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
    marginLeft: 4,
    marginLeft: 8,
  },
  qrButtonText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
    marginLeft: 4,
  },
  addButton: {
    flexDirection: "row",
    backgroundColor: "#1976D2",
    borderRadius: 12,
    padding: 12,
    backgroundColor: "#1976D2",
    borderRadius: 12,
    padding: 12,
    alignItems: "center",
    justifyContent: "center",
    marginVertical: 8,
    marginVertical: 8,
  },
  addButtonText: {
    color: "#FFFFFF",
    fontSize: 14,
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
    marginLeft: 8,
    marginLeft: 8,
  },
  logoutButton: {
    flexDirection: "row",
    backgroundColor: "#D32F2F",
    borderRadius: 12,
    padding: 12,
  logoutButton: {
    flexDirection: "row",
    backgroundColor: "#D32F2F",
    borderRadius: 12,
    padding: 12,
    alignItems: "center",
    justifyContent: "center",
    marginVertical: 8,
    justifyContent: "center",
    marginVertical: 8,
  },
  logoutText: {
    color: "#FFFFFF",
  logoutText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
    marginLeft: 8,
  },
  deviceContainer: {
    marginTop: 16,
    fontWeight: "600",
    marginLeft: 8,
  },
  deviceContainer: {
    marginTop: 16,
  },
  emptyText: {
    color: "#616161",
    fontSize: 14,
    color: "#616161",
    fontSize: 14,
    textAlign: "center",
    backgroundColor: "#F5F5F5",
    padding: 16,
    borderRadius: 8,
    marginVertical: 8,
    backgroundColor: "#F5F5F5",
    padding: 16,
    borderRadius: 8,
    marginVertical: 8,
  },
  peboCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
    elevation: 2,
    shadowColor: "#000000",
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
    elevation: 2,
    shadowColor: "#000000",
    shadowOpacity: 0.1,
    shadowRadius: 6,
    shadowRadius: 6,
  },
  peboHeader: {
    flexDirection: "row",
    alignItems: "center",
  },
  peboInfo: {
    marginLeft: 8,
    marginLeft: 8,
    flex: 1,
  },
  peboName: {
    fontSize: 16,
    fontWeight: "500",
    color: "#212121",
    fontSize: 16,
    fontWeight: "500",
    color: "#212121",
  },
  peboLocation: {
    fontSize: 12,
    color: "#757575",
    marginTop: 1,
    fontSize: 12,
    color: "#757575",
    marginTop: 1,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.5)",
    backgroundColor: "rgba(0,0,0,0.5)",
    justifyContent: "center",
    alignItems: "center",
  },
  modalContent: {
    width: "85%",
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 20,
    elevation: 5,
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 20,
    elevation: 5,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: "#1976D2",
    color: "#1976D2",
    textAlign: "center",
    marginBottom: 16,
    marginBottom: 16,
  },
  modalSubtitle: {
    fontSize: 12,
    color: "#616161",
    fontSize: 12,
    color: "#616161",
    textAlign: "center",
    marginBottom: 12,
    marginBottom: 12,
  },
  modalButtons: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 12,
    marginTop: 12,
  },
  modalButton: {
    flex: 1,
    backgroundColor: "#1976D2",
    padding: 10,
    borderRadius: 8,
    backgroundColor: "#1976D2",
    padding: 10,
    borderRadius: 8,
    alignItems: "center",
    marginRight: 4,
  },
  cancelButton: {
    flex: 1,
    backgroundColor: "#D32F2F",
    padding: 10,
    borderRadius: 8,
    alignItems: "center",
    marginLeft: 4,
    marginRight: 4,
  },
  cancelButton: {
    flex: 1,
    backgroundColor: "#D32F2F",
    padding: 10,
    borderRadius: 8,
    alignItems: "center",
    marginLeft: 4,
  },
  modalButtonText: {
    color: "#FFFFFF",
    fontSize: 14,
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
  },
  cancelButtonText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
  },
  logoutConfirmButton: {
    flex: 1,
    backgroundColor: "#D32F2F",
    padding: 10,
    borderRadius: 8,
    alignItems: "center",
    marginRight: 4,
  },
  cancelConfirmButton: {
    flex: 1,
    backgroundColor: "#1976D2",
    padding: 10,
    borderRadius: 8,
    alignItems: "center",
    marginLeft: 4,
  },
  selectDeviceButton: {
    flex: 1,
    backgroundColor: "#1976D2",
    padding: 10,
    borderRadius: 8,
    alignItems: "center",
    marginRight: 4,
  },
  cancelDeviceButton: {
    flex: 1,
    backgroundColor: "#D32F2F",
    padding: 10,
    borderRadius: 8,
    alignItems: "center",
    marginLeft: 4,
  },
  cancelButtonText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
  },
  logoutConfirmButton: {
    flex: 1,
    backgroundColor: "#D32F2F",
    padding: 10,
    borderRadius: 8,
    alignItems: "center",
    marginRight: 4,
  },
  cancelConfirmButton: {
    flex: 1,
    backgroundColor: "#1976D2",
    padding: 10,
    borderRadius: 8,
    alignItems: "center",
    marginLeft: 4,
  },
  selectDeviceButton: {
    flex: 1,
    backgroundColor: "#1976D2",
    padding: 10,
    borderRadius: 8,
    alignItems: "center",
    marginRight: 4,
  },
  cancelDeviceButton: {
    flex: 1,
    backgroundColor: "#D32F2F",
    padding: 10,
    borderRadius: 8,
    alignItems: "center",
    marginLeft: 4,
  },
  qrCodeContainer: {
    backgroundColor: "#FFFFFF",
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    borderWidth: 2,
    borderColor: "#4CAF50",
    alignItems: "center",
  },
<<<<<<< Updated upstream
<<<<<<< Updated upstream
});
=======
  closeQrModalButton: {
    backgroundColor: "#1976D2",
    padding: 10,
    borderRadius: 8,
    alignItems: "center",
    marginTop: 12,
  },
  pickerContainer: {
    backgroundColor: "#ECEFF1",
    borderRadius: 8,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: "#1976D2",
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 8,
  },
  picker: {
    flex: 1,
    height: 40,
    color: "#212121",
  },
  pickerItem: {
    fontSize: 14,
    color: "#212121",
  },
  pickerItemSelected: {
    color: "#1976D2",
    fontWeight: "600",
  },
  pickerPlaceholder: {
    fontSize: 14,
    color: "#757575",
  },
  pickerIcon: {
    marginRight: 8,
    fontSize: 20,
    color: "#1976D2",
  },
  errorText: {
    color: "#D32F2F",
    fontSize: 12,
    textAlign: "center",
    marginBottom: 12,
  },
  personCircleSize: 20,
  primaryColor: "#1976D2",
  wifiIcon: 20,
  wifiColor: "#1976D2",
  personIcon: 80,
  camera: 20,
  eyeIcon: 22,
  wifiIconSize: 20,
  qrIconSize: 18,
  addIcon: 16,
  chipIcon: 20,
  logoutIcon: 16,
});

export default memo(SettingsScreen);
>>>>>>> Stashed changes
=======
  closeQrModalButton: {
    backgroundColor: "#1976D2",
    padding: 10,
    borderRadius: 8,
    alignItems: "center",
    marginTop: 12,
  },
  pickerContainer: {
    backgroundColor: "#ECEFF1",
    borderRadius: 8,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: "#1976D2",
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 8,
  },
  picker: {
    flex: 1,
    height: 40,
    color: "#212121",
  },
  pickerItem: {
    fontSize: 14,
    color: "#212121",
  },
  pickerItemSelected: {
    color: "#1976D2",
    fontWeight: "600",
  },
  pickerPlaceholder: {
    fontSize: 14,
    color: "#757575",
  },
  pickerIcon: {
    marginRight: 8,
    fontSize: 20,
    color: "#1976D2",
  },
  errorText: {
    color: "#D32F2F",
    fontSize: 12,
    textAlign: "center",
    marginBottom: 12,
  },
  personCircleSize: 20,
  primaryColor: "#1976D2",
  wifiIcon: 20,
  wifiColor: "#1976D2",
  personIcon: 80,
  camera: 20,
  eyeIcon: 22,
  wifiIconSize: 20,
  qrIconSize: 18,
  addIcon: 16,
  chipIcon: 20,
  logoutIcon: 16,
});

export default memo(SettingsScreen);
>>>>>>> Stashed changes

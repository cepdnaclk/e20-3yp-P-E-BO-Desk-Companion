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
  Dimensions,
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

import LoadingScreen from "../components/LoadingScreen"; // ✅ your animated loader

import PopupModal from "../components/PopupModal";

const { width, height } = Dimensions.get("window");

// Theme colors extracted from TaskManagementScreen
const THEME_COLORS = {
  primary: "#1DE9B6",
  secondary: "#4CAF50",
  background: "#000000",
  cardBackground: "rgba(26, 26, 26, 0.3)",
  cardBorder: "rgba(29, 233, 182, 0.2)",
  textPrimary: "#FFFFFF",
  textSecondary: "#888",
  textMuted: "#666",
  inputBackground: "rgba(26, 26, 26, 0.6)",
  inputBorder: "rgba(29, 233, 182, 0.3)",
  success: "#4CAF50",
  error: "#FF5252",
  warning: "#FF9800",
  accent: "#1DE9B6",
  glow: "rgba(29, 233, 182, 0.3)",
  shadow: "rgba(29, 233, 182, 0.2)",
  glassyGreen: "rgba(29, 233, 182, 0.1)",
  glassyBorder: "rgba(29, 233, 182, 0.4)",
  glassyGradient: ["#1DE9B6", "#00BFA5"],
};

const SettingsScreen = () => {
  const navigation = useNavigation();

  // All state variables
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
  const [processingUserId, setProcessingUserId] = useState(null);
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
  const [isLoading, setIsLoading] = useState(true);
  // Secondary users state variables
  const [addUserModalVisible, setAddUserModalVisible] = useState(false);
  const [newUserName, setNewUserName] = useState("");
  const [isAddingUser, setIsAddingUser] = useState(false);
  const [imageViewerVisible, setImageViewerVisible] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [selectedImageTitle, setSelectedImageTitle] = useState("");
  const [editUserModalVisible, setEditUserModalVisible] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [editUserName, setEditUserName] = useState("");
  const [isUpdatingUser, setIsUpdatingUser] = useState(false);
  const [isRemovingUser, setIsRemovingUser] = useState(false);
  const [removeUserModalVisible, setRemoveUserModalVisible] = useState(false);
  const [mainUserName, setMainUserName] = useState("");
  const [editMainUserModalVisible, setEditMainUserModalVisible] =
    useState(false);
  const [newMainUserName, setNewMainUserName] = useState("");
  const [isUpdatingMainUser, setIsUpdatingMainUser] = useState(false);
  const [selectedDeviceForUsers, setSelectedDeviceForUsers] = useState(null);
  const [deviceSecondaryUsers, setDeviceSecondaryUsers] = useState({});

  // Animation refs
  const pulse1 = useRef(new Animated.Value(0)).current;
  const pulse2 = useRef(new Animated.Value(0)).current;
  const rotate = useRef(new Animated.Value(0)).current;
  const float1 = useRef(new Animated.Value(0)).current;
  const float2 = useRef(new Animated.Value(0)).current;
  const glow = useRef(new Animated.Value(0)).current;
const canShowQr =
  wifiSSID.trim() &&
  wifiPassword.trim() &&
  wifiSSID.trim().toUpperCase() !== "N/A" &&
  wifiPassword.trim().toUpperCase() !== "N/A" &&
  peboDevices.length > 0;

  const BUCKET_NAME = "pebo-user-images";
  const API_GATEWAY_URL =
    "https://aw8yn9cbj1.execute-api.us-east-1.amazonaws.com/prod/presigned";

  // Animation effects
  useEffect(() => {
    // Energetic pulsing animation
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulse1, {
          toValue: 1,
          duration: 1500,
          useNativeDriver: true,
        }),
        Animated.timing(pulse1, {
          toValue: 0,
          duration: 1500,
          useNativeDriver: true,
        }),
      ])
    ).start();

    // Secondary pulse with offset
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulse2, {
          toValue: 1,
          duration: 2000,
          useNativeDriver: true,
        }),
        Animated.timing(pulse2, {
          toValue: 0,
          duration: 2000,
          useNativeDriver: true,
        }),
      ])
    ).start();

    // Continuous rotation
    Animated.loop(
      Animated.timing(rotate, {
        toValue: 1,
        duration: 20000,
        useNativeDriver: true,
      })
    ).start();

    // Floating animations
    Animated.loop(
      Animated.sequence([
        Animated.timing(float1, {
          toValue: 1,
          duration: 3000,
          useNativeDriver: true,
        }),
        Animated.timing(float1, {
          toValue: 0,
          duration: 3000,
          useNativeDriver: true,
        }),
      ])
    ).start();

    Animated.loop(
      Animated.sequence([
        Animated.timing(float2, {
          toValue: 1,
          duration: 4000,
          useNativeDriver: true,
        }),
        Animated.timing(float2, {
          toValue: 0,
          duration: 4000,
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

  const hasWifiChanged = () => {
    return (
      wifiSSID.trim() !== originalWifiSSID.trim() ||
      wifiPassword.trim() !== originalWifiPassword.trim()
    );
  };

  // Fetch data on component mount
  useEffect(() => {
    const fetchAllData = async () => {
      try {
        const devices = await getPeboDevices();
        setPeboDevices(devices);

        const wifi = await getWifiName();
        setWifiSSID(wifi.wifiSSID);
        setWifiPassword(wifi.wifiPassword);
        setOriginalWifiSSID(wifi.wifiSSID);
        setOriginalWifiPassword(wifi.wifiPassword);

        const userId = auth.currentUser?.uid;
   if (userId) {
     const imageSnap = await db
       .ref(`users/${userId}/profileImage`)
       .once("value");

     if (imageSnap.exists()) {
       const img = imageSnap.val();
       setUserImage(img);
       setImageTimestamp(Date.now());

       // Only fetch and set name if image exists
       const nameSnap = await db.ref(`users/${userId}/name`).once("value");
       if (nameSnap.exists()) {
         const name = nameSnap.val();
         if (typeof name === "string" && name.trim() !== "") {
           setMainUserName(name);
         }
       }
     }
   }

      } catch (err) {
        console.error("Initialization error:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAllData();
  }, []);

  // Image handling with better error handling
  const handleImageError = (error, imageType = "profile") => {
    console.log(`${imageType} image load error:`, error);
  };

  // **FIXED**: Main user image capture function
  const captureAndUploadImage = async () => {
    if (!username.trim()) {
      showPopup("Error", "How should PEBO call you?", "alert-circle");
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
        throw new Error(`S3 upload failed: ${uploadResponse.statusText}`);
      }

      const s3Url = `https://${BUCKET_NAME}.s3.amazonaws.com/${objectName}`;
      console.log("S3 URL:", s3Url);

      const userId = auth.currentUser?.uid;
      if (userId) {
        await db.ref(`users/${userId}/profileImage`).set(s3Url);
        await db.ref(`users/${userId}/name`).set(username);
        await db.ref(`users/${userId}/imageHistory`).push({
          url: s3Url,
          timestamp: new Date().toISOString(),
          path: objectName,
        });
      }

      setUserImage(s3Url);
      setMainUserName(username);
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

  // **FIXED**: Enhanced secondary user image capture with proper state management
  const captureAndUploadSecondaryUserImage = async (
    userId,
    deviceId,
    secondaryUserId,
    username
  ) => {
    if (!username.trim()) {
      showPopup("Error", "Username is required", "alert-circle");
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
      return;
    }

    // Set processing state for this specific user
    setProcessingUserId(secondaryUserId);
    const imageUri = result.assets[0].uri;

    try {
      // Use same naming format as main user
      const sanitizedUsername = username
        .toLowerCase()
        .replace(/[^a-z0-9]/g, "_");
      const objectName = `user_${sanitizedUsername}.jpg`;

      // Get presigned URL
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
        throw new Error("Pre-signed URL not found in response");
      }

      // Upload to S3
      const imageResponse = await fetch(imageUri);
      const blob = await imageResponse.blob();
      const uploadResponse = await fetch(presignedUrl, {
        method: "PUT",
        body: blob,
        headers: { "Content-Type": "image/jpeg" },
      });

      if (!uploadResponse.ok) {
        throw new Error(`S3 upload failed: ${uploadResponse.statusText}`);
      }

      const s3Url = `https://${BUCKET_NAME}.s3.amazonaws.com/${objectName}`;
      console.log("Secondary user S3 URL:", s3Url);

      // Save to Firebase with the correct path structure
      const mainUserId = auth.currentUser?.uid;
      if (mainUserId) {
        // Save under: users/{mainUserId}/peboDevices/{deviceId}/secondaryUsers/{secondaryUserId}
        await db
          .ref(
            `users/${mainUserId}/peboDevices/${deviceId}/secondaryUsers/${secondaryUserId}`
          )
          .update({
            name: username,
            profileImage: s3Url,
            updatedAt: new Date().toISOString(),
          });

        // Also update the existing device structure for compatibility
        await db
          .ref(`devices/${deviceId}/secondaryUsers/${secondaryUserId}`)
          .update({
            name: username,
            image: s3Url,
            updatedAt: new Date().toISOString(),
          });

        // Save to image history
        await db
          .ref(
            `users/${mainUserId}/peboDevices/${deviceId}/secondaryUsers/${secondaryUserId}/imageHistory`
          )
          .push({
            url: s3Url,
            timestamp: new Date().toISOString(),
            path: objectName,
          });
      }

      showPopup(
        "Success",
        "Secondary user image uploaded successfully",
        "checkmark-circle"
      );

      // Update local state
      const updatedUsers = {
        ...deviceSecondaryUsers,
        [deviceId]: deviceSecondaryUsers[deviceId].map((user) =>
          user.id === secondaryUserId
            ? { ...user, image: s3Url, name: username }
            : user
        ),
      };
      setDeviceSecondaryUsers(updatedUsers);
    } catch (error) {
      console.error("Secondary user upload error:", error);
      showPopup(
        "Error",
        `Failed to process image: ${error.message}`,
        "alert-circle"
      );
    } finally {
      setProcessingUserId(null);
    }
  };

  // **FIXED**: WiFi save function
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

      setOriginalWifiSSID(ssid);
      setOriginalWifiPassword(pwd);
      showPopup("Success", "Wi-Fi settings saved", "wifi");
    } catch (err) {
      showPopup("Error", err.message, "alert-circle");
    } finally {
      setIsSavingWifi(false);
    }
  };

  // **FIXED**: Show QR Code function
 const handleShowQrCode = () => {
   if (
     !wifiSSID.trim() ||
     !wifiPassword.trim() ||
     wifiSSID.trim().toUpperCase() === "N/A" ||
     wifiPassword.trim().toUpperCase() === "N/A"
   ) {
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


  // **FIXED**: Device selection for QR
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

  // **FIXED**: Add PEBO function
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

  // **FIXED**: Edit PEBO function
  const handleEditPebo = (pebo) => {
    setSelectedPebo(pebo);
    setEditPeboName(pebo.name);
    setEditPeboLocation(pebo.location);
    setEditPeboModalVisible(true);
  };

  // **FIXED**: Update PEBO function
  const handleUpdatePebo = async () => {
    const name = editPeboName.trim();
    const loc = editPeboLocation.trim();

    if (!name || !loc) {
      showPopup("Error", "Enter PEBO name and location", "alert-circle");
      return;
    }

    setIsUpdatingPebo(true);
    try {
      const success = await updatePeboDevice(selectedPebo.id, {
        name,
        location: loc,
      });

      if (success) {
        const updated = await getPeboDevices();
        setPeboDevices(updated);
        setEditPeboModalVisible(false);
        setSelectedPebo(null);
        setEditPeboName("");
        setEditPeboLocation("");
        showPopup("Success", "PEBO updated successfully!", "checkmark-circle");
      } else {
        showPopup("Error", "Failed to update PEBO", "alert-circle");
      }
    } catch (err) {
      console.error("Update PEBO error:", err);
      showPopup("Error", "Failed to update PEBO", "alert-circle");
    } finally {
      setIsUpdatingPebo(false);
    }
  };

  // **FIXED**: Remove PEBO function
  // **FIXED**: Remove PEBO function
  const handleRemovePebo = async () => {
    setRemoveModalVisible(true);
  };

  // **FIXED**: Confirm remove PEBO with better error handling
  const confirmRemovePebo = async () => {
    if (!selectedPebo || !selectedPebo.id) {
      showPopup("Error", "No device selected", "alert-circle");
      return;
    }

    setIsRemovingPebo(true);
    try {
      console.log("Attempting to remove PEBO:", selectedPebo.id);

      // Call the Firebase function
      await removePeboDevice(selectedPebo.id);

      // Refresh the devices list
      const updated = await getPeboDevices();
      setPeboDevices(updated);

      // Close modals and reset state
      setEditPeboModalVisible(false);
      setRemoveModalVisible(false);
      setSelectedPebo(null);
      setEditPeboName("");
      setEditPeboLocation("");

      showPopup("Success", "PEBO removed successfully!", "checkmark-circle");
    } catch (error) {
      console.error("Error in confirmRemovePebo:", error);
      showPopup(
        "Error",
        error.message || "Failed to remove PEBO",
        "alert-circle"
      );
    } finally {
      setIsRemovingPebo(false);
    }
  };

  const handleLogout = () => {
    const userId = auth.currentUser?.uid;
    if (userId) {
      db.ref(`users/${userId}/profileImage`).off(); // Detach listener
    }
    auth.signOut();
  };

  // **FIXED**: Confirm logout
  const confirmLogout = () => {
    setLogoutModalVisible(false);
    handleLogout();
  };

  // Secondary user functions
  const getDeviceSecondaryUsers = (deviceId) => {
    return deviceSecondaryUsers[deviceId] || [];
  };

  // **FIXED**: Add secondary user function
  const handleAddSecondaryUser = async () => {
    const name = newUserName.trim();
    if (!name) {
      showPopup("Error", "Enter user name", "alert-circle");
      return;
    }

    setIsAddingUser(true);
    try {
      const mainUserId = auth.currentUser?.uid;
      const deviceId = selectedDeviceForUsers.id;

      // Create new user reference in users-centered structure
      const newUserRef = db
        .ref(`users/${mainUserId}/peboDevices/${deviceId}/secondaryUsers`)
        .push();

      await newUserRef.set({
        name,
        createdAt: new Date().toISOString(),
      });

      // Update local state
      const updatedUsers = {
        ...deviceSecondaryUsers,
        [deviceId]: [
          ...(deviceSecondaryUsers[deviceId] || []),
          { id: newUserRef.key, name, createdAt: new Date().toISOString() },
        ],
      };
      setDeviceSecondaryUsers(updatedUsers);

      setAddUserModalVisible(false);
      setNewUserName("");
      setSelectedDeviceForUsers(null);
      showPopup("Success", "User added successfully!", "checkmark-circle");
    } catch (err) {
      showPopup("Error", err.message, "alert-circle");
    } finally {
      setIsAddingUser(false);
    }
  };

  // **FIXED**: Edit user function
  const handleEditUser = (user, deviceId) => {
    setSelectedUser({ ...user, deviceId });
    setEditUserName(user.name);
    setEditUserModalVisible(true);
  };

  // **FIXED**: Update user function

const handleUpdateUser = async () => {
  const name = editUserName.trim();
  if (!name) {
    showPopup("Error", "Enter user name", "alert-circle");
    return;
  }

  setIsUpdatingUser(true);
  try {
    const mainUserId = auth.currentUser?.uid;

    const sanitizedUsername = name.toLowerCase().replace(/[^a-z0-9]/g, "_");
    const objectName = `user_${sanitizedUsername}.jpg`;

    const snapshot = await db
      .ref(
        `users/${mainUserId}/peboDevices/${selectedUser.deviceId}/secondaryUsers/${selectedUser.id}/profileImage`
      )
      .once("value");

    const oldImageUrl = snapshot.exists() ? snapshot.val() : null;
    let s3Url = null;

    if (oldImageUrl) {
      const response = await fetch(
        `${API_GATEWAY_URL}?username=${encodeURIComponent(sanitizedUsername)}`
      );
      const data = await response.json();
      const presignedUrl = data.body
        ? JSON.parse(data.body).presignedUrl
        : data.presignedUrl;

      const oldImageBlob = await fetch(oldImageUrl).then((r) => r.blob());
      await fetch(presignedUrl, {
        method: "PUT",
        body: oldImageBlob,
        headers: { "Content-Type": "image/jpeg" },
      });

      s3Url = `https://${BUCKET_NAME}.s3.amazonaws.com/${objectName}`;
    }

    await db
      .ref(
        `users/${mainUserId}/peboDevices/${selectedUser.deviceId}/secondaryUsers/${selectedUser.id}`
      )
      .update({
        name,
        ...(s3Url && { profileImage: s3Url }),
        updatedAt: new Date().toISOString(),
      });

    await db
      .ref(`devices/${selectedUser.deviceId}/secondaryUsers/${selectedUser.id}`)
      .update({
        name,
        ...(s3Url && { image: s3Url }),
        updatedAt: new Date().toISOString(),
      });

    const updatedUsers = {
      ...deviceSecondaryUsers,
      [selectedUser.deviceId]: deviceSecondaryUsers[selectedUser.deviceId].map(
        (user) =>
          user.id === selectedUser.id
            ? { ...user, name, ...(s3Url && { image: s3Url }) }
            : user
      ),
    };
    setDeviceSecondaryUsers(updatedUsers);

    setEditUserModalVisible(false);
    setSelectedUser(null);
    setEditUserName("");
    showPopup("Success", "User updated successfully!", "checkmark-circle");
  } catch (err) {
    showPopup("Error", err.message, "alert-circle");
  } finally {
    setIsUpdatingUser(false);
  }
};

    

  // **FIXED**: Remove user function
  const handleRemoveUser = (user, deviceId) => {
    setSelectedUser({ ...user, deviceId });
    setRemoveUserModalVisible(true);
  };

  // **FIXED**: Confirm remove user
  const confirmRemoveUser = async () => {
    setIsRemovingUser(true);
    try {
      const mainUserId = auth.currentUser?.uid;

      // Remove from users-centered structure
      await db
        .ref(
          `users/${mainUserId}/peboDevices/${selectedUser.deviceId}/secondaryUsers/${selectedUser.id}`
        )
        .remove();

      // Update local state
      const updatedUsers = {
        ...deviceSecondaryUsers,
        [selectedUser.deviceId]: deviceSecondaryUsers[
          selectedUser.deviceId
        ].filter((user) => user.id !== selectedUser.id),
      };
      setDeviceSecondaryUsers(updatedUsers);

      setRemoveUserModalVisible(false);
      setSelectedUser(null);
      showPopup("Success", "User removed successfully!", "checkmark-circle");
    } catch (err) {
      showPopup("Error", err.message, "alert-circle");
    } finally {
      setIsRemovingUser(false);
    }
  };

  // **FIXED**: Update main user function
  const handleUpdateMainUser = async () => {    const name = newMainUserName.trim();
    if (!name) {
      showPopup("Error", "Enter user name", "alert-circle");
      return;
    }

    setIsUpdatingMainUser(true);
    try {
      const userId = auth.currentUser?.uid;
      if (userId) {
        const sanitizedUsername = name.toLowerCase().replace(/[^a-z0-9]/g, "_");
        const objectName = `user_${sanitizedUsername}.jpg`;

        const imageSnap = await db.ref(`users/${userId}/profileImage`).once("value");
        const oldImageUrl = imageSnap.exists() ? imageSnap.val() : null;

        if (oldImageUrl) {
          const response = await fetch(`${API_GATEWAY_URL}?username=${encodeURIComponent(sanitizedUsername)}`);
          const data = await response.json();
          const presignedUrl = data.body
            ? JSON.parse(data.body).presignedUrl
            : data.presignedUrl;

          const oldImageBlob = await fetch(oldImageUrl).then((r) => r.blob());

          await fetch(presignedUrl, {
            method: "PUT",
            body: oldImageBlob,
            headers: { "Content-Type": "image/jpeg" },
          });

          const s3Url = `https://${BUCKET_NAME}.s3.amazonaws.com/${objectName}`;

          await db.ref(`users/${userId}/profileImage`).set(s3Url);
          await db.ref(`users/${userId}/name`).set(name);
          await db.ref(`users/${userId}/imageHistory`).push({
            url: s3Url,
            timestamp: new Date().toISOString(),
            path: objectName,
          });

          setUserImage(s3Url);
          setImageTimestamp(Date.now());
        } else {
          await db.ref(`users/${userId}/name`).set(name);
        }

        setMainUserName(name);
        setEditMainUserModalVisible(false);
        setNewMainUserName("");
        showPopup("Success", "Name updated successfully!", "checkmark-circle");
      }
    } catch (err) {
      showPopup("Error", err.message, "alert-circle");
    } finally {
      setIsUpdatingMainUser(false);
    }};

  const openImageViewer = (imageUrl, title) => {
    setSelectedImage(imageUrl);
    setSelectedImageTitle(title);
    setImageViewerVisible(true);
  };

  const renderDeviceItem = ({ item }) => (
    <TouchableOpacity
      style={styles.deviceSelectionCard}
      onPress={() => handleDeviceSelection(item)}
    >
      <LinearGradient
        colors={[THEME_COLORS.cardBackground, "rgba(26, 26, 26, 0.8)"]}
        style={styles.deviceSelectionCardInner}
      >
        <View style={styles.deviceIcon}>
          <MaterialIcons name="router" size={24} color={THEME_COLORS.primary} />
        </View>
        <View style={styles.deviceInfo}>
          <Text style={styles.deviceName}>{item.name}</Text>
          <Text style={styles.deviceLocation}>{item.location}</Text>
        </View>
      </LinearGradient>
    </TouchableOpacity>
  );

  const rotateInterpolate = rotate.interpolate({
    inputRange: [0, 1],
    outputRange: ["0deg", "360deg"],
  });
  if (isLoading) {
    return <LoadingScreen message="Syncing PEBO Settings..." />;
  }

  return (
    <View style={styles.container}>
      <StatusBar
        barStyle="light-content"
        backgroundColor={THEME_COLORS.background}
      />

      {/* Enhanced Futuristic Animated Background */}
      <View style={styles.backgroundContainer}>
        <Animated.View
          style={[
            styles.pulseOrb1,
            {
              opacity: pulse1,
              transform: [
                {
                  scale: pulse1.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0.8, 1.2],
                  }),
                },
              ],
            },
          ]}
        />
        <Animated.View
          style={[
            styles.pulseOrb2,
            {
              opacity: pulse2,
              transform: [
                {
                  scale: pulse2.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0.6, 1.4],
                  }),
                },
              ],
            },
          ]}
        />
        <Animated.View
          style={[
            styles.floatingParticle1,
            {
              transform: [
                {
                  translateY: float1.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0, -30],
                  }),
                },
              ],
            },
          ]}
        />
        <Animated.View
          style={[
            styles.floatingParticle2,
            {
              transform: [
                {
                  translateY: float2.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0, 20],
                  }),
                },
              ],
            },
          ]}
        />
        <View style={styles.gridLines} />
      </View>

      {/* Header with Gradient */}
      <LinearGradient
        colors={[THEME_COLORS.glow, THEME_COLORS.cardBackground]}
        style={styles.header}
      >
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => navigation.navigate("Dashboard")}
        >
          <MaterialIcons
            name="arrow-back"
            size={24}
            color={THEME_COLORS.primary}
          />
        </TouchableOpacity>
        <Text style={styles.headerText}>CONTROL PANEL</Text>
        <TouchableOpacity
          style={styles.logoutButton}
          onPress={() => setLogoutModalVisible(true)}
        >
          <MaterialIcons name="logout" size={24} color={THEME_COLORS.primary} />
        </TouchableOpacity>
      </LinearGradient>

      <ScrollView
        style={styles.scrollView}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {/* Profile Section */}
        <View style={styles.profileSection}>
          <View style={styles.profileImageContainer}>
            <Animated.View
              style={[
                styles.profileGlow,
                {
                  opacity: glow,
                  transform: [
                    {
                      scale: glow.interpolate({
                        inputRange: [0, 1],
                        outputRange: [1, 1.1],
                      }),
                    },
                  ],
                },
              ]}
            />
            {userImage ? (
              <TouchableOpacity
                onPress={() =>
                  openImageViewer(userImage, mainUserName || "Main User")
                }
              >
                <Image
                  source={{ uri: `${userImage}?t=${imageTimestamp}` }}
                  style={styles.profileImage}
                  onError={(e) =>
                    handleImageError(e.nativeEvent.error, "profile")
                  }
                />
              </TouchableOpacity>
            ) : (
              <View style={styles.placeholderImage}>
                <MaterialIcons
                  name="person"
                  size={40}
                  color={THEME_COLORS.primary}
                />
              </View>
            )}
            <TouchableOpacity
              style={styles.cameraButton}
              onPress={() => setUsernameModalVisible(true)}
              disabled={isProcessing}
            >
              {isProcessing ? (
                <ActivityIndicator
                  size="small"
                  color={THEME_COLORS.background}
                />
              ) : (
                <MaterialIcons
                  name="camera-alt"
                  size={16}
                  color={THEME_COLORS.background}
                />
              )}
            </TouchableOpacity>
          </View>
          <View style={styles.nameSection}>
            <Text style={styles.profileName}></Text>

            {userImage && mainUserName && (
              <View style={styles.nameSection}>
                <Text style={styles.profileName}>{mainUserName}</Text>
                <TouchableOpacity
                  style={styles.editButton}
                  onPress={() => {
                    setNewMainUserName(mainUserName);
                    setEditMainUserModalVisible(true);
                  }}
                >
                  <MaterialIcons
                    name="edit"
                    size={16}
                    color={THEME_COLORS.primary}
                  />
                </TouchableOpacity>
              </View>
            )}
          </View>
        </View>

        {/* WiFi Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>NETWORK SETUP</Text>
          <View style={styles.cardContainer}>
            <View style={styles.inputGroup}>
              <TextInput
                style={styles.input}
                placeholder="WiFi SSID"
                placeholderTextColor={THEME_COLORS.textMuted}
                value={wifiSSID}
                onChangeText={setWifiSSID}
              />
              <View style={styles.passwordContainer}>
                <TextInput
                  style={[styles.input, { flex: 1, marginBottom: 0 }]}
                  placeholder="WiFi Password"
                  placeholderTextColor={THEME_COLORS.textMuted}
                  value={wifiPassword}
                  onChangeText={setWifiPassword}
                  secureTextEntry={!showPassword}
                />
                <TouchableOpacity
                  style={styles.eyeButton}
                  onPress={() => setShowPassword(!showPassword)}
                >
                  <MaterialIcons
                    name={showPassword ? "visibility" : "visibility-off"}
                    size={20}
                    color={THEME_COLORS.primary}
                  />
                </TouchableOpacity>
              </View>
            </View>

            <View style={styles.buttonRow}>
              {hasWifiChanged() && (
                <TouchableOpacity
                  style={[styles.button, styles.saveButton]}
                  onPress={handleSaveWifi}
                  disabled={isSavingWifi}
                >
                  <LinearGradient
                    colors={THEME_COLORS.glassyGradient}
                    style={styles.buttonGradient}
                  >
                    {isSavingWifi ? (
                      <ActivityIndicator
                        size="small"
                        color={THEME_COLORS.background}
                      />
                    ) : (
                      <Text style={styles.buttonText}>SAVE NETWORK</Text>
                    )}
                  </LinearGradient>
                </TouchableOpacity>
              )}
              <TouchableOpacity
                style={[
                  styles.button,
                  styles.qrButton,
                  !canShowQr && { opacity: 0.5 }, // Visually disables if requirements not met
                ]}
                onPress={handleShowQrCode}
                disabled={!canShowQr}
              >
                <View style={{ flexDirection: "row", alignItems: "center" }}>
                  <Ionicons
                    name="qr-code-outline"
                    size={24}
                    color={THEME_COLORS.primary}
                    style={{ marginRight: 8 }}
                  />
                  <Text
                    style={[styles.buttonText, { color: THEME_COLORS.primary }]}
                  >
                    SHOW QR
                  </Text>
                </View>
              </TouchableOpacity>
            </View>
          </View>
        </View>

        {/* PEBO Devices Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>PEBO DEVICES</Text>
            <TouchableOpacity
              style={styles.addButton}
              onPress={() => setModalVisible(true)}
            >
              <MaterialIcons
                name="add"
                size={20}
                color={THEME_COLORS.primary}
              />
            </TouchableOpacity>
          </View>

          {peboDevices.length === 0 ? (
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyText}>No PEBO devices found</Text>
            </View>
          ) : (
            peboDevices.map((device, index) => (
              <View key={index} style={styles.deviceCard}>
                <View style={styles.deviceHeader}>
                  <View style={styles.deviceInfo}>
                    <Text style={styles.deviceName}>{device.name}</Text>
                    <Text style={styles.deviceLocation}>{device.location}</Text>
                  </View>
                  <View style={styles.deviceActions}>
                    <TouchableOpacity
                      style={styles.addUserButton}
                      onPress={() => {
                        setSelectedDeviceForUsers(device);
                        setAddUserModalVisible(true);
                      }}
                    >
                      <MaterialIcons
                        name="person-add"
                        size={20}
                        color={THEME_COLORS.background}
                      />
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={styles.editDeviceButton}
                      onPress={() => handleEditPebo(device)}
                    >
                      <MaterialIcons
                        name="edit"
                        size={20}
                        color={THEME_COLORS.primary}
                      />
                    </TouchableOpacity>
                  </View>
                </View>

                {/* Device Secondary Users */}
                <View style={styles.deviceUsers}>
                  {getDeviceSecondaryUsers(device.id).length === 0 ? (
                    <Text style={styles.noUsersText}>No users added</Text>
                  ) : (
                    <FlatList
                      data={getDeviceSecondaryUsers(device.id)}
                      renderItem={({ item }) => (
                        <View style={styles.secondaryUserCard}>
                          <View style={styles.secondaryUserImageContainer}>
                            {item.image ? (
                              <TouchableOpacity
                                onPress={() =>
                                  openImageViewer(item.image, item.name)
                                }
                              >
                                <Image
                                  source={{ uri: item.image }}
                                  style={styles.secondaryUserImage}
                                  onError={(e) =>
                                    handleImageError(
                                      e.nativeEvent.error,
                                      "secondary user"
                                    )
                                  }
                                />
                              </TouchableOpacity>
                            ) : (
                              <View
                                style={[
                                  styles.secondaryUserImage,
                                  styles.placeholderSecondaryImage,
                                ]}
                              >
                                <MaterialIcons
                                  name="person"
                                  size={24}
                                  color={THEME_COLORS.primary}
                                />
                              </View>
                            )}

                            {/* Camera button for secondary users */}
                            <TouchableOpacity
                              style={styles.secondaryCameraButton}
                              onPress={() =>
                                captureAndUploadSecondaryUserImage(
                                  auth.currentUser?.uid,
                                  device.id,
                                  item.id,
                                  item.name
                                )
                              }
                              disabled={processingUserId === item.id}
                            >
                              {processingUserId === item.id ? (
                                <ActivityIndicator
                                  size="small"
                                  color={THEME_COLORS.background}
                                />
                              ) : (
                                <Ionicons
                                  name="camera"
                                  size={12}
                                  color={THEME_COLORS.background}
                                />
                              )}
                            </TouchableOpacity>
                          </View>

                          <Text
                            style={styles.secondaryUserName}
                            numberOfLines={1}
                          >
                            {item.name}
                          </Text>

                          <View style={styles.userActions}>
                            <TouchableOpacity
                              style={styles.editUserButton}
                              onPress={() => handleEditUser(item, device.id)}
                            >
                              <MaterialIcons
                                name="edit"
                                size={12}
                                color={THEME_COLORS.primary}
                              />
                            </TouchableOpacity>
                            <TouchableOpacity
                              style={styles.removeUserButton}
                              onPress={() => handleRemoveUser(item, device.id)}
                            >
                              <MaterialIcons
                                name="delete"
                                size={12}
                                color={THEME_COLORS.error}
                              />
                            </TouchableOpacity>
                          </View>
                        </View>
                      )}
                      keyExtractor={(item) => item.id}
                      horizontal
                      showsHorizontalScrollIndicator={false}
                    />
                  )}
                </View>
              </View>
            ))
          )}
        </View>
      </ScrollView>

      {/* All Modals */}

      {/* Username Modal for Main User */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={usernameModalVisible}
        onRequestClose={() => setUsernameModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View
            style={[
              styles.modalContainer,
              {
                backgroundColor: THEME_COLORS.glassyGreen,
                borderColor: THEME_COLORS.glassyBorder,
                borderWidth: 1,
              },
            ]}
          >
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>SET USERNAME</Text>
              <TouchableOpacity
                onPress={() => setUsernameModalVisible(false)}
                style={styles.closeButton}
              >
                <MaterialIcons
                  name="close"
                  size={24}
                  color={THEME_COLORS.primary}
                />
              </TouchableOpacity>
            </View>

            <TextInput
              style={styles.modalInput}
              placeholder="Enter your name"
              placeholderTextColor={THEME_COLORS.textMuted}
              value={username}
              onChangeText={setUsername}
            />

            <TouchableOpacity
              style={styles.modalButton}
              onPress={captureAndUploadImage}
              disabled={isProcessing}
            >
              <LinearGradient
                colors={THEME_COLORS.glassyGradient}
                style={styles.modalButtonGradient}
              >
                {isProcessing ? (
                  <ActivityIndicator
                    size="small"
                    color={THEME_COLORS.background}
                  />
                ) : (
                  <Text style={styles.modalButtonText}>CAPTURE IMAGE</Text>
                )}
              </LinearGradient>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Edit Main User Modal */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={editMainUserModalVisible}
        onRequestClose={() => setEditMainUserModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View
            style={[
              styles.modalContainer,
              {
                backgroundColor: THEME_COLORS.glassyGreen,
                borderColor: THEME_COLORS.glassyBorder,
                borderWidth: 1,
              },
            ]}
          >
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>EDIT NAME</Text>
              <TouchableOpacity
                onPress={() => setEditMainUserModalVisible(false)}
                style={styles.closeButton}
              >
                <MaterialIcons
                  name="close"
                  size={24}
                  color={THEME_COLORS.primary}
                />
              </TouchableOpacity>
            </View>

            <TextInput
              style={styles.modalInput}
              placeholder="Enter new name"
              placeholderTextColor={THEME_COLORS.textMuted}
              value={newMainUserName}
              onChangeText={setNewMainUserName}
            />

            <TouchableOpacity
              style={styles.modalButton}
              onPress={handleUpdateMainUser}
              disabled={isUpdatingMainUser}
            >
              <LinearGradient
                colors={THEME_COLORS.glassyGradient}
                style={styles.modalButtonGradient}
              >
                {isUpdatingMainUser ? (
                  <ActivityIndicator
                    size="small"
                    color={THEME_COLORS.background}
                  />
                ) : (
                  <Text style={styles.modalButtonText}>UPDATE NAME</Text>
                )}
              </LinearGradient>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Add PEBO Modal */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={modalVisible}
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View
            style={[
              styles.modalContainer,
              {
                backgroundColor: THEME_COLORS.glassyGreen,
                borderColor: THEME_COLORS.glassyBorder,
                borderWidth: 1,
              },
            ]}
          >
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>ADD NEW PEBO</Text>
              <TouchableOpacity
                onPress={() => setModalVisible(false)}
                style={styles.closeButton}
              >
                <MaterialIcons
                  name="close"
                  size={24}
                  color={THEME_COLORS.primary}
                />
              </TouchableOpacity>
            </View>

            <TextInput
              style={styles.modalInput}
              placeholder="PEBO Name"
              placeholderTextColor={THEME_COLORS.textMuted}
              value={peboName}
              onChangeText={setPeboName}
            />

            <TextInput
              style={styles.modalInput}
              placeholder="Location"
              placeholderTextColor={THEME_COLORS.textMuted}
              value={peboLocation}
              onChangeText={setPeboLocation}
            />

            <TouchableOpacity
              style={styles.modalButton}
              onPress={handleAddPebo}
            >
              <LinearGradient
                colors={THEME_COLORS.glassyGradient}
                style={styles.modalButtonGradient}
              >
                <Text style={styles.modalButtonText}>ADD DEVICE</Text>
              </LinearGradient>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Edit PEBO Modal */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={editPeboModalVisible}
        onRequestClose={() => setEditPeboModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View
            style={[
              styles.modalContainer,
              {
                backgroundColor: THEME_COLORS.glassyGreen,
                borderColor: THEME_COLORS.glassyBorder,
                borderWidth: 1,
              },
            ]}
          >
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>EDIT PEBO DEVICE</Text>
              <TouchableOpacity
                onPress={() => setEditPeboModalVisible(false)}
                style={styles.closeButton}
              >
                <MaterialIcons
                  name="close"
                  size={24}
                  color={THEME_COLORS.primary}
                />
              </TouchableOpacity>
            </View>

            <TextInput
              style={styles.modalInput}
              placeholder="PEBO Name"
              placeholderTextColor={THEME_COLORS.textMuted}
              value={editPeboName}
              onChangeText={setEditPeboName}
            />

            <TextInput
              style={styles.modalInput}
              placeholder="Location"
              placeholderTextColor={THEME_COLORS.textMuted}
              value={editPeboLocation}
              onChangeText={setEditPeboLocation}
            />

            <View style={styles.modalButtonRow}>
              <TouchableOpacity
                style={[styles.modalButton, { flex: 1 }]}
                onPress={handleRemovePebo}
                disabled={isRemovingPebo}
              >
                <LinearGradient
                  colors={[THEME_COLORS.error, "#F44336"]}
                  style={styles.modalButtonGradient}
                >
                  {isRemovingPebo ? (
                    <ActivityIndicator
                      size="small"
                      color={THEME_COLORS.textPrimary}
                    />
                  ) : (
                    <Text
                      style={[
                        styles.modalButtonText,
                        { color: THEME_COLORS.textPrimary },
                      ]}
                    >
                      REMOVE
                    </Text>
                  )}
                </LinearGradient>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.modalButton, { flex: 1 }]}
                onPress={handleUpdatePebo}
                disabled={isUpdatingPebo}
              >
                <LinearGradient
                  colors={THEME_COLORS.glassyGradient}
                  style={styles.modalButtonGradient}
                >
                  {isUpdatingPebo ? (
                    <ActivityIndicator
                      size="small"
                      color={THEME_COLORS.background}
                    />
                  ) : (
                    <Text style={styles.modalButtonText}>UPDATE</Text>
                  )}
                </LinearGradient>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Logout Confirmation Modal */}
      <Modal
        animationType="fade"
        transparent={true}
        visible={logoutModalVisible}
        onRequestClose={() => setLogoutModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <LinearGradient
            colors={[THEME_COLORS.cardBackground, THEME_COLORS.background]}
            style={styles.modalContainer}
          >
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>CONFIRM LOGOUT</Text>
              <TouchableOpacity
                onPress={() => setLogoutModalVisible(false)}
                style={styles.closeButton}
              >
                <MaterialIcons
                  name="close"
                  size={24}
                  color={THEME_COLORS.primary}
                />
              </TouchableOpacity>
            </View>

            <Text style={styles.confirmText}>
              Are you sure you want to logout?
            </Text>

            <View style={styles.modalButtonRow}>
              <TouchableOpacity
                style={[styles.modalButton, { flex: 1 }]}
                onPress={() => setLogoutModalVisible(false)}
              >
                <View style={styles.cancelButton}>
                  <Text style={styles.cancelButtonText}>CANCEL</Text>
                </View>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.modalButton, { flex: 1 }]}
                onPress={confirmLogout}
              >
                <LinearGradient
                  colors={[THEME_COLORS.error, "#F44336"]}
                  style={styles.modalButtonGradient}
                >
                  <Text
                    style={[
                      styles.modalButtonText,
                      { color: THEME_COLORS.textPrimary },
                    ]}
                  >
                    LOGOUT
                  </Text>
                </LinearGradient>
              </TouchableOpacity>
            </View>
          </LinearGradient>
        </View>
      </Modal>

      {/* Device Selection Modal for QR */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={deviceSelectionModalVisible}
        onRequestClose={() => setDeviceSelectionModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <LinearGradient
            colors={[THEME_COLORS.cardBackground, THEME_COLORS.background]}
            style={styles.modalContainer}
          >
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>SELECT DEVICE</Text>
              <TouchableOpacity
                onPress={() => setDeviceSelectionModalVisible(false)}
                style={styles.closeButton}
              >
                <MaterialIcons
                  name="close"
                  size={24}
                  color={THEME_COLORS.primary}
                />
              </TouchableOpacity>
            </View>

            <Text style={styles.deviceSelectionSubtitle}>
              Select a PEBO device to generate QR code for Wi-Fi setup
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

      {/* QR Code Modal */}
      <Modal
        animationType="fade"
        transparent={true}
        visible={qrModalVisible}
        onRequestClose={() => setQrModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <LinearGradient
            colors={[THEME_COLORS.cardBackground, THEME_COLORS.background]}
            style={styles.modalContainer}
          >
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>QR CODE</Text>
              <TouchableOpacity
                onPress={() => setQrModalVisible(false)}
                style={styles.closeButton}
              >
                <MaterialIcons
                  name="close"
                  size={24}
                  color={THEME_COLORS.primary}
                />
              </TouchableOpacity>
            </View>

            {selectedDeviceForQR && (
              <View style={styles.selectedDeviceInfo}>
                <Text style={styles.selectedDeviceTitle}>SELECTED DEVICE</Text>
                <Text style={styles.selectedDeviceName}>
                  {selectedDeviceForQR.name}
                </Text>
                <Text style={styles.selectedDeviceLocation}>
                  {selectedDeviceForQR.location}
                </Text>
              </View>
            )}

            <View style={styles.qrCodeContainer}>
              <QRCode
                value={generateQrCodeValue()}
                size={300} // enlarged size
                color={THEME_COLORS.background}
                backgroundColor={THEME_COLORS.textPrimary}
              />
            </View>

            <Text style={styles.qrSubtitle}>
              Scan this QR code with your PEBO device to configure Wi-Fi
              settings
            </Text>
          </LinearGradient>
        </View>
      </Modal>

      {/* Add Secondary User Modal */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={addUserModalVisible}
        onRequestClose={() => setAddUserModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <LinearGradient
            colors={[THEME_COLORS.cardBackground, THEME_COLORS.background]}
            style={styles.modalContainer}
          >
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>ADD USER</Text>
              <TouchableOpacity
                onPress={() => setAddUserModalVisible(false)}
                style={styles.closeButton}
              >
                <MaterialIcons
                  name="close"
                  size={24}
                  color={THEME_COLORS.primary}
                />
              </TouchableOpacity>
            </View>

            <TextInput
              style={styles.modalInput}
              placeholder="User Name"
              placeholderTextColor={THEME_COLORS.textMuted}
              value={newUserName}
              onChangeText={setNewUserName}
            />

            <TouchableOpacity
              style={styles.modalButton}
              onPress={handleAddSecondaryUser}
              disabled={isAddingUser}
            >
              <LinearGradient
                colors={THEME_COLORS.glassyGradient}
                style={styles.modalButtonGradient}
              >
                {isAddingUser ? (
                  <ActivityIndicator
                    size="small"
                    color={THEME_COLORS.background}
                  />
                ) : (
                  <Text style={styles.modalButtonText}>ADD USER</Text>
                )}
              </LinearGradient>
            </TouchableOpacity>
          </LinearGradient>
        </View>
      </Modal>

      {/* Edit Secondary User Modal */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={editUserModalVisible}
        onRequestClose={() => setEditUserModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <LinearGradient
            colors={[THEME_COLORS.cardBackground, THEME_COLORS.background]}
            style={styles.modalContainer}
          >
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>EDIT USER</Text>
              <TouchableOpacity
                onPress={() => setEditUserModalVisible(false)}
                style={styles.closeButton}
              >
                <MaterialIcons
                  name="close"
                  size={24}
                  color={THEME_COLORS.primary}
                />
              </TouchableOpacity>
            </View>

            <TextInput
              style={styles.modalInput}
              placeholder="User Name"
              placeholderTextColor={THEME_COLORS.textMuted}
              value={editUserName}
              onChangeText={setEditUserName}
            />

            <TouchableOpacity
              style={styles.modalButton}
              onPress={handleUpdateUser}
              disabled={isUpdatingUser}
            >
              <LinearGradient
                colors={THEME_COLORS.glassyGradient}
                style={styles.modalButtonGradient}
              >
                {isUpdatingUser ? (
                  <ActivityIndicator
                    size="small"
                    color={THEME_COLORS.background}
                  />
                ) : (
                  <Text style={styles.modalButtonText}>UPDATE USER</Text>
                )}
              </LinearGradient>
            </TouchableOpacity>
          </LinearGradient>
        </View>
      </Modal>

      {/* Remove Secondary User Confirmation Modal */}
      <Modal
        animationType="fade"
        transparent={true}
        visible={removeUserModalVisible}
        onRequestClose={() => setRemoveUserModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <LinearGradient
            colors={[THEME_COLORS.cardBackground, THEME_COLORS.background]}
            style={styles.modalContainer}
          >
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>CONFIRM REMOVAL</Text>
              <TouchableOpacity
                onPress={() => setRemoveUserModalVisible(false)}
                style={styles.closeButton}
              >
                <MaterialIcons
                  name="close"
                  size={24}
                  color={THEME_COLORS.primary}
                />
              </TouchableOpacity>
            </View>

            <Text style={styles.confirmText}>
              Are you sure you want to remove this user? This action cannot be
              undone.
            </Text>

            <View style={styles.modalButtonRow}>
              <TouchableOpacity
                style={[styles.modalButton, { flex: 1 }]}
                onPress={() => setRemoveUserModalVisible(false)}
              >
                <View style={styles.cancelButton}>
                  <Text style={styles.cancelButtonText}>CANCEL</Text>
                </View>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.modalButton, { flex: 1 }]}
                onPress={confirmRemoveUser}
                disabled={isRemovingUser}
              >
                <LinearGradient
                  colors={[THEME_COLORS.error, "#F44336"]}
                  style={styles.modalButtonGradient}
                >
                  {isRemovingUser ? (
                    <ActivityIndicator
                      size="small"
                      color={THEME_COLORS.textPrimary}
                    />
                  ) : (
                    <Text
                      style={[
                        styles.modalButtonText,
                        { color: THEME_COLORS.textPrimary },
                      ]}
                    >
                      REMOVE
                    </Text>
                  )}
                </LinearGradient>
              </TouchableOpacity>
            </View>
          </LinearGradient>
        </View>
      </Modal>

      {/* Username Modal for Main User */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={usernameModalVisible}
        onRequestClose={() => setUsernameModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <LinearGradient
            colors={[THEME_COLORS.cardBackground, THEME_COLORS.background]}
            style={styles.modalContainer}
          >
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>SET USERNAME</Text>
              <TouchableOpacity
                onPress={() => setUsernameModalVisible(false)}
                style={styles.closeButton}
              >
                <MaterialIcons
                  name="close"
                  size={24}
                  color={THEME_COLORS.primary}
                />
              </TouchableOpacity>
            </View>

            <TextInput
              style={styles.modalInput}
              placeholder="Enter your name"
              placeholderTextColor={THEME_COLORS.textMuted}
              value={username}
              onChangeText={setUsername}
            />

            <TouchableOpacity
              style={styles.modalButton}
              onPress={captureAndUploadImage}
              disabled={isProcessing}
            >
              <LinearGradient
                colors={THEME_COLORS.glassyGradient}
                style={styles.modalButtonGradient}
              >
                {isProcessing ? (
                  <ActivityIndicator
                    size="small"
                    color={THEME_COLORS.background}
                  />
                ) : (
                  <Text style={styles.modalButtonText}>CAPTURE IMAGE</Text>
                )}
              </LinearGradient>
            </TouchableOpacity>
          </LinearGradient>
        </View>
      </Modal>

      {/* Edit Main User Modal */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={editMainUserModalVisible}
        onRequestClose={() => setEditMainUserModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <LinearGradient
            colors={[THEME_COLORS.cardBackground, THEME_COLORS.background]}
            style={styles.modalContainer}
          >
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>EDIT NAME</Text>
              <TouchableOpacity
                onPress={() => setEditMainUserModalVisible(false)}
                style={styles.closeButton}
              >
                <MaterialIcons
                  name="close"
                  size={24}
                  color={THEME_COLORS.primary}
                />
              </TouchableOpacity>
            </View>

            <TextInput
              style={styles.modalInput}
              placeholder="Enter new name"
              placeholderTextColor={THEME_COLORS.textMuted}
              value={newMainUserName}
              onChangeText={setNewMainUserName}
            />

            <TouchableOpacity
              style={styles.modalButton}
              onPress={handleUpdateMainUser}
              disabled={isUpdatingMainUser}
            >
              <LinearGradient
                colors={THEME_COLORS.glassyGradient}
                style={styles.modalButtonGradient}
              >
                {isUpdatingMainUser ? (
                  <ActivityIndicator
                    size="small"
                    color={THEME_COLORS.background}
                  />
                ) : (
                  <Text style={styles.modalButtonText}>UPDATE NAME</Text>
                )}
              </LinearGradient>
            </TouchableOpacity>
          </LinearGradient>
        </View>
      </Modal>

      {/* Image Viewer Modal */}
      <Modal
        animationType="fade"
        transparent={true}
        visible={imageViewerVisible}
        onRequestClose={() => setImageViewerVisible(false)}
      >
        <View style={styles.imageViewerOverlay}>
          <TouchableOpacity
            style={styles.closeImageButton}
            onPress={() => setImageViewerVisible(false)}
          >
            <MaterialIcons
              name="close"
              size={24}
              color={THEME_COLORS.primary}
            />
          </TouchableOpacity>

          <View style={styles.imageViewerContent}>
            <Text style={styles.imageViewerTitle}>{selectedImageTitle}</Text>
            {selectedImage && (
              <Image
                source={{ uri: selectedImage }}
                style={styles.fullscreenImage}
                resizeMode="contain"
                onError={(e) =>
                  handleImageError(e.nativeEvent.error, "fullscreen")
                }
              />
            )}
          </View>
        </View>
      </Modal>
      <Modal
        animationType="fade"
        transparent={true}
        visible={removeModalVisible}
        onRequestClose={() => setRemoveModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <LinearGradient
            colors={[THEME_COLORS.cardBackground, THEME_COLORS.background]}
            style={styles.modalContainer}
          >
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>CONFIRM REMOVAL</Text>
              <TouchableOpacity
                onPress={() => setRemoveModalVisible(false)}
                style={styles.closeButton}
              >
                <MaterialIcons
                  name="close"
                  size={24}
                  color={THEME_COLORS.primary}
                />
              </TouchableOpacity>
            </View>

            <Text style={styles.confirmText}>
              Are you sure you want to remove this PEBO device? This cannot be
              undone.
            </Text>

            <View style={styles.modalButtonRow}>
              <TouchableOpacity
                style={[styles.modalButton, { flex: 1 }]}
                onPress={() => setRemoveModalVisible(false)}
              >
                <View style={styles.cancelButton}>
                  <Text style={styles.cancelButtonText}>CANCEL</Text>
                </View>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.modalButton, { flex: 1 }]}
                onPress={confirmRemovePebo}
                disabled={isRemovingPebo}
              >
                <LinearGradient
                  colors={[THEME_COLORS.error, "#F44336"]}
                  style={styles.modalButtonGradient}
                >
                  {isRemovingPebo ? (
                    <ActivityIndicator
                      size="small"
                      color={THEME_COLORS.textPrimary}
                    />
                  ) : (
                    <Text
                      style={[
                        styles.modalButtonText,
                        { color: THEME_COLORS.textPrimary },
                      ]}
                    >
                      REMOVE
                    </Text>
                  )}
                </LinearGradient>
              </TouchableOpacity>
            </View>
          </LinearGradient>
        </View>
      </Modal>

      {/* PopupModal component */}
      <PopupModal
        visible={popupVisible}
        onClose={() => setPopupVisible(false)}
        title={popupContent.title}
        message={popupContent.message}
        icon={popupContent.icon}
        theme={THEME_COLORS}
      />
    </View>
  );
};

// Complete StyleSheet (remaining styles)
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: THEME_COLORS.background,
  },
  backgroundContainer: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 0,
  },
  pulseOrb1: {
    position: "absolute",
    top: 150,
    left: 30,
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: THEME_COLORS.glow,
  },
  pulseOrb2: {
    position: "absolute",
    top: 300,
    right: 80,
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "rgba(255, 82, 82, 0.2)",
  },
  floatingParticle1: {
    position: "absolute",
    top: 200,
    left: 100,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: THEME_COLORS.primary,
  },
  floatingParticle2: {
    position: "absolute",
    top: 250,
    right: 120,
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: THEME_COLORS.error,
  },
  gridLines: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderWidth: 1,
    borderColor: THEME_COLORS.cardBorder,
    borderStyle: "dotted",
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
  backButton: {
    padding: 8,
  },
  headerText: {
    fontSize: 24,
    fontWeight: "900",
    color: THEME_COLORS.textPrimary,
    letterSpacing: 2,
    textShadowColor: THEME_COLORS.primary,
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 10,
  },
  logoutButton: {
    padding: 8,
  },
  scrollView: {
    flex: 1,
    zIndex: 1,
  },
  scrollContent: {
    padding: 24,
  },
  profileSection: {
    alignItems: "center",
    marginBottom: 32,
    padding: 20,
    borderRadius: 16,
    backgroundColor: THEME_COLORS.cardBackground,
    borderWidth: 1,
    borderColor: THEME_COLORS.cardBorder,
    shadowColor: THEME_COLORS.primary,
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 20,
  },
  profileImageContainer: {
    position: "relative",
    marginBottom: 15,
  },
  profileGlow: {
    position: "absolute",
    top: -10,
    left: -10,
    right: -10,
    bottom: -10,
    borderRadius: 60,
    backgroundColor: THEME_COLORS.glow,
    zIndex: 0,
  },
  profileImage: {
    width: 100,
    height: 100,
    borderRadius: 50,
    borderWidth: 2,
    borderColor: THEME_COLORS.primary,
    zIndex: 1,
  },
  placeholderImage: {
    width: 100,
    height: 100,
    borderRadius: 50,
    borderWidth: 2,
    borderColor: THEME_COLORS.primary,
    backgroundColor: THEME_COLORS.cardBackground,
    justifyContent: "center",
    alignItems: "center",
    zIndex: 1,
  },
  cameraButton: {
    position: "absolute",
    bottom: 0,
    right: 0,
    backgroundColor: THEME_COLORS.primary,
    borderRadius: 15,
    width: 30,
    height: 30,
    justifyContent: "center",
    alignItems: "center",
    zIndex: 2,
  },
  nameSection: {
    flexDirection: "row",
    alignItems: "center",
  },
  profileName: {
    color: THEME_COLORS.textPrimary,
    fontSize: 24,
    fontWeight: "bold",
    marginRight: 10,
    textShadowColor: THEME_COLORS.primary,
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 5,
  },
  editButton: {
    padding: 8,
  },
  section: {
    marginBottom: 32,
  },
  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: THEME_COLORS.textPrimary,
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  addButton: {
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: THEME_COLORS.cardBorder,
    backgroundColor: THEME_COLORS.cardBackground,
  },
  cardContainer: {
    borderRadius: 16,
    padding: 20,
    backgroundColor: THEME_COLORS.cardBackground,
    borderWidth: 1,
    borderColor: THEME_COLORS.cardBorder,
  },
  inputGroup: {
    marginBottom: 20,
  },
  input: {
    backgroundColor: THEME_COLORS.inputBackground,
    borderRadius: 12,
    padding: 16,
    color: THEME_COLORS.textPrimary,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: THEME_COLORS.inputBorder,
    fontSize: 16,
  },
  passwordContainer: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: THEME_COLORS.inputBackground,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: THEME_COLORS.inputBorder,
  },
  eyeButton: {
    padding: 16,
  },
  buttonRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 12,
  },
  button: {
    flex: 1,
    borderRadius: 12,
    overflow: "hidden",
  },
  saveButton: {
    // Gradient applied inside
  },
  qrButton: {
    backgroundColor: THEME_COLORS.inputBackground,
    borderWidth: 1,
    borderColor: THEME_COLORS.inputBorder,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 16,
  },
  buttonGradient: {
    paddingVertical: 16,
    paddingHorizontal: 20,
    alignItems: "center",
    justifyContent: "center",
  },
  buttonText: {
    color: THEME_COLORS.background,
    fontSize: 18,
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  emptyContainer: {
    padding: 40,
    alignItems: "center",
    borderRadius: 16,
    backgroundColor: THEME_COLORS.cardBackground,
    borderWidth: 1,
    borderColor: THEME_COLORS.cardBorder,
  },
  emptyText: {
    color: THEME_COLORS.textMuted,
    fontSize: 16,
    fontStyle: "italic",
    textAlign: "center",
  },
  deviceCard: {
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    backgroundColor: THEME_COLORS.cardBackground,
    borderWidth: 1,
    borderColor: THEME_COLORS.cardBorder,
  },
  deviceHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
  },
  deviceInfo: {
    flex: 1,
  },
  deviceName: {
    color: THEME_COLORS.textPrimary,
    fontSize: 18,
    fontWeight: "600",
    marginBottom: 4,
  },
  deviceLocation: {
    color: THEME_COLORS.textSecondary,
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  deviceActions: {
    flexDirection: "row",
    gap: 12,
  },
  addUserButton: {
    backgroundColor: THEME_COLORS.primary,
    borderRadius: 12,
    width: 40,
    height: 40,
    justifyContent: "center",
    alignItems: "center",
  },
  editDeviceButton: {
    backgroundColor: THEME_COLORS.inputBackground,
    borderRadius: 12,
    width: 40,
    height: 40,
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: THEME_COLORS.inputBorder,
  },
  deviceUsers: {
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: THEME_COLORS.cardBorder,
  },
  noUsersText: {
    color: THEME_COLORS.textMuted,
    fontStyle: "italic",
    textAlign: "center",
    fontSize: 14,
  },
  secondaryUserCard: {
    alignItems: "center",
    marginRight: 20,
    padding: 8,
    position: "relative",
  },
  secondaryUserImageContainer: {
    position: "relative",
    marginBottom: 8,
  },
  secondaryUserImage: {
    width: 60,
    height: 60,
    borderRadius: 30,
    borderWidth: 2,
    borderColor: THEME_COLORS.primary,
  },
  placeholderSecondaryImage: {
    backgroundColor: THEME_COLORS.cardBackground,
    justifyContent: "center",
    alignItems: "center",
  },
  secondaryCameraButton: {
    position: "absolute",
    bottom: -4,
    right: -4,
    backgroundColor: THEME_COLORS.primary,
    borderRadius: 10,
    width: 20,
    height: 20,
    justifyContent: "center",
    alignItems: "center",
    zIndex: 2,
  },
  secondaryUserName: {
    color: THEME_COLORS.textPrimary,
    fontSize: 12,
    fontWeight: "500",
    textAlign: "center",
    maxWidth: 60,
  },
  userActions: {
    flexDirection: "row",
    justifyContent: "center",
    marginTop: 4,
    gap: 8,
  },
  editUserButton: {
    backgroundColor: THEME_COLORS.inputBackground,
    borderRadius: 8,
    width: 20,
    height: 20,
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: THEME_COLORS.inputBorder,
  },
  removeUserButton: {
    backgroundColor: THEME_COLORS.inputBackground,
    borderRadius: 8,
    width: 20,
    height: 20,
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(255, 82, 82, 0.3)",
  },

  // Modal Styles
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.8)",
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  modalContainer: {
    width: "100%",
    maxWidth: 400,
    borderRadius: 16,
    padding: 24,
    maxHeight: height * 0.8,
  },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 24,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: THEME_COLORS.textPrimary,
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  closeButton: {
    padding: 8,
  },
  modalInput: {
    backgroundColor: THEME_COLORS.inputBackground,
    borderRadius: 12,
    padding: 16,
    color: THEME_COLORS.textPrimary,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: THEME_COLORS.inputBorder,
    fontSize: 16,
  },
  modalButton: {
    borderRadius: 12,
    overflow: "hidden",
    marginTop: 8,
  },
  modalButtonGradient: {
    paddingVertical: 16,
    paddingHorizontal: 20,
    alignItems: "center",
    justifyContent: "center",
  },
  modalButtonText: {
    color: THEME_COLORS.background,
    fontSize: 16,
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  modalButtonRow: {
    flexDirection: "row",
    gap: 12,
    marginTop: 16,
  },
  confirmText: {
    color: THEME_COLORS.textPrimary,
    fontSize: 16,
    textAlign: "center",
    marginBottom: 8,
    lineHeight: 24,
  },
  cancelButton: {
    backgroundColor: THEME_COLORS.inputBackground,
    borderWidth: 1,
    borderColor: THEME_COLORS.inputBorder,
    borderRadius: 12,
    paddingVertical: 16,
    paddingHorizontal: 20,
    alignItems: "center",
    justifyContent: "center",
  },
  cancelButtonText: {
    color: THEME_COLORS.primary,
    fontSize: 16,
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
  },

  // Device Selection Modal Styles
  deviceSelectionSubtitle: {
    color: THEME_COLORS.textSecondary,
    fontSize: 14,
    textAlign: "center",
    marginBottom: 20,
    lineHeight: 20,
  },
  deviceSelectionList: {
    maxHeight: 300,
  },
  deviceSelectionCard: {
    marginBottom: 12,
    borderRadius: 12,
    overflow: "hidden",
  },
  deviceSelectionCardInner: {
    padding: 16,
    flexDirection: "row",
    alignItems: "center",
  },
  deviceIcon: {
    marginRight: 16,
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: THEME_COLORS.glow,
    justifyContent: "center",
    alignItems: "center",
  },
  selectedDeviceInfo: {
    backgroundColor: THEME_COLORS.glow,
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: THEME_COLORS.inputBorder,
  },
  selectedDeviceTitle: {
    color: THEME_COLORS.primary,
    fontSize: 12,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: 4,
  },
  selectedDeviceName: {
    color: THEME_COLORS.textPrimary,
    fontSize: 18,
    fontWeight: "600",
    marginBottom: 4,
  },
  selectedDeviceLocation: {
    color: THEME_COLORS.textSecondary,
    fontSize: 14,
    textTransform: "uppercase",
    letterSpacing: 1,
  },

  // QR Code Modal Styles
  qrCodeContainer: {
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: THEME_COLORS.textPrimary,
    borderRadius: 16,
    padding: 30, // previously 20
    marginVertical: 30, // add more vertical space
    shadowColor: THEME_COLORS.primary,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 10,
  },

  qrSubtitle: {
    color: THEME_COLORS.textSecondary,
    fontSize: 14,
    textAlign: "center",
    lineHeight: 20,
    marginTop: 16,
  },

  // Image Viewer Modal Styles
  imageViewerOverlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.95)",
    justifyContent: "center",
    alignItems: "center",
  },
  closeImageButton: {
    position: "absolute",
    top: 60,
    right: 24,
    zIndex: 10,
    backgroundColor: THEME_COLORS.cardBackground,
    borderRadius: 20,
    width: 40,
    height: 40,
    justifyContent: "center",
    alignItems: "center",
  },
  imageViewerContent: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  imageViewerTitle: {
    color: THEME_COLORS.textPrimary,
    fontSize: 20,
    fontWeight: "600",
    marginBottom: 20,
    textAlign: "center",
  },
  fullscreenImage: {
    width: width - 48,
    height: height - 200,
    borderRadius: 16,
    borderWidth: 2,
    borderColor: THEME_COLORS.primary,
  },
});

export default SettingsScreen;

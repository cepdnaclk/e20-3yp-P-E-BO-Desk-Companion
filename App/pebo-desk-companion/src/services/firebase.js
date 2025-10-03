import firebase from "firebase/compat/app";
import "firebase/compat/auth";
import "firebase/compat/database";
import { onAuthStateChanged } from "firebase/auth";
import {
  getStorage,
  ref as storageRef,
  uploadBytes,
  getDownloadURL,
  deleteObject,
} from "firebase/storage";

// Firebase Configuration
const firebaseConfig = {
  apiKey: "AIzaSyA2ZcQrnmrsisUCjywsfEYn4pR69PZCrpE",
  authDomain: "pebo-task-manager-767f3.firebaseapp.com",
  databaseURL:
    "https://pebo-task-manager-767f3-default-rtdb.asia-southeast1.firebasedatabase.app",
  projectId: "pebo-task-manager-767f3",
  storageBucket: "pebo-task-manager-767f3.appspot.com",
  messagingSenderId: "646915822892",
  appId: "1:646915822892:web:d8d472bac0f750a1554889",
};

// Initialize Firebase
if (!firebase.apps.length) {
  firebase.initializeApp(firebaseConfig);
}

export const auth = firebase.auth();
export const db = firebase.database();

// ------------------ 🔐 AUTH ------------------ //
export const logout = () => auth.signOut();

export const getUserName = () => {
  const user = auth.currentUser;
  if (user && user.displayName) {
    return user.displayName;
  } else {
    return "Guest";
  }
};

// ------------------ ✅ TASKS ------------------ //
export const addTask = async (task) => {
  const user = auth.currentUser;
  if (!user) return false;

  const newRef = db.ref(`users/${user.uid}/tasks`).push();
  await newRef.set({ ...task, id: newRef.key });
  return true;
};
// Add this to your firebase.js file
export const deleteTask = async (taskId) => {
  const user = auth.currentUser;
  if (!user) return false;
  
  try {
    await db.ref(`users/${user.uid}/tasks/${taskId}`).remove();
    return true;
  } catch (error) {
    console.error("Error deleting task:", error);
    return false;
  }
};

export const getTaskOverview = async () => {
  const user = auth.currentUser;
  if (!user) return [];

  const snapshot = await db.ref(`users/${user.uid}/tasks`).once("value");
  const val = snapshot.val();
  if (!val || typeof val !== "object") return [];
  return Object.values(val);
};

export const updateTask = async (taskId, updates) => {
  const user = auth.currentUser;
  if (!user) return false;

  await db.ref(`users/${user.uid}/tasks/${taskId}`).update(updates);
  return true;
};

// ------------------ 🧠 PEBO DEVICES ------------------ //
// ------------------ 🧠 PEBO DEVICES ------------------ //
export const addPeboDevice = async ({ name, location }) => {
  const user = auth.currentUser;
  if (!user) return null;

  const deviceRef = db.ref(`users/${user.uid}/peboDevices`).push();
  await deviceRef.set({
    name,
    location,
    online: false,
    createdAt: Date.now(),
  });

  return deviceRef.key;
};

export const updatePeboDevice = async (deviceId, updates) => {
  const user = auth.currentUser;
  if (!user) return false;
  
  try {
    await db.ref(`users/${user.uid}/peboDevices/${deviceId}`).update({
      ...updates,
      updatedAt: Date.now(),
    });
    return true;
  } catch (error) {
    console.error("Error updating PEBO device:", error);
    return false;
  }
};

// ✅ FIXED: Enhanced removePeboDevice function
// Fixed removePeboDevice function that properly throws errors
export const removePeboDevice = async (deviceId) => {
  const user = auth.currentUser;
  if (!user) {
    console.error("No authenticated user");
    throw new Error("No authenticated user");
  }
  
  if (!deviceId) {
    console.error("No device ID provided");
    throw new Error("No device ID provided");
  }

  try {
    console.log(`Attempting to remove device: ${deviceId} for user: ${user.uid}`);
    
    // First, check if the device exists
    const deviceSnapshot = await db.ref(`users/${user.uid}/peboDevices/${deviceId}`).once('value');
    if (!deviceSnapshot.exists()) {
      console.warn(`Device ${deviceId} not found in user's devices`);
      throw new Error(`Device ${deviceId} not found`);
    }

    // Remove from user's devices collection
    await db.ref(`users/${user.uid}/peboDevices/${deviceId}`).remove();
    console.log(`Successfully removed device ${deviceId} from user's collection`);
    
    // Optional: Remove from global devices collection if it exists
    try {
      const globalDeviceSnapshot = await db.ref(`devices/${deviceId}`).once('value');
      if (globalDeviceSnapshot.exists()) {
        await db.ref(`devices/${deviceId}`).remove();
        console.log(`Successfully removed device ${deviceId} from global collection`);
      }
    } catch (globalError) {
      console.warn("Could not remove from global devices collection:", globalError);
      // Don't fail the operation if global removal fails
    }
    
    console.log(`Device ${deviceId} successfully removed`);
    return true;
  } catch (error) {
    console.error("Error removing PEBO device:", error);
    throw new Error(`Failed to remove device: ${error.message}`);
  }
};


export const getPeboDevices = async () => {
  const user = auth.currentUser;
  if (!user) return [];

  try {
    const snapshot = await db.ref(`users/${user.uid}/peboDevices`).once("value");
    const devices = [];

    if (snapshot.exists()) {
      snapshot.forEach((child) => {
        devices.push({ 
          id: child.key, 
          ...child.val(),
          // Ensure these properties have default values
          name: child.val().name || `Device ${child.key}`,
          location: child.val().location || "Unknown Location",
          online: child.val().online || false,
          createdAt: child.val().createdAt || Date.now()
        });
      });
    }

    return devices;
  } catch (error) {
    console.error("Error fetching PEBO devices:", error);
    return [];
  }
};


// ------------------ 📶 WIFI SETTINGS ------------------ //
export const saveWifiSettings = async (settings) => {
  const user = auth.currentUser;
  if (!user) return false;

  await db.ref(`users/${user.uid}/settings`).set(settings);
  return true;
};

export const getWifiName = async () => {
  const user = auth.currentUser;
  if (!user) {
    return {
      peboName: "Unknown PEBO",
      wifiSSID: "N/A",
      wifiPassword: "N/A",
    };
  }

  const snapshot = await db.ref(`users/${user.uid}/settings`).once("value");
  const data = snapshot.val();

  return {
    peboName: data?.peboName || "Unknown PEBO",
    wifiSSID: data?.wifiSSID || "N/A",
    wifiPassword: data?.wifiPassword || "N/A",
  };
};

// ------------------ 🪣 S3 CONFIGURATION ------------------ //
export const saveS3Config = async (config) => {
  const user = auth.currentUser;
  if (!user) return false;

  const { accessKey, secretKey, bucketName } = config;

  await db.ref(`users/${user.uid}/s3Config`).set({
    accessKey,
    secretKey,
    bucketName,
    updatedAt: new Date().toISOString(),
  });

  return true;
};

export const getS3Config = async () => {
  const user = auth.currentUser;
  if (!user) return {};

  const snapshot = await db.ref(`users/${user.uid}/s3Config`).once("value");
  return snapshot.val() || {};
};

// ------------------ 👤 USER PROFILE IMAGE ------------------ //
export const uploadUserProfileImage = async (imageUri, username) => {
  const user = auth.currentUser;
  if (!user || !username || !imageUri) return null;

  // Sanitize username for safe filename
  const sanitizedUsername = username
    .replace(/[^a-zA-Z0-9]/g, "_")
    .toLowerCase();
  const imageName = `user_${sanitizedUsername}.jpg`;
  const storage = getStorage();
  const imageRef = storageRef(storage, `userImages/${imageName}`);

  try {
    const response = await fetch(imageUri);
    const blob = await response.blob();

    await uploadBytes(imageRef, blob);
    const downloadURL = await getDownloadURL(imageRef);

    // Save the download URL in the Realtime Database
    await db.ref(`users/${user.uid}/profileImage`).set(downloadURL);
    await db.ref(`users/${user.uid}/imageHistory`).push({
      url: downloadURL,
      timestamp: new Date().toISOString(),
      path: `userImages/${imageName}`,
    });

    return downloadURL;
  } catch (error) {
    console.error("Upload error:", error);
    return null;
  }
};

export const getUserProfileImage = async () => {
  const user = auth.currentUser;
  if (!user) return null;

  const snapshot = await db.ref(`users/${user.uid}/profileImage`).once("value");
  return snapshot.val() || null;
};

export const getUserImageHistory = async () => {
  const user = auth.currentUser;
  if (!user) return [];

  const snapshot = await db.ref(`users/${user.uid}/imageHistory`).once("value");
  const data = snapshot.val() || {};

  return Object.entries(data)
    .map(([key, value]) => ({ id: key, ...value }))
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
};

export const deleteUserImage = async (imageId) => {
  const user = auth.currentUser;
  if (!user) return false;

  const imageSnap = await db
    .ref(`users/${user.uid}/imageHistory/${imageId}`)
    .once("value");
  const imageData = imageSnap.val();
  if (!imageData) return false;

  if (imageData.path) {
    const storage = getStorage();
    try {
      await deleteObject(storageRef(storage, imageData.path));
    } catch (err) {
      console.warn("Image file could not be deleted:", err);
    }
  }

  await db.ref(`users/${user.uid}/imageHistory/${imageId}`).remove();

  const profileSnap = await db
    .ref(`users/${user.uid}/profileImage`)
    .once("value");
  if (profileSnap.val() === imageData.url) {
    await db.ref(`users/${user.uid}/profileImage`).remove();
  }

  return true;
};

export const setProfileImageFromHistory = async (imageId) => {
  const user = auth.currentUser;
  if (!user) return false;

  const snapshot = await db
    .ref(`users/${user.uid}/imageHistory/${imageId}`)
    .once("value");
  const imageData = snapshot.val();
  if (!imageData) return false;

  await db.ref(`users/${user.uid}/profileImage`).set(imageData.url);
  return true;
};

// Optional: Firestore doc retrieval
// (comment out if unused)
export const getUserDocument = async () => {
  try {
    const user = auth.currentUser;
    if (!user) return null;

    const userDocRef = doc(db, "users", user.uid);
    const userDoc = await getDoc(userDocRef);

    if (userDoc.exists()) {
      return userDoc.data();
    } else {
      return null;
    }
  } catch (error) {
    console.error("Error fetching user document:", error);
    return null;
  }
};

// ------------------ 👀 AUTH LISTENER ------------------ //
onAuthStateChanged(auth, (user) => {
  if (user) {
    console.log("User signed in:", user.displayName);
  } else {
    console.log("User signed out.");
    // Optional:
    // navigate("/login"); // For web apps
    // or
    // navigation.reset({ index: 0, routes: [{ name: "Login" }] }); // React Native
  }
});

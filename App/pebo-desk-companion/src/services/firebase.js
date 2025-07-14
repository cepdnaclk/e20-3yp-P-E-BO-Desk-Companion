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
  if (!user) throw new Error("User not authenticated");

  const newRef = db.ref(`users/${user.uid}/tasks`).push();
  await newRef.set({ ...task, id: newRef.key });
  return true;
};

export const getTaskOverview = async () => {
  const user = auth.currentUser;
  if (!user) throw new Error("User not authenticated");

  const snapshot = await db.ref(`users/${user.uid}/tasks`).once("value");
  const val = snapshot.val();
  if (!val || typeof val !== "object") return [];
  return Object.values(val);
};

export const updateTask = async (taskId, updates) => {
  const user = auth.currentUser;
  if (!user) throw new Error("User not authenticated");

  await db.ref(`users/${user.uid}/tasks/${taskId}`).update(updates);
  return true;
};

// ------------------ 🧠 PEBO DEVICES ------------------ //
export const addPeboDevice = async ({ name, location }) => {
  const user = auth.currentUser;
  if (!user) throw new Error("User not authenticated");

  const deviceRef = db.ref(`users/${user.uid}/peboDevices`).push();
  await deviceRef.set({
    name,
    location,
    createdAt: Date.now(),
  });

  return deviceRef.key;
};

export const getPeboDevices = async () => {
  const user = auth.currentUser;
  if (!user) throw new Error("User not authenticated");

  const snapshot = await db.ref(`users/${user.uid}/peboDevices`).once("value");
  const devices = [];

  snapshot.forEach((child) => {
    devices.push({ id: child.key, ...child.val() });
  });

  return devices;
};

// ------------------ 📶 WIFI SETTINGS ------------------ //
export const saveWifiSettings = async (settings) => {
  const user = auth.currentUser;
  if (!user) throw new Error("User not authenticated");

  await db.ref(`users/${user.uid}/settings`).set(settings);
  return true;
};

export const getWifiName = async () => {
  const user = auth.currentUser;
  if (!user) throw new Error("User not authenticated");

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
  if (!user) throw new Error("User not authenticated");

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
  if (!user) throw new Error("User not authenticated");

  const snapshot = await db.ref(`users/${user.uid}/s3Config`).once("value");
  return snapshot.val() || {};
};

// ------------------ 👤 USER PROFILE IMAGE ------------------ //
export const uploadUserProfileImage = async (imageUri, username) => {
  const user = auth.currentUser;
  if (!user) throw new Error("User not authenticated");
  if (!username) throw new Error("Username is required");

  // Sanitize username for safe filename
  const sanitizedUsername = username
    .replace(/[^a-zA-Z0-9]/g, "_")
    .toLowerCase();
  const imageName = `user_${sanitizedUsername}.jpg`;
  const storage = getStorage();
  const imageRef = storageRef(storage, `userImages/${imageName}`);

  const response = await fetch(imageUri);
  const blob = await response.blob();

  try {
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
    throw error;
  }
};
// Add this function to your Firebase utilities file
export const getUserDocument = async () => {
  try {
    const user = auth.currentUser;
    if (!user) {
      throw new Error("No authenticated user");
    }

    const userDocRef = doc(db, "users", user.uid);
    const userDoc = await getDoc(userDocRef);
    
    if (userDoc.exists()) {
      return userDoc.data();
    } else {
      throw new Error("User document not found");
    }
  } catch (error) {
    console.error("Error fetching user document:", error);
    throw error;
  }
};

export const getUserProfileImage = async () => {
  const user = auth.currentUser;
  if (!user) throw new Error("User not authenticated");

  const snapshot = await db.ref(`users/${user.uid}/profileImage`).once("value");
  return snapshot.val() || null;
};

export const getUserImageHistory = async () => {
  const user = auth.currentUser;
  if (!user) throw new Error("User not authenticated");

  const snapshot = await db.ref(`users/${user.uid}/imageHistory`).once("value");
  const data = snapshot.val() || {};

  return Object.entries(data)
    .map(([key, value]) => ({ id: key, ...value }))
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
};

export const deleteUserImage = async (imageId) => {
  const user = auth.currentUser;
  if (!user) throw new Error("User not authenticated");

  const imageSnap = await db
    .ref(`users/${user.uid}/imageHistory/${imageId}`)
    .once("value");
  const imageData = imageSnap.val();
  if (!imageData) throw new Error("Image not found");

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
  if (!user) throw new Error("User not authenticated");

  const snapshot = await db
    .ref(`users/${user.uid}/imageHistory/${imageId}`)
    .once("value");
  const imageData = snapshot.val();
  if (!imageData) throw new Error("Image not found");

  await db.ref(`users/${user.uid}/profileImage`).set(imageData.url);
  return true;
};

onAuthStateChanged(auth, (user) => {
  if (user) {
    console.log("User's name:", user.displayName);
  }
});


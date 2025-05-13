// src/services/firebase.js
import firebase from "firebase/compat/app";
import "firebase/compat/auth";
import "firebase/compat/database";
import {
  getStorage,
  ref as storageRef,
  uploadBytes,
  getDownloadURL,
} from "firebase/storage";
import {
  getDatabase,
  ref,
  set,
  onValue,
  push,
  update,
} from "firebase/database";

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

//
// 🔒 LOGOUT FUNCTION
//
export const logout = () => {
  return auth.signOut();
};

//
// 📋 ADD TASK
//
export const addTask = async (task) => {
  const user = auth.currentUser;
  if (!user) throw new Error("User not authenticated");

  try {
    const newRef = db.ref(`users/${user.uid}/tasks`).push();
    await newRef.set({ ...task, id: newRef.key });
    return true;
  } catch (err) {
    console.error("Firebase Error - addTask:", err);
    throw err;
  }
};

//
// 📥 GET TASKS
//
export const getTaskOverview = async () => {
  const user = auth.currentUser;
  if (!user) throw new Error("User not authenticated");

  try {
    const snapshot = await db.ref(`users/${user.uid}/tasks`).once("value");
    const val = snapshot.val();
    console.log("📥 Raw tasks from Firebase:", val);

    if (!val || typeof val !== "object") return [];
    return Object.values(val);
  } catch (err) {
    console.error("Firebase Error - getTaskOverview:", err);
    throw err;
  }
};

//
// ✏️ UPDATE TASK
//
export const updateTask = async (taskId, updates) => {
  const user = auth.currentUser;
  if (!user) throw new Error("User not authenticated");

  try {
    await db.ref(`users/${user.uid}/tasks/${taskId}`).update(updates);
    return true;
  } catch (err) {
    console.error("Firebase Error - updateTask:", err);
    throw err;
  }
};

//
// ➕ ADD PEBO DEVICE
//
export const addPeboDevice = async ({ name, location }) => {
  const userId = auth.currentUser.uid;
  const deviceRef = db.ref(`users/${userId}/peboDevices`).push();
  await deviceRef.set({
    name,
    location,
    createdAt: Date.now(),
  });
};

//
// 📄 GET PEBO DEVICES
//
export const getPeboDevices = async () => {
  const user = auth.currentUser;
  if (!user) throw new Error("User not authenticated");

  const snapshot = await db.ref(`users/${user.uid}/peboDevices`).once("value");

  const devices = [];
  snapshot.forEach((child) => {
    const deviceData = { id: child.key, ...child.val() };
    devices.push({
      id: deviceData.id,
      name: deviceData.name,
      location: deviceData.location,
    });
  });

  return devices;
};

//
// 💾 SAVE WIFI SETTINGS
//
export const saveWifiSettings = async (settings) => {
  const user = auth.currentUser;
  if (!user) throw new Error("User not authenticated");

  try {
    await db.ref(`users/${user.uid}/settings`).set(settings);
    return true;
  } catch (error) {
    console.error("Error saving Wi-Fi data:", error);
    throw error;
  }
};

//
// 📶 GET WIFI SETTINGS
//
export const getWifiName = async () => {
  const user = auth.currentUser;
  if (!user) throw new Error("User not authenticated");

  try {
    const snapshot = await db.ref(`users/${user.uid}/settings`).once("value");
    const data = snapshot.val();
    console.log("📶 Wi-Fi settings from Firebase:", data);

    return {
      peboName: data?.peboName || "Unknown PEBO",
      wifiSSID: data?.wifiSSID || "N/A",
      wifiPassword: data?.wifiPassword || "N/A",
    };
  } catch (error) {
    console.error("Error fetching Wi-Fi data:", error);
    return {
      peboName: "Unavailable",
      wifiSSID: "Unavailable",
      wifiPassword: "Unavailable",
    };
  }
};

//
// 🔐 SAVE S3 CONFIGURATION
//
export const saveS3Config = async (config) => {
  try {
    const { accessKey, secretKey, bucketName } = config;
    const userId = auth.currentUser.uid;
    const db = getDatabase();

    await set(ref(db, `users/${userId}/s3Config`), {
      accessKey,
      secretKey,
      bucketName,
      updatedAt: new Date().toISOString(),
    });

    return true;
  } catch (error) {
    console.error("Error saving S3 configuration:", error);
    throw error;
  }
};

//
// 🔍 GET S3 CONFIGURATION
//
export const getS3Config = async () => {
  try {
    const userId = auth.currentUser.uid;
    const db = getDatabase();

    return new Promise((resolve, reject) => {
      onValue(
        ref(db, `users/${userId}/s3Config`),
        (snapshot) => {
          resolve(snapshot.val() || {});
        },
        (error) => {
          reject(error);
        },
        { once: true }
      );
    });
  } catch (error) {
    console.error("Error getting S3 configuration:", error);
    throw error;
  }
};

//
// 📸 TRIGGER CAMERA CAPTURE
//
export const triggerCameraCapture = async (peboId) => {
  try {
    const db = getDatabase();
    const captureRef = ref(db, `peboActions/${peboId}/captureImage`);

    await set(captureRef, {
      requestedAt: new Date().toISOString(),
      status: "pending",
    });

    return true;
  } catch (error) {
    console.error("Error triggering camera capture:", error);
    throw error;
  }
};

//
// 🖼️ UPLOAD IMAGE TO FIREBASE STORAGE
//
export const uploadImageToStorage = async (uri, peboId) => {
  try {
    const storage = getStorage();
    const imageName = `pebo_${peboId}_${new Date().getTime()}.jpg`;
    const imageRef = storageRef(storage, `peboImages/${imageName}`);

    const response = await fetch(uri);
    const blob = await response.blob();

    await uploadBytes(imageRef, blob);
    const downloadURL = await getDownloadURL(imageRef);

    const db = getDatabase();
    await set(ref(db, `peboPhotos/${peboId}`), downloadURL);

    const historyRef = push(ref(db, `peboPhotoHistory/${peboId}`));
    await set(historyRef, {
      url: downloadURL,
      timestamp: new Date().toISOString(),
    });

    return downloadURL;
  } catch (error) {
    console.error("Error uploading image:", error);
    throw error;
  }
};

//
// 🕓 GET IMAGE HISTORY FOR PEBO
//
export const getPeboImageHistory = async (peboId) => {
  try {
    const db = getDatabase();

    return new Promise((resolve, reject) => {
      onValue(
        ref(db, `peboPhotoHistory/${peboId}`),
        (snapshot) => {
          const data = snapshot.val() || {};
          const history = Object.keys(data)
            .map((key) => ({
              id: key,
              ...data[key],
            }))
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

          resolve(history);
        },
        (error) => {
          reject(error);
        },
        { once: true }
      );
    });
  } catch (error) {
    console.error("Error getting image history:", error);
    throw error;
  }
};

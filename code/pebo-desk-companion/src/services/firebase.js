// src/services/firebase.js
import firebase from "firebase/compat/app";
import "firebase/compat/auth";
import "firebase/compat/database";

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
export const addPeboDevice = async (pebo) => {
  const user = auth.currentUser;
  if (!user) throw new Error("User not authenticated");

  try {
    const newRef = db.ref(`users/${user.uid}/pebos`).push();
    await newRef.set({ ...pebo, id: newRef.key });
    return true;
  } catch (err) {
    console.error("Firebase Error - addPeboDevice:", err);
    throw err;
  }
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

// src/services/firebase.js
import firebase from "firebase/compat/app";
import "firebase/compat/auth";
import "firebase/compat/database";

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

// Initialize Firebase app
if (!firebase.apps.length) {
  firebase.initializeApp(firebaseConfig);
}

// Firebase services
export const auth = firebase.auth();
export const db = firebase.database();

// ✅ Add a new task
export const addTask = async (task) => {
  try {
    const newRef = db.ref("tasks").push(); // Generate unique ID
    await newRef.set({ ...task, id: newRef.key });
    return true;
  } catch (err) {
    console.error("Firebase Error - addTask:", err);
    throw err;
  }
};

// ✅ Get all tasks
export const getTaskOverview = async () => {
  try {
    const snapshot = await db.ref("tasks").once("value");
    const val = snapshot.val();
    if (!val) return [];
    return Object.values(val);
  } catch (err) {
    console.error("Firebase Error - getTaskOverview:", err);
    throw err;
  }
};

// Placeholder: Replace 'wifiName' with your actual Firebase path
export const getWifiName = async () => {
  const user = auth.currentUser;
  if (!user) throw new Error("User not authenticated");

  try {
    const snapshot = await db.ref(`users/${user.uid}/settings`).once("value");
    const data = snapshot.val();

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

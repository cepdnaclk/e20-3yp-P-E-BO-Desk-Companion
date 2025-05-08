// src/context/AuthContext.js

import React, { createContext, useState, useEffect, useContext } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { auth } from "../services/firebase";

export const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    console.log("▶️ Attaching onAuthStateChanged listener");
    const unsubscribe = auth.onAuthStateChanged(async (currentUser) => {
      console.log("🔔 onAuthStateChanged:", currentUser);
      if (currentUser) {
        setUser(currentUser);
        try {
          await AsyncStorage.setItem(
            "user",
            JSON.stringify({
              uid: currentUser.uid,
              email: currentUser.email,
              displayName: currentUser.displayName,
            })
          );
        } catch (err) {
          console.error("Error storing user data:", err);
        }
      } else {
        setUser(null);
        try {
          await AsyncStorage.removeItem("user");
        } catch (err) {
          console.error("Error removing user data:", err);
        }
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const signIn = async (email, password) => {
    setLoading(true); // Start loading
    try {
      await auth.signInWithEmailAndPassword(email, password);
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    } finally {
      setLoading(false); // Stop loading after sign-in process
    }
  };

  const signUp = async (email, password, displayName) => {
    setLoading(true); // Start loading
    try {
      const cred = await auth.createUserWithEmailAndPassword(email, password);
      if (displayName) {
        await cred.user.updateProfile({ displayName });
      }
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    } finally {
      setLoading(false); // Stop loading after sign-up process
    }
  };

  const signOut = async () => {
    setLoading(true); // Start loading
    try {
      await auth.signOut();
      setUser(null); // Make sure to reset the user state
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    } finally {
      setLoading(false); // Stop loading after sign-out process
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        authReady: !loading, // Only show ready state when not loading
        signIn,
        signUp,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

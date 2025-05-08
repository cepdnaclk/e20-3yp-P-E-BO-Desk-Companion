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

    // Fallback: if listener never calls back, force loading off after 5s
    const timeout = setTimeout(() => {
      console.warn("⏰ onAuthStateChanged timeout, forcing loading=false");
      setLoading(false);
    }, 5000);

    return () => {
      unsubscribe();
      clearTimeout(timeout);
    };
  }, []);

  const signIn = (email, password) =>
    auth
      .signInWithEmailAndPassword(email, password)
      .then(() => ({ success: true }))
      .catch((err) => ({ success: false, error: err.message }))
      .finally(() => setLoading(false));

  const signUp = async (email, password, displayName) => {
    setLoading(true);
    try {
      const cred = await auth.createUserWithEmailAndPassword(email, password);
      if (displayName) {
        await cred.user.updateProfile({ displayName });
      }
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  const signOut = () =>
    auth
      .signOut()
      .then(() => ({ success: true }))
      .catch((err) => ({ success: false, error: err.message }))
      .finally(() => setLoading(false));

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        authReady: !loading, // <- new alias
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

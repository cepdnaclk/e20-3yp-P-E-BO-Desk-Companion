import React, {
  createContext,
  useState,
  useEffect,
  useContext,
  useMemo,
} from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { auth } from "../services/firebase";

export const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timeout = setTimeout(() => {
      console.warn(
        "âš ï¸ Auth fallback triggered â€” onAuthStateChanged may have failed."
      );
      setLoading(false);
    }, 5000);

    const unsubscribe = auth.onAuthStateChanged((currentUser) => {
      const handleUser = async () => {
        clearTimeout(timeout);
        try {
          if (__DEV__) console.log("ðŸ”” Auth state changed:", currentUser);

          if (currentUser) {
            setUser(currentUser);
            await AsyncStorage.setItem(
              "user",
              JSON.stringify({
                uid: currentUser.uid,
                email: currentUser.email,
                displayName: currentUser.displayName,
              })
            );
          } else {
            setUser(null);
            await AsyncStorage.removeItem("user");
          }
        } catch (err) {
          console.error("âŒ Auth state handling error:", err);
        } finally {
          setLoading(false);
        }
      };

      handleUser(); // safely handle async logic
    });

    return () => {
      clearTimeout(timeout);
      unsubscribe();
    };
  }, []);

  const signIn = async (email, password) => {
    setLoading(true);
    try {
      await auth.signInWithEmailAndPassword(email, password);
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

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

  const signOut = async () => {
    setLoading(true);
    try {
      await auth.signOut();
      setUser(null);
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  const value = useMemo(
    () => ({
      user,
      loading,
      authReady: !loading,
      signIn,
      signUp,
      signOut,
    }),
    [user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
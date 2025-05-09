import React, { useState, useEffect, useContext } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from "react-native";
import { Ionicons, MaterialIcons } from "@expo/vector-icons";
import {
  signInWithEmailAndPassword,
  sendPasswordResetEmail,
} from "firebase/auth";
import { auth } from "../services/firebase";
import { AuthContext } from "../context/AuthContext";
import PopupModal from "../components/PopupModal";

export default function LoginScreen({ navigation }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const { setUser } = useContext(AuthContext);

  const [modalVisible, setModalVisible] = useState(false);
  const [modalContent, setModalContent] = useState({
    title: "",
    message: "",
    icon: "",
  });

  const showModal = (title, message, icon, onClose = null) => {
    setModalContent({ title, message, icon, onClose });
    setModalVisible(true);
  };

  const validateEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

  useEffect(() => {
    const newErrors = {};
    if (email && !validateEmail(email)) {
      newErrors.email = "Invalid email format";
    }
    if (password && password.length < 6) {
      newErrors.password = "Password must be at least 6 characters";
    }
    setErrors(newErrors);
  }, [email, password]);

  const handleLogin = async () => {
    if (!email || !password) {
      return showModal(
        "Missing Fields",
        "Please enter email and password.",
        "alert-circle"
      );
    }

    if (Object.keys(errors).length > 0) {
      return showModal(
        "Validation Error",
        "Fix the highlighted issues first.",
        "alert-circle"
      );
    }

    setLoading(true);
    try {
      const userCredential = await signInWithEmailAndPassword(
        auth,
        email.trim(),
        password.trim()
      );
      setUser(userCredential.user);
    } catch (err) {
      let msg = "Could not log in. Try again.";
      switch (err.code) {
        case "auth/user-not-found":
          msg = "User not found.";
          break;
        case "auth/wrong-password":
          msg = "Incorrect password.";
          break;
        case "auth/invalid-email":
          msg = "Invalid email address.";
          break;
        case "auth/too-many-requests":
          msg = "Too many attempts. Try again later.";
          break;
        case "auth/network-request-failed":
          msg = "Network error. Check your internet connection.";
          break;
      }
      showModal("Login Error", msg, "close-circle");
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordReset = async () => {
    if (!email) {
      return showModal(
        "Enter Email",
        "Please enter your email to reset password.",
        "mail"
      );
    }

    if (errors.email) {
      return showModal(
        "Invalid Email",
        "Please enter a valid email.",
        "alert-circle"
      );
    }

    try {
      await sendPasswordResetEmail(auth, email.trim());
      showModal("Success", "Password reset email sent.", "checkmark-circle");
    } catch (error) {
      showModal(
        "Error",
        "Unable to send reset email. Try again.",
        "close-circle"
      );
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : null}
      style={{ flex: 1 }}
    >
      <ScrollView contentContainerStyle={{ flexGrow: 1 }}>
        <View style={styles.container}>
          <View style={styles.card}>
            <Text style={styles.title}>Welcome Back 👋</Text>
            <Text style={styles.subtitle}>Login to your account</Text>

            {/* Email Field */}
            <View
              style={[styles.inputWrapper, errors.email && styles.inputError]}
            >
              <MaterialIcons
                name="email"
                size={20}
                color="#888"
                style={styles.inputIcon}
              />
              <TextInput
                placeholder="Email"
                keyboardType="email-address"
                autoCapitalize="none"
                value={email}
                placeholderTextColor="#888"
                onChangeText={setEmail}
                style={styles.input}
              />
            </View>
            {errors.email && (
              <Text style={styles.errorText}>{errors.email}</Text>
            )}

            {/* Password Field */}
            <View
              style={[
                styles.inputWrapper,
                errors.password && styles.inputError,
              ]}
            >
              <Ionicons
                name="lock-closed-outline"
                size={20}
                color="#888"
                style={styles.inputIcon}
              />
              <TextInput
                placeholder="Password"
                secureTextEntry={!showPassword}
                placeholderTextColor="#888"
                value={password}
                onChangeText={setPassword}
                style={styles.input}
              />
              <TouchableOpacity onPress={() => setShowPassword(!showPassword)}>
                <Ionicons
                  name={showPassword ? "eye-off" : "eye"}
                  size={20}
                  color="#888"
                />
              </TouchableOpacity>
            </View>
            {errors.password && (
              <Text style={styles.errorText}>{errors.password}</Text>
            )}

            <TouchableOpacity onPress={handlePasswordReset}>
              <Text style={styles.forgotText}>Forgot Password?</Text>
            </TouchableOpacity>

            {/* Login Button */}
            {loading ? (
              <ActivityIndicator
                size="large"
                color="#007AFF"
                style={{ marginVertical: 20 }}
              />
            ) : (
              <TouchableOpacity style={styles.button} onPress={handleLogin}>
                <Text style={styles.buttonText}>Log In</Text>
              </TouchableOpacity>
            )}

            {/* Or Divider */}
            {/* <Text style={styles.orText}>— OR —</Text> */}

            {/* Google Button (placeholder)
            <TouchableOpacity style={styles.googleButton}>
              <Ionicons name="logo-google" size={20} color="#fff" />
              <Text style={styles.googleText}>Continue with Google</Text>
            </TouchableOpacity> */}

            {/* Sign Up Link */}
            <TouchableOpacity onPress={() => navigation.navigate("SignUp")}>
              <Text style={styles.linkText}>
                Don't have an account?{" "}
                <Text style={styles.linkBold}>Sign Up</Text>
              </Text>
            </TouchableOpacity>
          </View>

          <PopupModal
            visible={modalVisible}
            title={modalContent.title}
            message={modalContent.message}
            icon={modalContent.icon}
            onClose={() => {
              setModalVisible(false);
              modalContent.onClose?.();
            }}
          />
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f1f4f9",
    justifyContent: "center",
    padding: 20,
  },
  card: {
    backgroundColor: "#fff",
    padding: 24,
    borderRadius: 20,
    elevation: 5,
    shadowColor: "#000",
    shadowOpacity: 0.1,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 8,
  },
  title: {
    fontSize: 26,
    fontWeight: "700",
    textAlign: "center",
    marginBottom: 4,
    color: "#222",
  },
  subtitle: {
    fontSize: 15,
    textAlign: "center",
    marginBottom: 24,
    color: "#777",
  },
  inputWrapper: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#f9f9f9",
    borderWidth: 1,
    borderColor: "#ccc",
    borderRadius: 10,
    paddingHorizontal: 12,
    marginBottom: 10,
  },
  input: {
    flex: 1,
    height: 48,
    fontSize: 15,
    color: "#333",
  },
  inputIcon: {
    marginRight: 8,
  },
  inputError: {
    borderColor: "#FF3B30",
  },
  errorText: {
    color: "#FF3B30",
    fontSize: 13,
    marginBottom: 6,
    marginLeft: 4,
  },
  forgotText: {
    color: "#007AFF",
    textAlign: "right",
    marginBottom: 20,
    fontSize: 14,
  },
  button: {
    backgroundColor: "#007AFF",
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: "center",
    marginBottom: 20,
  },
  buttonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
  orText: {
    textAlign: "center",
    color: "#888",
    marginBottom: 20,
    fontSize: 13,
  },
  googleButton: {
    flexDirection: "row",
    backgroundColor: "#DB4437",
    paddingVertical: 12,
    borderRadius: 10,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 20,
  },
  googleText: {
    color: "#fff",
    marginLeft: 8,
    fontSize: 15,
    fontWeight: "600",
  },
  linkText: {
    textAlign: "center",
    color: "#555",
    fontSize: 14,
  },
  linkBold: {
    color: "#007AFF",
    fontWeight: "600",
  },
});

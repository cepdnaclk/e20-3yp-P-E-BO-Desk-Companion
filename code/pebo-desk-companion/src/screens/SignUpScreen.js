import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  ActivityIndicator,
  TouchableOpacity,
} from "react-native";
import { createUserWithEmailAndPassword } from "firebase/auth";
import { auth } from "../services/firebase";
import { Ionicons } from "@expo/vector-icons";
import PopupModal from "../components/PopupModal";

export default function SignUpScreen({ navigation }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [modalVisible, setModalVisible] = useState(false);
  const [modalContent, setModalContent] = useState({
    title: "",
    message: "",
    icon: "",
  });

  const showModal = (title, message, icon = "alert-circle") => {
    setModalContent({ title, message, icon });
    setModalVisible(true);
  };

  useEffect(() => {
    const newErrors = {};
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = "Invalid email format";
    }
    if (password && password.length < 6) {
      newErrors.password = "Password must be at least 6 characters";
    }
    if (confirm && confirm !== password) {
      newErrors.confirm = "Passwords do not match";
    }
    setErrors(newErrors);
  }, [email, password, confirm]);

  const [redirectToDashboard, setRedirectToDashboard] = useState(false);

  useEffect(() => {
    if (redirectToDashboard && !modalVisible) {
      navigation.reset({
        index: 0,
        routes: [{ name: "Dashboard" }],
      });
    }
  }, [redirectToDashboard, modalVisible]);

  const handleSignUp = async () => {
    if (!email || !password || !confirm) {
      return showModal(
        "Missing Fields",
        "Please fill in all fields.",
        "alert-circle"
      );
    }

    if (Object.keys(errors).length > 0) {
      return showModal(
        "Fix Errors",
        "Please fix the highlighted issues.",
        "alert-circle"
      );
    }

    setLoading(true);
    try {
      await createUserWithEmailAndPassword(auth, email.trim(), password);
      setRedirectToDashboard(true);
      showModal("Success", "Account created!", "checkmark-circle");
    } catch (err) {
      let msg = "Could not sign up. Try again.";
      let icon = "close-circle";
      if (err.code === "auth/email-already-in-use")
        msg = "Email already in use.";
      else if (err.code === "auth/invalid-email")
        msg = "Invalid email address.";
      else if (err.code === "auth/weak-password") msg = "Password is too weak.";
      showModal("Signup Error", msg, icon);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Sign Up 👤</Text>
      <Text style={styles.welcome}>
        👋 Let’s get you started with a new account.
      </Text>

      {/* Email Input */}
      <TextInput
        style={[styles.input, errors.email && styles.inputError]}
        placeholder="Email"
        placeholderTextColor="#888"
        keyboardType="email-address"
        autoCapitalize="none"
        value={email}
        onChangeText={setEmail}
      />
      {errors.email && <Text style={styles.errorText}>{errors.email}</Text>}

      {/* Password Input */}
      <View style={[styles.inputRow, errors.password && styles.inputError]}>
        <TextInput
          style={styles.flexInput}
          placeholder="Password"
          placeholderTextColor="#888"
          secureTextEntry={!showPassword}
          value={password}
          onChangeText={setPassword}
        />
        <TouchableOpacity onPress={() => setShowPassword(!showPassword)}>
          <Ionicons
            name={showPassword ? "eye-off" : "eye"}
            size={22}
            color="#666"
          />
        </TouchableOpacity>
      </View>
      {errors.password && (
        <Text style={styles.errorText}>{errors.password}</Text>
      )}

      {/* Confirm Password */}
      <View style={[styles.inputRow, errors.confirm && styles.inputError]}>
        <TextInput
          style={styles.flexInput}
          placeholder="Confirm Password"
          placeholderTextColor="#888"
          secureTextEntry={!showConfirm}
          value={confirm}
          onChangeText={setConfirm}
        />
        <TouchableOpacity onPress={() => setShowConfirm(!showConfirm)}>
          <Ionicons
            name={showConfirm ? "eye-off" : "eye"}
            size={22}
            color="#666"
          />
        </TouchableOpacity>
      </View>
      {errors.confirm && <Text style={styles.errorText}>{errors.confirm}</Text>}

      {loading ? (
        <ActivityIndicator
          size="large"
          color="#007AFF"
          style={{ marginVertical: 20 }}
        />
      ) : (
        <TouchableOpacity style={styles.button} onPress={handleSignUp}>
          <Text style={styles.buttonText}>Create Account</Text>
        </TouchableOpacity>
      )}

      <TouchableOpacity
        onPress={() => navigation.navigate("Login")}
        style={styles.loginLink}
      >
        <Text style={styles.linkText}>
          Already have an account? <Text style={styles.linkBold}>Log in</Text>
        </Text>
      </TouchableOpacity>

      {/* Modal */}
      <PopupModal
        visible={modalVisible}
        onClose={() => {
          setModalVisible(false);
          if (redirectToDashboard) {
            setRedirectToDashboard(false);
            navigation.reset({
              index: 0,
              routes: [{ name: "Dashboard" }],
            });
          }
        }}
        title={modalContent.title}
        message={modalContent.message}
        icon={modalContent.icon}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 24,
    justifyContent: "center",
    backgroundColor: "#f2f2f7", // updated for soft tone
  },
  title: {
    fontSize: 28,
    fontWeight: "700",
    textAlign: "center",
    color: "#222",
    marginBottom: 12,
  },
  welcome: {
    fontSize: 16,
    color: "#555",
    textAlign: "center",
    marginBottom: 28,
  },
  input: {
    height: 50,
    borderWidth: 1,
    borderColor: "#ccc",
    borderRadius: 12,
    paddingHorizontal: 16,
    marginBottom: 8,
    backgroundColor: "#fff",
    fontSize: 16,
    color: "#000", // ✅ ensures text is visible
  },
  inputRow: {
    height: 50,
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#ccc",
    borderRadius: 12,
    paddingHorizontal: 16,
    backgroundColor: "#fff",
    marginBottom: 8,
  },
  flexInput: {
    flex: 1,
    fontSize: 16,
    color: "#000", // ✅ ensures text is visible
  },
  inputError: {
    borderColor: "#FF3B30",
  },
  errorText: {
    color: "#FF3B30",
    fontSize: 13,
    marginBottom: 10,
    marginLeft: 4,
  },
  button: {
    backgroundColor: "#007AFF",
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: "center",
    marginTop: 10,
    shadowColor: "#007AFF",
    shadowOpacity: 0.2,
    shadowOffset: { width: 0, height: 3 },
    shadowRadius: 5,
    elevation: 3,
  },
  buttonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
  loginLink: {
    marginTop: 24,
    alignItems: "center",
  },
  linkText: {
    color: "#555",
    fontSize: 14,
  },
  linkBold: {
    color: "#007AFF",
    fontWeight: "600",
  },
});

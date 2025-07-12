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
  StatusBar,
  ImageBackground,
  Image,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import {
  signInWithEmailAndPassword,
  sendPasswordResetEmail,
  createUserWithEmailAndPassword,
} from "firebase/auth";
import { getDatabase, ref, set } from "firebase/database";
import { auth } from "../services/firebase";
import { AuthContext } from "../context/AuthContext";
import PopupModal from "../components/PopupModal";

export default function AuthScreen({ navigation }) {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [name, setName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
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
    if (isSignUp && name.trim() === "") {
      newErrors.name = "Name is required";
    }
    if (email && !validateEmail(email)) {
      newErrors.email = "Invalid email format";
    }
    if (password && password.length < 6) {
      newErrors.password = "Password must be at least 6 characters";
    }
    if (isSignUp && confirmPassword && confirmPassword !== password) {
      newErrors.confirmPassword = "Passwords do not match";
    }
    setErrors(newErrors);
  }, [email, password, confirmPassword, name, isSignUp]);

  const clearForm = () => {
    setEmail("");
    setPassword("");
    setConfirmPassword("");
    setName("");
    setErrors({});
  };

  const handleToggle = (signUp) => {
    setIsSignUp(signUp);
    clearForm();
  };

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

  const handleSignUp = async () => {
    if (!email || !password || !confirmPassword || !name.trim()) {
      return showModal("Missing Fields", "Please fill in all fields.");
    }
    if (password !== confirmPassword) {
      return showModal("Password Mismatch", "Passwords do not match.");
    }
    if (Object.keys(errors).length > 0) {
      return showModal("Fix Errors", "Please fix the highlighted issues.");
    }
    setLoading(true);
    try {
      const userCredential = await createUserWithEmailAndPassword(
        auth,
        email.trim(),
        password
      );
      const user = userCredential.user;
      await user.updateProfile({
        displayName: name.trim(),
      });
      const db = getDatabase();
      await set(ref(db, `users/${user.uid}`), {
        name: name.trim(),
        email: email.trim(),
      });
      showModal("Success", "Account created successfully!", "checkmark-circle");
      setUser(user);
    } catch (err) {
      let msg = "Could not sign up. Try again.";
      if (err.code === "auth/email-already-in-use")
        msg = "Email already in use.";
      else if (err.code === "auth/invalid-email")
        msg = "Invalid email address.";
      else if (err.code === "auth/weak-password") msg = "Password is too weak.";
      showModal("Signup Error", msg, "close-circle");
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
    <>
      <StatusBar barStyle="light-content" backgroundColor="#0A0A0A" />
      <ImageBackground
        source={require("../../assets/images/robot-pebo.jpg")} // Your background image
        style={styles.backgroundImage}
        resizeMode="cover"
      >
        {/* Dark overlay for better text readability */}
        <View style={styles.overlay} />

        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : null}
          style={styles.container}
        >
          <ScrollView contentContainerStyle={styles.scrollContent}>
            <View style={styles.header}>
              <Text style={styles.title}>
                {isSignUp ? "Create Your" : "Welcome Back"}
              </Text>
              <Text style={styles.subtitle}>
                {isSignUp ? "New Account" : "to PEBO "}
              </Text>
              {isSignUp && (
                <Text style={styles.description}>
                  Sign up to Your Desk Companion.
                </Text>
              )}
              {/* Robot Image - Only show for Sign In (now smaller since bg is there) */}
              {/* {!isSignUp && (
                <View style={styles.robotContainer}>
                  <View style={styles.robotImageWrapper}>
                    <Image
                      source={require("../../assets/images/robot-pebo.jpg")}
                      style={styles.robotImage}
                      resizeMode="cover"
                    />
                    <View style={styles.robotImageOverlay} />
                  </View>
                </View>
              )} */}
            </View>

            {/* Toggle Switch */}
            <View style={styles.toggleContainer}>
              <View style={styles.toggleWrapper}>
                <TouchableOpacity
                  style={[
                    styles.toggleButton,
                    !isSignUp && styles.toggleButtonActive,
                  ]}
                  onPress={() => handleToggle(false)}
                >
                  <Text
                    style={[
                      styles.toggleText,
                      !isSignUp && styles.toggleTextActive,
                    ]}
                  >
                    Sign In
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[
                    styles.toggleButton,
                    isSignUp && styles.toggleButtonActive,
                  ]}
                  onPress={() => handleToggle(true)}
                >
                  <Text
                    style={[
                      styles.toggleText,
                      isSignUp && styles.toggleTextActive,
                    ]}
                  >
                    Sign Up
                  </Text>
                </TouchableOpacity>
              </View>
            </View>

            <View style={styles.form}>
              {/* Name Field - Only for Sign Up */}
              {isSignUp && (
                <View style={styles.inputContainer}>
                  <Text style={styles.inputLabel}>Full Name</Text>
                  <View
                    style={[
                      styles.inputWrapper,
                      errors.name && styles.inputError,
                    ]}
                  >
                    <TextInput
                      placeholder="Enter your full name"
                      placeholderTextColor="#666"
                      autoCapitalize="words"
                      value={name}
                      onChangeText={setName}
                      style={styles.input}
                    />
                  </View>
                  {errors.name && (
                    <Text style={styles.errorText}>{errors.name}</Text>
                  )}
                </View>
              )}

              {/* Email Field */}
              <View style={styles.inputContainer}>
                <Text style={styles.inputLabel}>Email address</Text>
                <View
                  style={[
                    styles.inputWrapper,
                    errors.email && styles.inputError,
                  ]}
                >
                  <TextInput
                    placeholder="Enter your email"
                    keyboardType="email-address"
                    autoCapitalize="none"
                    value={email}
                    placeholderTextColor="#666"
                    onChangeText={setEmail}
                    style={styles.input}
                  />
                </View>
                {errors.email && (
                  <Text style={styles.errorText}>{errors.email}</Text>
                )}
              </View>

              {/* Password Field */}
              <View style={styles.inputContainer}>
                <View style={styles.labelRow}>
                  <Text style={styles.inputLabel}>Password</Text>
                  {!isSignUp && (
                    <TouchableOpacity onPress={handlePasswordReset}>
                      <Text style={styles.forgotText}>Forgot Password?</Text>
                    </TouchableOpacity>
                  )}
                </View>
                <View
                  style={[
                    styles.inputWrapper,
                    errors.password && styles.inputError,
                  ]}
                >
                  <TextInput
                    placeholder={
                      isSignUp ? "Create a password" : "Enter your password"
                    }
                    secureTextEntry={!showPassword}
                    placeholderTextColor="#666"
                    value={password}
                    onChangeText={setPassword}
                    style={styles.input}
                  />
                  <TouchableOpacity
                    onPress={() => setShowPassword(!showPassword)}
                  >
                    <Ionicons
                      name={showPassword ? "eye-off" : "eye"}
                      size={20}
                      color="#666"
                    />
                  </TouchableOpacity>
                </View>
                {errors.password && (
                  <Text style={styles.errorText}>{errors.password}</Text>
                )}
              </View>

              {/* Confirm Password Field - Only for Sign Up */}
              {isSignUp && (
                <View style={styles.inputContainer}>
                  <Text style={styles.inputLabel}>Confirm Password</Text>
                  <View
                    style={[
                      styles.inputWrapper,
                      errors.confirmPassword && styles.inputError,
                    ]}
                  >
                    <TextInput
                      placeholder="Confirm your password"
                      secureTextEntry={!showConfirmPassword}
                      placeholderTextColor="#666"
                      value={confirmPassword}
                      onChangeText={setConfirmPassword}
                      style={styles.input}
                    />
                    <TouchableOpacity
                      onPress={() =>
                        setShowConfirmPassword(!showConfirmPassword)
                      }
                    >
                      <Ionicons
                        name={showConfirmPassword ? "eye-off" : "eye"}
                        size={20}
                        color="#666"
                      />
                    </TouchableOpacity>
                  </View>
                  {errors.confirmPassword && (
                    <Text style={styles.errorText}>
                      {errors.confirmPassword}
                    </Text>
                  )}
                </View>
              )}

              {/* Submit Button */}
              <TouchableOpacity
                style={[
                  styles.submitButton,
                  loading && styles.submitButtonDisabled,
                ]}
                onPress={isSignUp ? handleSignUp : handleLogin}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator size="small" color="#000" />
                ) : (
                  <Text style={styles.submitButtonText}>
                    {isSignUp ? "Continue" : "Log In"}
                  </Text>
                )}
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
          </ScrollView>
        </KeyboardAvoidingView>
      </ImageBackground>
    </>
  );
}

const styles = StyleSheet.create({
  backgroundImage: {
    flex: 1,
    width: "100%",
    height: "100%",
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(10, 10, 10, 0.85)", // Dark overlay for better text readability
  },
  container: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: 24,
    paddingTop: 80,
    paddingBottom: 40,
  },
  header: {
    alignItems: "center",
    marginBottom: 40,
  },
  title: {
    fontSize: 32,
    fontWeight: "700",
    color: "#FFFFFF",
    marginBottom: 4,
    textShadowColor: "rgba(0, 0, 0, 0.5)",
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 3,
  },
  subtitle: {
    fontSize: 32,
    fontWeight: "700",
    color: "#FFFFFF",
    marginBottom: 8,
    textShadowColor: "rgba(0, 0, 0, 0.5)",
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 3,
  },
  description: {
    fontSize: 16,
    color: "#CCCCCC",
    textAlign: "center",
    textShadowColor: "rgba(0, 0, 0, 0.5)",
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 2,
  },
  robotContainer: {
    marginTop: 20,
    alignItems: "center",
  },
  robotImageWrapper: {
    position: "relative",
    borderRadius: 20,
    overflow: "hidden",
    borderWidth: 2,
    borderColor: "#1DE9B6",
  },
  robotImage: {
    width: 100,
    height: 100,
    borderRadius: 18,
  },
  robotImageOverlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0, 0, 0, 0.3)",
    borderRadius: 18,
  },
  toggleContainer: {
    alignItems: "center",
    marginBottom: 40,
  },
  toggleWrapper: {
    flexDirection: "row",
    backgroundColor: "rgba(26, 26, 26, 0.9)",
    borderRadius: 25,
    padding: 4,
    width: 200,
    borderWidth: 1,
    borderColor: "#333",
  },
  toggleButton: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 21,
    alignItems: "center",
  },
  toggleButtonActive: {
    backgroundColor: "#1DE9B6",
  },
  toggleText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#999",
  },
  toggleTextActive: {
    color: "#000",
  },
  form: {
    flex: 1,
  },
  inputContainer: {
    marginBottom: 24,
  },
  inputLabel: {
    fontSize: 16,
    color: "#FFFFFF",
    marginBottom: 8,
    fontWeight: "500",
    textShadowColor: "rgba(0, 0, 0, 0.5)",
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 2,
  },
  labelRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  inputWrapper: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(26, 26, 26, 0.9)",
    borderWidth: 1,
    borderColor: "#333",
    borderRadius: 12,
    paddingHorizontal: 16,
    height: 56,
  },
  input: {
    flex: 1,
    fontSize: 16,
    color: "#FFFFFF",
  },
  inputError: {
    borderColor: "#FF3B30",
  },
  errorText: {
    color: "#FF3B30",
    fontSize: 14,
    marginTop: 6,
    textShadowColor: "rgba(0, 0, 0, 0.5)",
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 2,
  },
  forgotText: {
    color: "#1DE9B6",
    fontSize: 14,
    fontWeight: "500",
    textShadowColor: "rgba(0, 0, 0, 0.5)",
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 2,
  },
  submitButton: {
    backgroundColor: "#1DE9B6",
    paddingVertical: 18,
    borderRadius: 12,
    alignItems: "center",
    marginTop: 20,
    shadowColor: "#000",
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  submitButtonDisabled: {
    opacity: 0.6,
  },
  submitButtonText: {
    color: "#000000",
    fontSize: 16,
    fontWeight: "600",
  },
});

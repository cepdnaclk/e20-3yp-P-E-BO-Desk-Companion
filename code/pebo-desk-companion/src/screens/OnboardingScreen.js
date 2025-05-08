import React from "react";
import {
  View,
  Text,
  ImageBackground,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
} from "react-native";

const { width, height } = Dimensions.get("window");

const OnboardingScreen = ({ onFinish, navigation }) => {
  return (
    <ImageBackground
      source={require("../../assets/images/bot.png")} // Adjust path as necessary
      style={styles.background}
      resizeMode="cover"
    >
      <View style={styles.overlay} />
      <View style={styles.content}>
        <Text style={styles.title}>Welcome to PEBO!</Text>
        <Text style={styles.subtitle}>Your Smart Desk Assistant</Text>
        <Text style={styles.description}>
          Manage tasks, automate your desk, and more with PEBO.
        </Text>
        <TouchableOpacity
          style={styles.button}
          onPress={() => {
            onFinish(navigation); // Pass navigation to onFinish
          }}
        >
          <Text style={styles.buttonText}>Get Started</Text>
        </TouchableOpacity>
      </View>
    </ImageBackground>
  );
};

const styles = StyleSheet.create({
  background: {
    flex: 1,
    width,
    height,
    justifyContent: "center",
    alignItems: "center",
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0, 0, 0, 0.5)", // Dark overlay for better readability
  },
  content: {
    padding: 24,
    alignItems: "center",
    zIndex: 1, // Ensures the content is above the overlay
  },
  title: {
    fontSize: 36,
    fontWeight: "bold",
    color: "#fff",
    textAlign: "center",
    marginBottom: 10,
  },
  subtitle: {
    fontSize: 22,
    color: "#eee",
    marginVertical: 10,
    textAlign: "center",
  },
  description: {
    fontSize: 16,
    color: "#ccc",
    textAlign: "center",
    marginVertical: 20,
  },
  button: {
    backgroundColor: "#5A67D8",
    paddingVertical: 14,
    paddingHorizontal: 40,
    borderRadius: 30,
    elevation: 4,
    marginTop: 20, // Add spacing between content and button
  },
  buttonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
});

export default OnboardingScreen;

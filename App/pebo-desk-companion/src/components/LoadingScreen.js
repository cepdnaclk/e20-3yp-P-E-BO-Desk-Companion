// LoadingScreen.js
import React, { useEffect, useRef } from "react";
import { View, Text, Animated, StyleSheet, Dimensions } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { MaterialIcons } from "@expo/vector-icons";

const { width, height } = Dimensions.get("window");

const LoadingScreen = ({ message = "Loading PEBO Data..." }) => {
  const spinValue = useRef(new Animated.Value(0)).current;
  const pulseValue = useRef(new Animated.Value(0)).current;
  const scaleValue = useRef(new Animated.Value(0)).current;
  const glowValue = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Spinning animation
    Animated.loop(
      Animated.timing(spinValue, {
        toValue: 1,
        duration: 2000,
        useNativeDriver: true,
      })
    ).start();

    // Pulsing animation
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseValue, {
          toValue: 1,
          duration: 1000,
          useNativeDriver: true,
        }),
        Animated.timing(pulseValue, {
          toValue: 0,
          duration: 1000,
          useNativeDriver: true,
        }),
      ])
    ).start();

    // Scale animation
    Animated.sequence([
      Animated.timing(scaleValue, {
        toValue: 1,
        duration: 800,
        useNativeDriver: true,
      }),
    ]).start();

    // Glow animation
    Animated.loop(
      Animated.sequence([
        Animated.timing(glowValue, {
          toValue: 1,
          duration: 1500,
          useNativeDriver: true,
        }),
        Animated.timing(glowValue, {
          toValue: 0,
          duration: 1500,
          useNativeDriver: true,
        }),
      ])
    ).start();
  }, []);

  const spin = spinValue.interpolate({
    inputRange: [0, 1],
    outputRange: ["0deg", "360deg"],
  });

  const pulse = pulseValue.interpolate({
    inputRange: [0, 1],
    outputRange: [0.8, 1.2],
  });

  const glow = glowValue.interpolate({
    inputRange: [0, 1],
    outputRange: [0.3, 1],
  });

  return (
    <View style={styles.container}>
      <LinearGradient
        colors={["#000000", "#1a1a1a", "#000000"]}
        style={styles.gradient}
      >
        {/* Background particles */}
        <Animated.View
          style={[styles.particle, styles.particle1, { opacity: glow }]}
        />
        <Animated.View
          style={[styles.particle, styles.particle2, { opacity: glow }]}
        />
        <Animated.View
          style={[styles.particle, styles.particle3, { opacity: glow }]}
        />

        {/* Main loading content */}
        <View style={styles.content}>
          {/* PEBO Logo */}
          <Animated.View
            style={[
              styles.logoContainer,
              { transform: [{ scale: scaleValue }] },
            ]}
          >
            <Text style={styles.logo}>PEBO</Text>
          </Animated.View>

          {/* Loading spinner */}
          <Animated.View
            style={[
              styles.spinnerContainer,
              { transform: [{ rotate: spin }, { scale: pulse }] },
            ]}
          >
            <View style={styles.spinner}>
              <MaterialIcons name="settings" size={60} color="#1DE9B6" />
              <Animated.View style={[styles.glowRing, { opacity: glow }]} />
            </View>
          </Animated.View>

          {/* Loading dots */}
          <View style={styles.dotsContainer}>
            <LoadingDots />
          </View>

          {/* Loading message */}
          <Text style={styles.loadingText}>{message}</Text>

          {/* Progress indicators */}
          <View style={styles.progressContainer}>
            <Text style={styles.progressText}>Connecting to Firebase...</Text>
            <Text style={styles.progressText}>Syncing AWS Data...</Text>
            <Text style={styles.progressText}>Initializing Dashboard...</Text>
          </View>
        </View>
      </LinearGradient>
    </View>
  );
};

// Animated loading dots component
const LoadingDots = () => {
  const dot1 = useRef(new Animated.Value(0)).current;
  const dot2 = useRef(new Animated.Value(0)).current;
  const dot3 = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const animateDots = () => {
      Animated.sequence([
        Animated.timing(dot1, {
          toValue: 1,
          duration: 400,
          useNativeDriver: true,
        }),
        Animated.timing(dot2, {
          toValue: 1,
          duration: 400,
          useNativeDriver: true,
        }),
        Animated.timing(dot3, {
          toValue: 1,
          duration: 400,
          useNativeDriver: true,
        }),
        Animated.timing(dot1, {
          toValue: 0,
          duration: 400,
          useNativeDriver: true,
        }),
        Animated.timing(dot2, {
          toValue: 0,
          duration: 400,
          useNativeDriver: true,
        }),
        Animated.timing(dot3, {
          toValue: 0,
          duration: 400,
          useNativeDriver: true,
        }),
      ]).start(() => animateDots());
    };
    animateDots();
  }, []);

  return (
    <View style={styles.dots}>
      <Animated.View style={[styles.dot, { opacity: dot1 }]} />
      <Animated.View style={[styles.dot, { opacity: dot2 }]} />
      <Animated.View style={[styles.dot, { opacity: dot3 }]} />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  gradient: {
    flex: 1,
    width: "100%",
    justifyContent: "center",
    alignItems: "center",
  },
  particle: {
    position: "absolute",
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: "#1DE9B6",
  },
  particle1: {
    top: "20%",
    left: "15%",
  },
  particle2: {
    top: "60%",
    right: "20%",
  },
  particle3: {
    bottom: "30%",
    left: "70%",
  },
  content: {
    alignItems: "center",
    justifyContent: "center",
  },
  logoContainer: {
    marginBottom: 40,
  },
  logo: {
    fontSize: 48,
    fontWeight: "900",
    color: "#FFFFFF",
    letterSpacing: 6,
    textShadowColor: "#1DE9B6",
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 20,
  },
  spinnerContainer: {
    marginBottom: 30,
  },
  spinner: {
    width: 120,
    height: 120,
    borderRadius: 60,
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 2,
    borderColor: "rgba(29, 233, 182, 0.3)",
    position: "relative",
  },
  glowRing: {
    position: "absolute",
    width: 140,
    height: 140,
    borderRadius: 70,
    borderWidth: 1,
    borderColor: "#1DE9B6",
    top: -12,
    left: -12,
  },
  dotsContainer: {
    marginBottom: 30,
  },
  dots: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#1DE9B6",
    marginHorizontal: 4,
  },
  loadingText: {
    fontSize: 18,
    color: "#FFFFFF",
    fontWeight: "600",
    marginBottom: 30,
    textAlign: "center",
  },
  progressContainer: {
    alignItems: "center",
  },
  progressText: {
    fontSize: 12,
    color: "#888",
    marginBottom: 8,
    textTransform: "uppercase",
    letterSpacing: 1,
  },
});

export default LoadingScreen;

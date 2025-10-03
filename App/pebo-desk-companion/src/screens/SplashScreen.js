import React, { useRef, useEffect, useState } from "react";
import { View, StyleSheet, StatusBar, Text, Animated } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useAuth } from "../context/AuthContext";
import { useVideoPlayer, VideoView } from "expo-video";
import { BlurView } from "expo-blur";

const SplashScreen = () => {
  const navigation = useNavigation();
  const { user } = useAuth();
  const videoRef = useRef(null);
  const [loadingProgress, setLoadingProgress] = useState(new Animated.Value(0));
  const [isLoading, setIsLoading] = useState(true);

  const player = useVideoPlayer(
    require("../../assets/splash.mp4"),
    (instance) => {
      instance.loop = false;
      instance.play();
    }
  );

  // Loading animation
  useEffect(() => {
    const loadingAnimation = Animated.timing(loadingProgress, {
      toValue: 1,
      duration: 2000, // 2 seconds loading
      useNativeDriver: false,
    });

    loadingAnimation.start(() => {
      setIsLoading(false);
    });

    return () => loadingAnimation.stop();
  }, [loadingProgress]);

  useEffect(() => {
    const sub = player.addListener("playToEnd", () => {
      navigation.replace("Onboarding");
    });
    return () => sub.remove();
  }, [player, navigation]);

  const progressWidth = loadingProgress.interpolate({
    inputRange: [0, 1],
    outputRange: ["0%", "100%"],
  });

  return (
    <View style={styles.container}>
      <StatusBar hidden />
      <VideoView
        ref={videoRef}
        style={styles.backgroundVideo}
        player={player}
        allowsFullscreen={false}
        allowsPictureInPicture={false}
        resizeMode="cover"
      />
      <BlurView intensity={60} style={StyleSheet.absoluteFill} tint="dark" />
      <View style={styles.overlay} />
      <View style={styles.textContainer}>
        <Text style={styles.roboticText}>Welcome to PEBO</Text>

        {/* Loading Animation */}
        {isLoading && (
          <View style={styles.loadingContainer}>
            <Text style={styles.loadingText}>INITIALIZING...</Text>
            <View style={styles.loadingBarContainer}>
              <Animated.View
                style={[styles.loadingBar, { width: progressWidth }]}
              />
            </View>
            <LoadingDots />
          </View>
        )}
      </View>
    </View>
  );
};

// Animated loading dots component
const LoadingDots = () => {
  const [dotAnim] = useState(new Animated.Value(0));

  useEffect(() => {
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(dotAnim, {
          toValue: 1,
          duration: 500,
          useNativeDriver: true,
        }),
        Animated.timing(dotAnim, {
          toValue: 0,
          duration: 500,
          useNativeDriver: true,
        }),
      ])
    );
    animation.start();
    return () => animation.stop();
  }, [dotAnim]);

  const opacity = dotAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0.3, 1],
  });

  return (
    <View style={styles.dotsContainer}>
      <Animated.View style={[styles.dot, { opacity }]} />
      <Animated.View
        style={[styles.dot, { opacity, animationDelay: "0.2s" }]}
      />
      <Animated.View
        style={[styles.dot, { opacity, animationDelay: "0.4s" }]}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000" },
  backgroundVideo: {
    position: "absolute",
    width: "100%",
    height: "100%",
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0,0,0,0.4)",
  },
  textContainer: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: "center",
    alignItems: "center",
  },
  roboticText: {
    color: "#fff",
    fontSize: 36,
    fontFamily: "Orbitron-Bold",
    letterSpacing: 2,
    textShadowColor: "#000",
    textShadowOffset: { width: 2, height: 2 },
    textShadowRadius: 8,
    marginBottom: 40,
  },
  loadingContainer: {
    alignItems: "center",
    width: "80%",
  },
  loadingText: {
    color: "#00ffff",
    fontSize: 14,
    fontFamily: "Orbitron-Bold",
    letterSpacing: 1,
    marginBottom: 20,
    textShadowColor: "#00ffff",
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 8,
  },
  loadingBarContainer: {
    width: "100%",
    height: 4,
    backgroundColor: "rgba(255,255,255,0.2)",
    borderRadius: 2,
    overflow: "hidden",
    marginBottom: 20,
  },
  loadingBar: {
    height: "100%",
    backgroundColor: "#00ffff",
    borderRadius: 2,
    shadowColor: "#00ffff",
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 4,
  },
  dotsContainer: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#00ffff",
    marginHorizontal: 4,
    shadowColor: "#00ffff",
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 4,
  },
});

export default SplashScreen;

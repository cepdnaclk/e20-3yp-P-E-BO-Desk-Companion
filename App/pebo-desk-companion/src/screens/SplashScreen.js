import React, { useRef, useEffect } from "react";
import { View, StyleSheet, StatusBar, Text } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useAuth } from "../context/AuthContext";
import { useVideoPlayer, VideoView } from "expo-video";
import { BlurView } from "expo-blur";

const SplashScreen = () => {
  const navigation = useNavigation();
  const { user } = useAuth();
  const videoRef = useRef(null);

  const player = useVideoPlayer(
    require("../../assets/splash.mp4"),
    (instance) => {
      instance.loop = false;
      instance.play();
    }
  );

  useEffect(() => {
    const sub = player.addListener("playToEnd", () => {
      navigation.replace("Onboarding");
    });
    return () => sub.remove();
  }, [player, navigation]);

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
      </View>
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
    backgroundColor: "rgba(0,0,0,0.4)", // Darken for readability
  },
  textContainer: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: "center",
    alignItems: "center",
  },
  roboticText: {
    color: "#fff",
    fontSize: 36,
    fontFamily: "Orbitron-Bold", // Use a robotic font, see below
    letterSpacing: 2,
    textShadowColor: "#000",
    textShadowOffset: { width: 2, height: 2 },
    textShadowRadius: 8,
  },
});

export default SplashScreen;

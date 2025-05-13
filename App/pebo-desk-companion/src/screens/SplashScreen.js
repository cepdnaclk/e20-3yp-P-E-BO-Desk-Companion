import React, { useEffect, useRef } from "react";
import { View, Animated } from "react-native";
import LottieView from "lottie-react-native";
import { useNavigation } from "@react-navigation/native";


const AnimatedLottieView = Animated.createAnimatedComponent(LottieView);

const SplashScreen = () => {
  const navigation = useNavigation();
  const progress = useRef(new Animated.Value(0)).current;

useEffect(() => {
  Animated.loop(
    Animated.timing(progress, {
      toValue: 1,
      duration: 2000,
      useNativeDriver: false,
    })
  ).start();
}, []);


  return (
    <View style={{ flex: 1, justifyContent: "center", alignItems: "center" }}>
      <AnimatedLottieView
        source={require("../../assets/animations/Animation - 1746295208070.json")}
        progress={progress}
      />
    </View>
  );
};

export default SplashScreen;

import React, { useContext, useEffect, useState } from "react";
import { AuthContext } from "../context/AuthContext";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { createStackNavigator } from "@react-navigation/stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import SplashScreen from "../screens/SplashScreen";
import OnboardingScreen from "../screens/OnboardingScreen";
import AuthScreen from "../screens/AuthScreen";
// import AuthScreen from "../screens/AuthScreen";
import DashboardScreen from "../screens/DashboardScreen";
import TaskManagementScreen from "../screens/TaskManagementScreen";
import SettingsScreen from "../screens/SettingsScreen";
import { MaterialIcons } from "@expo/vector-icons";

const Stack = createStackNavigator();
const Tab = createBottomTabNavigator();
const THEME_COLORS = {
  primary: "#1DE9B6",
  secondary: "#4CAF50",
  background: "#000000",
  cardBackground: "rgba(26, 26, 26, 0.3)",
  cardBorder: "rgba(29, 233, 182, 0.2)",
  textPrimary: "#FFFFFF",
  textSecondary: "#888",
  textMuted: "#666",
  inputBackground: "rgba(26, 26, 26, 0.6)",
  inputBorder: "rgba(29, 233, 182, 0.3)",
  success: "#4CAF50",
  error: "#FF5252",
  warning: "#FF9800",
  accent: "#1DE9B6",
  glow: "rgba(29, 233, 182, 0.3)",
  shadow: "rgba(29, 233, 182, 0.2)",
  glassyGreen: "rgba(29, 233, 182, 0.1)",
  glassyBorder: "rgba(29, 233, 182, 0.4)",
  glassyGradient: ["#1DE9B6", "#00BFA5"],
};
// Log imports to debug
console.log("SettingsScreen:", SettingsScreen);
console.log("DashboardScreen:", DashboardScreen);
console.log("TaskManagementScreen:", TaskManagementScreen);

// Auth Stack
const AuthNavigator = () => (
  <Stack.Navigator screenOptions={{ headerShown: false }}>
    <Stack.Screen name="Login" component={AuthScreen} />
    {/* <Stack.Screen name="SignUp" component={AuthScreen} /> */}
  </Stack.Navigator>
);

// Bottom Tabs after login
const TabNavigator = () => {
  if (!SettingsScreen) {
    throw new Error(
      "SettingsScreen is not a valid component. Check the import."
    );
  }

  return (
    <Tab.Navigator
      initialRouteName="Dashboard"
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: THEME_COLORS.background,
          borderTopWidth: 0,
          // Optional: add a border or shadow that matches the theme
          borderTopColor: THEME_COLORS.cardBorder,
          elevation: 10,
          shadowColor: THEME_COLORS.shadow,
        },
        tabBarLabelStyle: {
          fontSize: 14,
          color: THEME_COLORS.textPrimary,
          fontWeight: "bold",
          letterSpacing: 1,
        },
        tabBarActiveTintColor: THEME_COLORS.primary,
        tabBarInactiveTintColor: THEME_COLORS.textSecondary,
        tabBarShowLabel: true,
      }}
    >
      <Tab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{
          tabBarLabel: "Dashboard",
          tabBarIcon: ({ color, size }) => (
            <MaterialIcons name="home" size={size} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="Tasks"
        component={TaskManagementScreen}
        options={{
          tabBarLabel: "Tasks",
          tabBarIcon: ({ color, size }) => (
            <MaterialIcons name="check-circle" size={size} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="Settings"
        component={SettingsScreen}
        options={{
          tabBarLabel: "Settings",
          tabBarIcon: ({ color, size }) => (
            <MaterialIcons name="settings" size={size} color={color} />
          ),
        }}
      />
    </Tab.Navigator>
  );
};

const MainNavigator = () => {
  const { user, authReady } = useContext(AuthContext);
  const [showSplash, setShowSplash] = useState(true);
  const [hasSeenOnboarding, setHasSeenOnboarding] = useState(null);

  useEffect(() => {
    const checkOnboarding = async () => {
      try {
        const seen = await AsyncStorage.getItem("hasSeenOnboarding");
        setHasSeenOnboarding(seen === "true");
      } catch (err) {
        console.error("Error reading onboarding status:", err);
        setHasSeenOnboarding(false);
      }
    };
    checkOnboarding();
  }, []);

  useEffect(() => {
    if (authReady && hasSeenOnboarding !== null) {
      const timer = setTimeout(() => setShowSplash(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [authReady, hasSeenOnboarding]);

  if (!authReady || showSplash || hasSeenOnboarding === null) {
    return <SplashScreen />;
  }

  if (!user) {
    if (!hasSeenOnboarding) {
      return (
        <OnboardingScreen
          onFinish={async () => {
            await AsyncStorage.setItem("hasSeenOnboarding", "true");
            setHasSeenOnboarding(true);
          }}
        />
      );
    }
    return <AuthNavigator />;
  }

  return <TabNavigator />;
};

export default MainNavigator;

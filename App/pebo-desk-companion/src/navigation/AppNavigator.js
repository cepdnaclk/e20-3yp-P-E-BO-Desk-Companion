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
        tabBarStyle: { backgroundColor: "#1e1e1e", borderTopWidth: 0 },
        tabBarLabelStyle: { fontSize: 14 },
        tabBarActiveTintColor: "#fff",
        tabBarInactiveTintColor: "#aaa",
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

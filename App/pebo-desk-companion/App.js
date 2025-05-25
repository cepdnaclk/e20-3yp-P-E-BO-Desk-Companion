// Polyfill TextEncoder and TextDecoder
import { TextEncoder, TextDecoder } from "text-encoding";

if (typeof global.TextEncoder === "undefined") {
  global.TextEncoder = TextEncoder;
}

if (typeof global.TextDecoder === "undefined") {
  global.TextDecoder = TextDecoder;
}

// Original imports
import "react-native-gesture-handler";
import React from "react";
import { StyleSheet, View, Text, ActivityIndicator } from "react-native";
import { AuthProvider, useAuth } from "./src/context/AuthContext";
import MainNavigator from "./src/navigation/AppNavigator";
import { NavigationContainer } from "@react-navigation/native";
import { GestureHandlerRootView } from "react-native-gesture-handler";

function AppContent() {
  const { loading } = useAuth();

  if (loading) {
    return (
      <View style={styles.loader}>
        <ActivityIndicator size="large" color="#FFFFFF" />
        <Text style={{ color: "#FFF", marginTop: 10 }}>Loading...</Text>
      </View>
    );
  }

  return (
    <NavigationContainer>
      <MainNavigator />
    </NavigationContainer>
  );
}

// ✅ Wrap everything and export this as default
export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  loader: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#333333",
  },
});

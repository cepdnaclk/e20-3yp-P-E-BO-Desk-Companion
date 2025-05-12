import React from "react";
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
} from "react-native";
import { Ionicons } from "@expo/vector-icons"; // Make sure expo/vector-icons is installed

const PopupModal = ({ visible, message, onClose, type = "info" }) => {
  const scaleValue = React.useRef(new Animated.Value(0)).current;

  React.useEffect(() => {
    if (visible) {
      Animated.spring(scaleValue, {
        toValue: 1,
        useNativeDriver: true,
        friction: 5,
      }).start();
    } else {
      scaleValue.setValue(0);
    }
  }, [visible]);

  const getIconDetails = () => {
    switch (type) {
      case "success":
        return { name: "checkmark-circle", color: "#28a745" };
      case "error":
        return { name: "close-circle", color: "#dc3545" };
      case "warning":
        return { name: "alert-circle", color: "#ffc107" };
      default:
        return { name: "information-circle", color: "#007bff" };
    }
  };

  const icon = getIconDetails();

  return (
    <Modal
      transparent
      animationType="fade"
      visible={visible}
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <Animated.View
          style={[
            styles.modalContainer,
            { transform: [{ scale: scaleValue }] },
          ]}
        >
          <Ionicons
            name={icon.name}
            size={48}
            color={icon.color}
            style={styles.icon}
          />
          <Text style={styles.messageText}>{message}</Text>
          <TouchableOpacity
            onPress={onClose}
            style={[styles.okButton, { backgroundColor: icon.color }]}
          >
            <Text style={styles.okButtonText}>OK</Text>
          </TouchableOpacity>
        </Animated.View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.4)",
    justifyContent: "center",
    alignItems: "center",
  },
  modalContainer: {
    backgroundColor: "#fff",
    width: "80%",
    borderRadius: 20,
    padding: 24,
    alignItems: "center",
    shadowColor: "#000",
    shadowOpacity: 0.25,
    shadowRadius: 10,
    elevation: 10,
  },
  icon: {
    marginBottom: 12,
  },
  messageText: {
    fontSize: 16,
    textAlign: "center",
    marginBottom: 20,
    color: "#333",
  },
  okButton: {
    paddingVertical: 10,
    paddingHorizontal: 28,
    borderRadius: 12,
  },
  okButtonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
});

export default PopupModal;

import React from "react";
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

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
        return { name: "checkmark-circle", color: "#1DE9B6" };
      case "error":
        return { name: "close-circle", color: "#FF3B30" };
      case "warning":
        return { name: "alert-circle", color: "#FF9500" };
      default:
        return { name: "information-circle", color: "#1DE9B6" };
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
    backgroundColor: "rgba(0,0,0,0.7)",
    justifyContent: "center",
    alignItems: "center",
  },
  modalContainer: {
    backgroundColor: "#1A1A1A",
    width: "80%",
    borderRadius: 20,
    padding: 24,
    alignItems: "center",
    shadowColor: "#000",
    shadowOpacity: 0.5,
    shadowRadius: 15,
    elevation: 20,
    borderWidth: 1,
    borderColor: "#333",
  },
  icon: {
    marginBottom: 12,
  },
  messageText: {
    fontSize: 16,
    textAlign: "center",
    marginBottom: 20,
    color: "#FFFFFF",
    lineHeight: 22,
  },
  okButton: {
    paddingVertical: 12,
    paddingHorizontal: 32,
    borderRadius: 12,
    minWidth: 80,
  },
  okButtonText: {
    color: "#000000",
    fontSize: 16,
    fontWeight: "600",
  },
});

export default PopupModal;

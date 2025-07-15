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

const PopupModal = ({
  visible,
  title,
  message,
  onClose,
  type = "info",
  icon,
  showButtons = false,
  onConfirm,
  onCancel,
  confirmText = "Confirm",
  cancelText = "Cancel",
}) => {
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
    // If custom icon is provided, use it
    if (icon) {
      switch (icon) {
        case "checkmark-circle":
          return { name: "checkmark-circle", color: "#1DE9B6" };
        case "alert-circle":
          return { name: "alert-circle", color: "#FF9500" };
        case "trash-outline":
          return { name: "trash-outline", color: "#FF3B30" };
        default:
          return { name: icon, color: "#1DE9B6" };
      }
    }

    // Fallback to type-based icons
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

  const iconDetails = getIconDetails();

  const handleConfirm = () => {
    if (onConfirm) {
      onConfirm();
    } else {
      onClose();
    }
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    } else {
      onClose();
    }
  };

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
            name={iconDetails.name}
            size={48}
            color={iconDetails.color}
            style={styles.icon}
          />

          {title && <Text style={styles.titleText}>{title}</Text>}

          <Text style={styles.messageText}>{message}</Text>

          {showButtons ? (
            <View style={styles.buttonContainer}>
              <TouchableOpacity
                onPress={handleCancel}
                style={[styles.button, styles.cancelButton]}
              >
                <Text style={styles.cancelButtonText}>{cancelText}</Text>
              </TouchableOpacity>

              <TouchableOpacity
                onPress={handleConfirm}
                style={[
                  styles.button,
                  styles.confirmButton,
                  { backgroundColor: iconDetails.color },
                ]}
              >
                <Text style={styles.confirmButtonText}>{confirmText}</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <TouchableOpacity
              onPress={onClose}
              style={[styles.okButton, { backgroundColor: iconDetails.color }]}
            >
              <Text style={styles.okButtonText}>OK</Text>
            </TouchableOpacity>
          )}
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
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#1A1A1A",
    width: "80%",
    borderRadius: 20,
    padding: 24,
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
  titleText: {
    fontSize: 18,
    fontWeight: "600",
    textAlign: "center",
    marginBottom: 8,
    color: "#FFFFFF",
  },
  messageText: {
    fontSize: 16,
    textAlign: "center",
    marginBottom: 20,
    color: "#FFFFFF",
    lineHeight: 22,
  },
  buttonContainer: {
    flexDirection: "row",
    gap: 12,
    width: "100%",
  },
  button: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 12,
    alignItems: "center",
  },
  cancelButton: {
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: "#555",
  },
  confirmButton: {
    // backgroundColor will be set dynamically
  },
  cancelButtonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "600",
  },
  confirmButtonText: {
    color: "#000000",
    fontSize: 16,
    fontWeight: "600",
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

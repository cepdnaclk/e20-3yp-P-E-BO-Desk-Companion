import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { getS3Config, saveS3Config } from "../services/firebase";

const S3ConfigSection = ({ onConfigSaved }) => {
  const [accessKey, setAccessKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [bucketName, setBucketName] = useState("");
  const [showSecret, setShowSecret] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [hasConfig, setHasConfig] = useState(false);

  // Load existing config if available
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const config = await getS3Config();
        if (config && config.accessKey) {
          setAccessKey(config.accessKey || "");
          setSecretKey(config.secretKey || "");
          setBucketName(config.bucketName || "");
          setHasConfig(true);
        }
      } catch (error) {
        console.error("Error loading S3 config:", error);
      } finally {
        setIsLoading(false);
      }
    };

    loadConfig();
  }, []);

  const handleSaveConfig = async () => {
    // Validate inputs
    if (!accessKey.trim() || !secretKey.trim() || !bucketName.trim()) {
      alert("Please fill in all S3 configuration fields");
      return;
    }

    setIsSaving(true);
    try {
      await saveS3Config({
        accessKey: accessKey.trim(),
        secretKey: secretKey.trim(),
        bucketName: bucketName.trim(),
      });

      setHasConfig(true);
      if (onConfigSaved) onConfigSaved();
      alert("S3 configuration saved successfully");
    } catch (error) {
      alert(`Error saving configuration: ${error.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <View style={[styles.card, { alignItems: "center", padding: 30 }]}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={{ marginTop: 10, color: "#666" }}>
          Loading S3 configuration...
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Ionicons name="cloud-upload" size={20} color="#007AFF" />
        <Text style={styles.cardLabel}>S3 Storage Configuration</Text>
      </View>

      <Text style={styles.description}>
        Configure AWS S3 storage for your PEBO images.
        {hasConfig ? " Your configuration is saved." : ""}
      </Text>

      <TextInput
        placeholder="AWS Access Key"
        style={styles.input}
        value={accessKey}
        onChangeText={setAccessKey}
        placeholderTextColor="#999"
        autoCapitalize="none"
      />

      <View style={styles.passwordContainer}>
        <TextInput
          placeholder="AWS Secret Key"
          style={[styles.input, { flex: 1, marginBottom: 0 }]}
          value={secretKey}
          onChangeText={setSecretKey}
          placeholderTextColor="#999"
          secureTextEntry={!showSecret}
          autoCapitalize="none"
        />
        <TouchableOpacity
          onPress={() => setShowSecret(!showSecret)}
          style={styles.eyeIcon}
        >
          <Ionicons
            name={showSecret ? "eye-off" : "eye"}
            size={22}
            color="#999"
          />
        </TouchableOpacity>
      </View>

      <TextInput
        placeholder="S3 Bucket Name"
        style={styles.input}
        value={bucketName}
        onChangeText={setBucketName}
        placeholderTextColor="#999"
        autoCapitalize="none"
      />

      <TouchableOpacity
        style={[styles.saveButton, isSaving && { backgroundColor: "#ddd" }]}
        onPress={handleSaveConfig}
        disabled={isSaving}
      >
        {isSaving ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <>
            <Ionicons name="save" size={20} color="#fff" />
            <Text style={styles.saveButtonText}>
              {hasConfig ? "Update S3 Config" : "Save S3 Config"}
            </Text>
          </>
        )}
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
    shadowColor: "#000",
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 6,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 16,
  },
  cardLabel: {
    fontSize: 16,
    fontWeight: "600",
    marginLeft: 8,
    color: "#007AFF",
  },
  description: {
    fontSize: 14,
    color: "#666",
    marginBottom: 15,
  },
  input: {
    backgroundColor: "#F0F4F8",
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
    fontSize: 16,
    color: "#1C1C1E",
  },
  passwordContainer: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 12,
    position: "relative",
  },
  eyeIcon: {
    position: "absolute",
    right: 12,
    height: "100%",
    justifyContent: "center",
  },
  saveButton: {
    backgroundColor: "#007AFF",
    paddingVertical: 12,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 10,
    flexDirection: "row",
    gap: 8,
  },
  saveButtonText: {
    color: "#FFFFFF",
    fontSize: 17,
    fontWeight: "600",
  },
});

export default S3ConfigSection;

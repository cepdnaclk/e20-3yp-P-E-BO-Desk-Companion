import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Image,
  Alert,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import { Ionicons } from "@expo/vector-icons";
import {
  getS3Config,
  saveS3Config,
  updateUserImageURL,
  getUserImageURL,
} from "../services/firebase";
import { getAuth } from "firebase/auth";
import AWS from "aws-sdk";

const S3ConfigSection = ({ onConfigSaved }) => {
  const [accessKey, setAccessKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [bucketName, setBucketName] = useState("");
  const [showSecret, setShowSecret] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [hasConfig, setHasConfig] = useState(false);

  const [image, setImage] = useState(null);
  const [uploading, setUploading] = useState(false);

  const user = getAuth().currentUser;

  useEffect(() => {
    const loadData = async () => {
      try {
        const config = await getS3Config();
        if (config && config.accessKey) {
          setAccessKey(config.accessKey);
          setSecretKey(config.secretKey);
          setBucketName(config.bucketName);
          setHasConfig(true);
        }

        if (user) {
          const imageUrl = await getUserImageURL(user.uid);
          if (imageUrl) setImage(imageUrl);
        }
      } catch (error) {
        console.error("Error loading config:", error);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  const handleSaveConfig = async () => {
    if (!accessKey || !secretKey || !bucketName) {
      alert("Please fill in all fields.");
      return;
    }

    setIsSaving(true);
    try {
      await saveS3Config({ accessKey, secretKey, bucketName });
      setHasConfig(true);
      onConfigSaved && onConfigSaved();
      alert("S3 configuration saved!");
    } catch (err) {
      alert("Error saving config: " + err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const pickImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      quality: 0.7,
    });

    if (!result.canceled && result.assets.length > 0) {
      const asset = result.assets[0];
      uploadToS3(asset.uri);
    }
  };

  const uploadToS3 = async (uri) => {
    if (!accessKey || !secretKey || !bucketName) {
      alert("Please configure S3 first.");
      return;
    }

    setUploading(true);

    try {
      const response = await fetch(uri);
      const blob = await response.blob();
      const fileExt = uri.split(".").pop();
      const fileName = `users/${user.uid}.${fileExt}`;

      AWS.config.update({
        accessKeyId: accessKey,
        secretAccessKey: secretKey,
        region: "us-east-1", // or your bucket region
      });

      const s3 = new AWS.S3();
      const params = {
        Bucket: bucketName,
        Key: fileName,
        Body: blob,
        ContentType: blob.type,
        ACL: "public-read",
      };

      s3.upload(params, async (err, data) => {
        if (err) {
          alert("Upload failed: " + err.message);
        } else {
          setImage(data.Location);
          await updateUserImageURL(user.uid, data.Location);
          Alert.alert("Success", "Image uploaded successfully.");
        }
        setUploading(false);
      });
    } catch (err) {
      alert("Upload failed: " + err.message);
      setUploading(false);
    }
  };

  if (isLoading) {
    return (
      <View style={styles.card}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text>Loading S3 Config...</Text>
      </View>
    );
  }

  return (
    <View style={styles.card}>
      <Text style={styles.cardLabel}>S3 Storage Configuration</Text>
      <Text style={styles.description}>
        Configure AWS S3 storage and upload a profile image.
      </Text>

      <TextInput
        placeholder="AWS Access Key"
        style={styles.input}
        value={accessKey}
        onChangeText={setAccessKey}
        autoCapitalize="none"
      />
      <View style={styles.passwordContainer}>
        <TextInput
          placeholder="AWS Secret Key"
          style={[styles.input, { flex: 1 }]}
          value={secretKey}
          onChangeText={setSecretKey}
          secureTextEntry={!showSecret}
          autoCapitalize="none"
        />
        <TouchableOpacity
          onPress={() => setShowSecret(!showSecret)}
          style={styles.eyeIcon}
        >
          <Ionicons name={showSecret ? "eye-off" : "eye"} size={22} />
        </TouchableOpacity>
      </View>
      <TextInput
        placeholder="S3 Bucket Name"
        style={styles.input}
        value={bucketName}
        onChangeText={setBucketName}
        autoCapitalize="none"
      />

      <TouchableOpacity style={styles.saveButton} onPress={handleSaveConfig}>
        {isSaving ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <>
            <Ionicons name="save" size={20} color="#fff" />
            <Text style={styles.saveButtonText}>
              {hasConfig ? "Update Config" : "Save Config"}
            </Text>
          </>
        )}
      </TouchableOpacity>

      {image && (
        <Image
          source={{ uri: image }}
          style={{ width: 100, height: 100, borderRadius: 10, marginTop: 20 }}
        />
      )}

      <TouchableOpacity
        style={[styles.saveButton, { marginTop: 10 }]}
        onPress={pickImage}
        disabled={uploading}
      >
        {uploading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <>
            <Ionicons name="cloud-upload" size={20} color="#fff" />
            <Text style={styles.saveButtonText}>Upload User Image</Text>
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

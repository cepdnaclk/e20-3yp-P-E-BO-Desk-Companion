import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  Image,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  FlatList,
  Modal,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { getPeboImageHistory } from "../services/firebase";

const PeboImageHistory = ({ peboId, peboName }) => {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState(null);
  const [modalVisible, setModalVisible] = useState(false);

  useEffect(() => {
    loadImages();
  }, [peboId]);

  const loadImages = async () => {
    if (!peboId) return;

    setLoading(true);
    try {
      const imageHistory = await getPeboImageHistory(peboId);
      setImages(imageHistory);
    } catch (error) {
      console.error("Error loading images:", error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
  };

  const handleImagePress = (image) => {
    setSelectedImage(image);
    setModalVisible(true);
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="small" color="#007AFF" />
        <Text style={styles.loadingText}>Loading images...</Text>
      </View>
    );
  }

  if (images.length === 0) {
    return (
      <View style={styles.emptyContainer}>
        <Ionicons name="images-outline" size={40} color="#999" />
        <Text style={styles.emptyText}>No images yet</Text>
      </View>
    );
  }

  const renderImageItem = ({ item }) => (
    <TouchableOpacity
      style={styles.imageCard}
      onPress={() => handleImagePress(item)}
    >
      <Image source={{ uri: item.url }} style={styles.thumbnail} />
      <Text style={styles.timestamp}>{formatDate(item.timestamp)}</Text>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{peboName} Images</Text>

      <FlatList
        data={images}
        renderItem={renderImageItem}
        keyExtractor={(item) => item.id}
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.imageList}
      />

      <Modal
        animationType="fade"
        transparent={true}
        visible={modalVisible}
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            {selectedImage && (
              <>
                <Image
                  source={{ uri: selectedImage.url }}
                  style={styles.fullImage}
                  resizeMode="contain"
                />
                <Text style={styles.modalTimestamp}>
                  {formatDate(selectedImage.timestamp)}
                </Text>
              </>
            )}
            <TouchableOpacity
              style={styles.closeButton}
              onPress={() => setModalVisible(false)}
            >
              <Ionicons name="close-circle" size={32} color="#fff" />
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      <TouchableOpacity style={styles.refreshButton} onPress={loadImages}>
        <Ionicons name="refresh" size={20} color="#fff" />
        <Text style={styles.refreshButtonText}>Refresh Images</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: 10,
  },
  title: {
    fontSize: 18,
    fontWeight: "600",
    marginBottom: 10,
    color: "#1C1C1E",
  },
  imageList: {
    paddingVertical: 10,
  },
  imageCard: {
    marginRight: 12,
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 8,
    shadowColor: "#000",
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  thumbnail: {
    width: 120,
    height: 90,
    borderRadius: 8,
  },
  timestamp: {
    fontSize: 11,
    color: "#666",
    marginTop: 5,
    textAlign: "center",
  },
  loadingContainer: {
    padding: 20,
    alignItems: "center",
    justifyContent: "center",
  },
  loadingText: {
    color: "#666",
    marginTop: 8,
  },
  emptyContainer: {
    padding: 20,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#f9f9f9",
    borderRadius: 12,
  },
  emptyText: {
    color: "#666",
    marginTop: 8,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.8)",
    justifyContent: "center",
    alignItems: "center",
  },
  modalContent: {
    width: "90%",
    maxHeight: "80%",
    backgroundColor: "#000",
    borderRadius: 16,
    padding: 16,
    alignItems: "center",
  },
  fullImage: {
    width: "100%",
    height: 300,
    borderRadius: 8,
  },
  modalTimestamp: {
    color: "#fff",
    marginTop: 10,
    fontSize: 14,
  },
  closeButton: {
    position: "absolute",
    top: 10,
    right: 10,
  },
  refreshButton: {
    flexDirection: "row",
    backgroundColor: "#5856D6",
    padding: 10,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 10,
    alignSelf: "flex-start",
  },
  refreshButtonText: {
    color: "#fff",
    marginLeft: 6,
    fontWeight: "600",
  },
});

export default PeboImageHistory;

#!/usr/bin/env python3
import boto3
import os
from PIL import Image
import time
import tempfile
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64

def decrypt_image(input_path, output_path, key):
    try:
        aesgcm = AESGCM(key)
        with open(input_path, 'rb') as f:
            data = f.read()
        nonce = data[:12]
        ciphertext = data[12:]
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        with open(output_path, 'wb') as f:
            f.write(plaintext)
        # ~ print(f"Decrypted {input_path} to {output_path}")
        print ("********Decrypted********")
    except Exception as e:
        raise Exception(f"Decryption error: {e}")

def recognize_image():
    ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
    SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    REGION = os.getenv("AWS_REGION")
    AES_KEY = os.getenv("AES_KEY")
    bucket_name = "pebo-user-images"
    image_name = "captured.jpg"
    encrypted_image_path = "/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/captured.jpg.enc"
    max_image_age = 20

    if not AES_KEY:
        key_file = "/home/pi/.pebo_key"
        if os.path.exists(key_file):
            with open(key_file, 'r') as f:
                AES_KEY = f.read().strip()
        else:
            print("AES_KEY not set.")
            return {"name": "NONE", "emotion": "NONE"}

    try:
        if isinstance(AES_KEY, bytes):
            aes_key_bytes = AES_KEY
        else:
            aes_key_bytes = AES_KEY.encode()
        aes_key = base64.b64decode(aes_key_bytes)
        if len(aes_key) != 32:
            raise ValueError("AES key must be 32 bytes")
    except Exception as e:
        print(f"Invalid AES key: {e}")
        return {"name": "NONE", "emotion": "NONE"}

    try:
        if not os.path.exists(encrypted_image_path):
            print(f"Encrypted image not found at {encrypted_image_path}")
            return {"name": "NONE", "emotion": "NONE"}
        image_creation_time = os.path.getctime(encrypted_image_path)
        current_time = time.time()
        image_age = current_time - image_creation_time
        if image_age > max_image_age:
            print(f"Encrypted image is too old ({image_age:.1f}s > {max_image_age}s)")
            return {"name": "NONE", "emotion": "NONE"}
    except Exception as e:
        print(f"Image access error: {e}")
        return {"name": "NONE", "emotion": "NONE"}

    try:
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_image_path = temp_file.name
        decrypt_image(encrypted_image_path, temp_image_path, aes_key)
    except Exception as e:
        print(f"Decryption error: {e}")
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        return {"name": "NONE", "emotion": "NONE"}

    try:
        with Image.open(temp_image_path) as img:
            if img.format != "JPEG":
                raise Exception("Image is not a valid JPEG")
    except Exception as e:
        print(f"Image validation error: {e}")
        os.remove(temp_image_path)
        return {"name": "NONE", "emotion": "NONE"}

    try:
        rekognition = boto3.client('rekognition', region_name=REGION,
                                  aws_access_key_id=ACCESS_KEY,
                                  aws_secret_access_key=SECRET_KEY)
        s3 = boto3.client('s3', region_name=REGION,
                         aws_access_key_id=ACCESS_KEY,
                         aws_secret_access_key=SECRET_KEY)
    except Exception as e:
        print(f"AWS client initialization error: {e}")
        os.remove(temp_image_path)
        return {"name": "NONE", "emotion": "NONE"}

    try:
        s3.upload_file(temp_image_path, bucket_name, image_name, ExtraArgs={'ContentType': 'image/jpeg'})
        print("Image uploaded successfully")
    except Exception as e:
        print(f"Upload error: {e}")
        os.remove(temp_image_path)
        return {"name": "NONE", "emotion": "NONE"}

    try:
        os.remove(temp_image_path)
    except Exception as e:
        print(f"Error removing temporary file: {e}")

    try:
        face_check = rekognition.detect_faces(
            Image={'S3Object': {'Bucket': bucket_name, 'Name': image_name}},
            Attributes=['DEFAULT']
        )
        if len(face_check['FaceDetails']) != 1:
            print("Image must contain exactly one face")
            return {"name": "NONE", "emotion": "NONE"}
    except Exception as e:
        print(f"Face detection error: {e}")
        return {"name": "NONE", "emotion": "NONE"}

    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix='')
        best_match = None
        highest_similarity = 0
        for obj in response.get('Contents', []):
            reference_image = obj['Key']
            if reference_image == image_name:
                continue
            try:
                result = rekognition.compare_faces(
                    SourceImage={'S3Object': {'Bucket': bucket_name, 'Name': reference_image}},
                    TargetImage={'S3Object': {'Bucket': bucket_name, 'Name': image_name}},
                    SimilarityThreshold=80
                )
                if result['FaceMatches']:
                    similarity = result['FaceMatches'][0]['Similarity']
                    if similarity > highest_similarity:
                        highest_similarity = similarity
                        best_match = reference_image
            except Exception:
                continue
        if best_match:
            emotion_data = rekognition.detect_faces(
                Image={'S3Object': {'Bucket': bucket_name, 'Name': image_name}},
                Attributes=['ALL']
            )
            emotions = emotion_data['FaceDetails'][0].get('Emotions', [])
            top_emotion = sorted(emotions, key=lambda x: x['Confidence'], reverse=True)[0]['Type'] if emotions else "NONE"
            name = best_match.replace("user_", "").replace(".jpg", "")
            return {"name": name, "emotion": top_emotion}
        else:
            return {"name": "NONE", "emotion": "NONE"}
    except Exception as e:
        print(f"Recognition error: {e}")
        return {"name": "NONE", "emotion": "NONE"}

if __name__ == "__main__":
    result = recognize_image()
    print(result)

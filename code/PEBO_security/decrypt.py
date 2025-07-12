# Decrypt
with open("user_image_encrypted.bin", "rb") as f:
    encrypted_data = f.read()

decrypted_data = cipher.decrypt(encrypted_data)

# Pass to AWS Rekognition as bytes
import boto3

client = boto3.client('rekognition', region_name='your-region')

response = client.detect_faces(
    Image={'Bytes': decrypted_data},
    Attributes=['ALL']
)

print(response)

from cryptography.fernet import Fernet

# Key setup (store securely)
key = Fernet.generate_key()
cipher = Fernet(key)

# Encrypt
with open("user_image.jpg", "rb") as f:
    encrypted_data = cipher.encrypt(f.read())

with open("user_image_encrypted.bin", "wb") as f:
    f.write(encrypted_data)

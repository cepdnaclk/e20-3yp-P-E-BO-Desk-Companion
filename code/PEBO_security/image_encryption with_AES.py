import io
import os
from PIL import Image
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from base64 import b64encode, b64decode

def encrypt_image(image_path, key=None):
    """
    Encrypts an image using AES-256-CBC
    
    Args:
        image_path: Path to the source image
        key: Optional encryption key (will generate one if not provided)
        
    Returns:
        (encrypted_data, key, iv): Tuple containing encrypted data and encryption parameters
    """
    # Generate a random key if not provided
    if key is None:
        key = get_random_bytes(32)  # 256-bit key for AES-256
    
    # Read image and convert to bytes
    with Image.open(image_path) as img:
        # Convert image to RGB if it has an alpha channel
        if img.mode == 'RGBA':
            img = img.convert('RGB')
            
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        raw_data = img_bytes.getvalue()
    
    # Create cipher and encrypt
    iv = get_random_bytes(16)  # Initialization vector
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_data = cipher.encrypt(pad(raw_data, AES.block_size))
    
    return encrypted_data, key, iv

def decrypt_image(encrypted_data, key, iv):
    """
    Decrypts an image that was encrypted with AES-256-CBC
    
    Args:
        encrypted_data: The encrypted image data
        key: The encryption key
        iv: The initialization vector
        
    Returns:
        PIL Image object
    """
    # Create cipher and decrypt
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
    
    # Convert back to image
    img = Image.open(io.BytesIO(decrypted_data))
    return img

def encrypt_and_save(image_path, output_path):
    """Encrypts an image and saves encryption parameters to files"""
    encrypted_data, key, iv = encrypt_image(image_path)
    
    # Save encrypted image
    with open(output_path, 'wb') as f:
        f.write(encrypted_data)
    
    # Save encryption key and IV (in practice, handle these securely!)
    with open(output_path + '.key', 'wb') as f:
        f.write(key)
    
    with open(output_path + '.iv', 'wb') as f:
        f.write(iv)
    
    return key, iv

def prepare_for_transmission(image_path):
    """
    Prepares an encrypted image for transmission
    Returns a single base64 string containing all needed data
    """
    encrypted_data, key, iv = encrypt_image(image_path)
    
    # Create a package containing all needed components
    package = {
        'encrypted_data': b64encode(encrypted_data).decode('utf-8'),
        'key': b64encode(key).decode('utf-8'),
        'iv': b64encode(iv).decode('utf-8')
    }
    
    # In a real system, you would encrypt the key with the recipient's
    # public key, or use a key management service
    
    return package

# Example usage:
if __name__ == "__main__":
    # Capture image
    import picamera
    
    # Create a temporary file to store the captured image
    image_path = "captured_image.jpg"
    encrypted_path = "encrypted_image.bin"
    
    # Capture the image
    with picamera.PiCamera() as camera:
        camera.resolution = (1024, 768)
        camera.capture(image_path)
    
    # Encrypt the image
    key, iv = encrypt_and_save(image_path, encrypted_path)
    
    print(f"Image encrypted and saved to {encrypted_path}")
    print(f"Encryption key and IV saved to {encrypted_path}.key and {encrypted_path}.iv")
    
    # For a real system with AWS, you'd use AWS KMS to manage keys securely
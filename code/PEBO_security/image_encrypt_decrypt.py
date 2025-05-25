from PIL import Image
import sys

# Encrypt or decrypt image using XOR
def xor_image(file_path, key, output_path):
    img = Image.open(file_path)
    data = bytearray(img.tobytes())

    for i in range(len(data)):
        data[i] ^= key

    encrypted_img = Image.frombytes(img.mode, img.size, bytes(data))
    encrypted_img.save(output_path)

# Example usage
if __name__ == "__main__":
    mode = sys.argv[1]  # "encrypt" or "decrypt"
    input_file = sys.argv[2]
    output_file = sys.argv[3]
    xor_key = int(sys.argv[4])  # e.g., 123

    xor_image(input_file, xor_key, output_file)

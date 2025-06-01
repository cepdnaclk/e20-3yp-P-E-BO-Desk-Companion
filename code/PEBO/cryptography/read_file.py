import os

import base64

aes_key = os.getenv("AES_KEY")
print(f"AES_KEY type: {type(aes_key)}, value: {aes_key}")
aes_key_bytes = aes_key if isinstance(aes_key, bytes) else aes_key.encode()
key = base64.b64decode(aes_key_bytes)
print(f"Key: {key.hex()}, length: {len(key)}")

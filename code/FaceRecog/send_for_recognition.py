import requests
import json

API_URL = "https://your-api-gateway.amazonaws.com/prod/recognize-user"

def recognize_user(image_name):
    payload = {"bucket": "pebo-user-images", "image_name": image_name}
    response = requests.post(API_URL, json=payload)
    return response.json()

image_name = "user_image.jpg"
result = recognize_user(image_name)
print("Recognition Result:", result)

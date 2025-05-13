import boto3
import os
from picamera2 import Picamera2
from time import sleep

# AWS Rekognition Client
rekognition = boto3.client('rekognition')

# Define S3 Bucket and Image Names
bucket_name = "pebo-user-images"
captured_image = "captured.jpg"  # Newly captured image

# AWS S3 Configuration
#ACCESS_KEY = "AKIATTSKFOHRLPXVE5PM"
#SECRET_KEY = "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"
ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
REGION = os.getenv("AWS_REGION")

LOCAL_IMAGE_PATH = f"/home/pi/Documents/PEBO_project_aws/{captured_image}"

# Initialize Camera
camera = Picamera2()

# Function to capture and upload the image
def capture_and_upload():
    camera.start()
    sleep(2)
    camera.capture_file(LOCAL_IMAGE_PATH)
    camera.stop_preview()
    print("Image Captured.")

    s3_client = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)
    s3_client.upload_file(LOCAL_IMAGE_PATH, bucket_name, captured_image)
    print(f"Image uploaded to S3 bucket: {bucket_name}/{captured_image}")

# Function to extract the first emotion from Rekognition's response
def get_first_emotion_from_response(response):
    # Check if the response contains face details
    if 'FaceDetails' in response and len(response['FaceDetails']) > 0:
        # Loop through each face detected in the response
        for face in response['FaceDetails']:
            if 'Emotions' in face and len(face['Emotions']) > 0:
                # Sort emotions by confidence in descending order and get the first one
                emotions_sorted = sorted(face['Emotions'], key=lambda x: x['Confidence'], reverse=True)
                first_emotion = emotions_sorted[0]['Type']
                return first_emotion
    return "No emotions detected"

# Function to recognize the user by comparing faces
def recognize_user():
    try:
        # List all reference images in the S3 bucket (assuming they are prefixed with 'user_')
        s3_client = boto3.client('s3')
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix='user_')  # Adjust prefix as needed
        
        # Variables to store the best match info
        best_match_image = None
        highest_similarity = 0

        # Iterate over all reference images
        for item in response.get('Contents', []):
            reference_image = item['Key']
            if reference_image == captured_image:  # Skip the captured image
                continue

            # Call AWS Rekognition to compare faces
            compare_response = rekognition.compare_faces(
                SourceImage={'S3Object': {'Bucket': bucket_name, 'Name': reference_image}},
                TargetImage={'S3Object': {'Bucket': bucket_name, 'Name': captured_image}},
                SimilarityThreshold=80  # Set the match confidence threshold (adjust as needed)
            )

            # Check if there is a match
            if compare_response['FaceMatches']:
                match_confidence = compare_response['FaceMatches'][0]['Similarity']
                print(f"Match Found with {reference_image}: {match_confidence:.2f}%")

                # Keep track of the highest match
                if match_confidence > highest_similarity:
                    highest_similarity = match_confidence
                    best_match_image = reference_image

        # If a match is found
        if best_match_image:
            print(f"\nMatch: {best_match_image} with {highest_similarity:.2f}% similarity")
            # Perform emotion detection on the captured image
            emotion_response = rekognition.detect_faces(
                Image={'S3Object': {'Bucket': bucket_name, 'Name': captured_image}},
                Attributes=['ALL']  # Ensure emotion detection is included
            )
            first_emotion = get_first_emotion_from_response(emotion_response)
            print(f"First Detected Emotion: {first_emotion}")
            
            return {"match": True, "reference_image": best_match_image, "confidence": highest_similarity, "emotion": first_emotion}
        else:
            # If no match is found, ask the user for their name
            name = input("No match found. Please enter your name: ")
            new_image_name = f"user_{name}.jpg"

            # Rename the captured image to user_<name>.jpg
            s3_client.upload_file(LOCAL_IMAGE_PATH, bucket_name, new_image_name)
            print(f"Image uploaded as new user: {new_image_name}")
            return {"match": False, "new_image_name": new_image_name}

    except Exception as e:
        print(f"⚠️ Error: {e}")
        return {"match": False, "error": str(e)}

# Run the function to capture, upload, and recognize
capture_and_upload()
sleep(2)
result = recognize_user()
print(result)
 
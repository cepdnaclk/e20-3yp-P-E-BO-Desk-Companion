import boto3

# AWS Rekognition Client
rekognition = boto3.client('rekognition')

# Define S3 Bucket and Image
bucket_name = "pebo-user-images"
image_name = "captured.jpg"

# Call AWS Rekognition for face analysis
response = rekognition.detect_faces(
    Image={'S3Object': {'Bucket': bucket_name, 'Name': image_name}},
    Attributes=['ALL']  # Ensures emotion detection is included
)

# Function to get the first emotion from the response
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

# Get the first emotion from the response
first_emotion = get_first_emotion_from_response(response)

# Print the first emotion detected
print(f"{first_emotion}")


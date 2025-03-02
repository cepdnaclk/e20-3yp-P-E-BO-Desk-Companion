import boto3

# Initialize Rekognition Client
rekognition = boto3.client('rekognition')

# Define S3 Bucket and Image
bucket_name = "pebo-user-images"
image_name = "captured.jpg"

# Call AWS Rekognition for face analysis
response = rekognition.detect_faces(
    Image={'S3Object': {'Bucket': bucket_name, 'Name': image_name}},
    Attributes=['ALL']  # Ensures emotion detection is included
)

# Print the Response
print(response)

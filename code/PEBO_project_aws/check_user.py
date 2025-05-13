import boto3
from picamera2 import Picamera2
from time import sleep

# AWS Rekognition Client
rekognition = boto3.client('rekognition')

# Define S3 Bucket and Image Names
bucket_name = "pebo-user-images"
captured_image = "captured.jpg"  # Newly captured image

# AWS S3 Configuration
ACCESS_KEY = "AKIATTSKFOHRLPXVE5PM"
SECRET_KEY = "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"
LOCAL_IMAGE_PATH = f"/home/pi/Documents/PEBO_project_aws/{captured_image}"


camera = Picamera2()

def capture_and_upload():
    camera.start()
    sleep(2)
    camera.capture_file(LOCAL_IMAGE_PATH)
    camera.stop_preview()
    print("Image Captured.")

    s3_client = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)
    s3_client.upload_file(LOCAL_IMAGE_PATH, bucket_name, captured_image)

    print(f"Image uploaded to S3 bucket: {bucket_name}/{captured_image}")


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
            # print(f"Match Found with {reference_image}")
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

        # Print the best match
        if best_match_image:
            print(f"\nMatch: {best_match_image} with {highest_similarity:.2f}% similarity")
            return {"match": True, "reference_image": best_match_image, "confidence": highest_similarity}
        else:
            print("No Match Found.")
            return {"match": False}

    except Exception as e:
        print(f"⚠️ Error: {e}")
        return {"match": False, "error": str(e)}

# Run the function
capture_and_upload()
sleep(2)
recognize_user()

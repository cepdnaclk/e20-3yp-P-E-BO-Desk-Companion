import boto3

# AWS Rekognition Client
rekognition = boto3.client('rekognition')

# Define S3 Bucket and Image Names
bucket_name = "pebo-user-images"
reference_image = "user_reference.jpg"  # Pre-uploaded reference image
captured_image = "captured.jpg"  # Newly captured image

def recognize_user():
    try:
        # Call AWS Rekognition to compare faces
        response = rekognition.compare_faces(
            SourceImage={'S3Object': {'Bucket': bucket_name, 'Name': reference_image}},
            TargetImage={'S3Object': {'Bucket': bucket_name, 'Name': captured_image}},
            SimilarityThreshold=80  # Set the match confidence threshold (adjust as needed)
        )

        # Process the response
        if response['FaceMatches']:
            match_confidence = response['FaceMatches'][0]['Similarity']
            print(f"✅ Match Found! Similarity: {match_confidence:.2f}%")
            return {"match": True, "confidence": match_confidence}
        else:
            print("❌ No Match Found.")
            return {"match": False}

    except Exception as e:
        print(f"⚠️ Error: {e}")
        return {"match": False, "error": str(e)}

# Run the function
recognize_user()

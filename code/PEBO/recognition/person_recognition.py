import boto3
import os
from PIL import Image

def recognize_from_existing_image():
    ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
    SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    REGION = os.getenv("AWS_REGION")
    bucket_name = "pebo-user-images"
    image_name = "captured.jpg"
    local_image_path = f"/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/{image_name}"

    # Initialize clients
    rekognition = boto3.client('rekognition', region_name=REGION,
                               aws_access_key_id=ACCESS_KEY,
                               aws_secret_access_key=SECRET_KEY)
    s3 = boto3.client('s3', region_name=REGION,
                      aws_access_key_id=ACCESS_KEY,
                      aws_secret_access_key=SECRET_KEY)

    # Check if image exists and is valid
    try:
        with Image.open(local_image_path) as img:
            if img.format != "JPEG":
                raise Exception("Image is not a valid JPEG")
    except Exception as e:
        print(f"Image validation error: {e}")
        return {"name": "NONE", "emotion": "NONE"}

    # Upload image
    try:
        s3.upload_file(local_image_path, bucket_name, image_name, ExtraArgs={'ContentType': 'image/jpeg'})
        print("Image uploaded successfully.")
    except Exception as e:
        print(f"Upload error: {e}")
        return {"name": "NONE", "emotion": "NONE"}

    # Check that exactly one face is in the image
    try:
        face_check = rekognition.detect_faces(
            Image={'S3Object': {'Bucket': bucket_name, 'Name': image_name}},
            Attributes=['DEFAULT']
        )
        if len(face_check['FaceDetails']) != 1:
            print("Image must contain exactly one face.")
            return {"name": "NONE", "emotion": "NONE"}
    except Exception as e:
        print(f"Face detection error: {e}")
        return {"name": "NONE", "emotion": "NONE"}

    # Match with known users
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix='user_')
        best_match = None
        highest_similarity = 0

        for obj in response.get('Contents', []):
            reference_image = obj['Key']
            if reference_image == image_name:
                continue
            try:
                result = rekognition.compare_faces(
                    SourceImage={'S3Object': {'Bucket': bucket_name, 'Name': reference_image}},
                    TargetImage={'S3Object': {'Bucket': bucket_name, 'Name': image_name}},
                    SimilarityThreshold=80
                )
                if result['FaceMatches']:
                    similarity = result['FaceMatches'][0]['Similarity']
                    if similarity > highest_similarity:
                        highest_similarity = similarity
                        best_match = reference_image
            except Exception as e:
                print(f"Comparison error with {reference_image}: {e}")
                continue

        if best_match:
            emotion_data = rekognition.detect_faces(
                Image={'S3Object': {'Bucket': bucket_name, 'Name': image_name}},
                Attributes=['ALL']
            )
            emotions = emotion_data['FaceDetails'][0].get('Emotions', [])
            top_emotion = sorted(emotions, key=lambda x: x['Confidence'], reverse=True)[0]['Type'] if emotions else "NONE"
            name = best_match.replace("user_", "").replace(".jpg", "")
            return {"name": name, "emotion": top_emotion}
        else:
            return {"name": "NONE", "emotion": "NONE"}

    except Exception as e:
        print(f"Recognition error: {e}")
        return {"name": "NONE", "emotion": "NONE"}

if __name__ == "__main__":
    result = recognize_from_existing_image()
    print(result)

import boto3
import os
from picamera2 import Picamera2
from time import sleep
from PIL import Image

def recognize_person():
    ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
    SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    REGION = os.getenv("AWS_REGION")
    bucket_name = "pebo-user-images"
    captured_image = "captured.jpg"
    LOCAL_IMAGE_PATH = f"/home/pi/Documents/GitHub/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/interaction/{captured_image}"

    rekognition = boto3.client('rekognition', region_name=REGION,
                              aws_access_key_id=ACCESS_KEY,
                              aws_secret_access_key=SECRET_KEY)
    s3_client = boto3.client('s3', region_name=REGION,
                            aws_access_key_id=ACCESS_KEY,
                            aws_secret_access_key=SECRET_KEY)
    camera = Picamera2()

    # Capture image
    try:
        camera.start()
        sleep(2)
        camera.capture_file(LOCAL_IMAGE_PATH, format='jpeg')
        camera.stop()
        camera.close()
        del camera
        if not os.path.exists(LOCAL_IMAGE_PATH) or os.path.getsize(LOCAL_IMAGE_PATH) < 1000:
            raise Exception("Captured image is invalid or too small")
        print("Image Captured.")
    except Exception as e:
        print(f"Error capturing image: {e}")
        return {"name": None, "emotion": None, "error": str(e)}

    # Validate image format
    try:
        with Image.open(LOCAL_IMAGE_PATH) as img:
            print(f"Image format: {img.format}, Size: {img.size}")
            if img.format != "JPEG":
                raise Exception("Image is not a valid JPEG")
    except Exception as e:
        print(f"Invalid image: {e}")
        return {"name": None, "emotion": None, "error": str(e)}

    # Upload to S3
    try:
        s3_client.upload_file(
            LOCAL_IMAGE_PATH,
            bucket_name,
            captured_image,
            ExtraArgs={'ContentType': 'image/jpeg'}
        )
        print(f"Image uploaded to S3 bucket: {bucket_name}/{captured_image}")
        s3_client.head_object(Bucket=bucket_name, Key=captured_image)
        print(f"Confirmed: {captured_image} exists in S3 bucket.")
    except s3_client.exceptions.ClientError as e:
        print(f"Error uploading to S3: {e}")
        return {"name": None, "emotion": None, "error": str(e)}

    def validate_image(bucket, key):
        try:
            response = rekognition.detect_faces(
                Image={'S3Object': {'Bucket': bucket, 'Name': key}},
                Attributes=['DEFAULT']
            )
            if len(response['FaceDetails']) != 1:
                print(f"Image {key} has {len(response['FaceDetails'])} faces, expected 1")
                return False
            return True
        except Exception as e:
            print(f"Error validating {key}: {e}")
            return False

    def get_first_emotion_from_response(response):
        if 'FaceDetails' in response and len(response['FaceDetails']) > 0:
            for face in response['FaceDetails']:
                if 'Emotions' in face and len(face['Emotions']) > 0:
                    emotions_sorted = sorted(face['Emotions'], key=lambda x: x['Confidence'], reverse=True)
                    return emotions_sorted[0]['Type']
        return "No emotions detected"

    # Validate captured image
    if not validate_image(bucket_name, captured_image):
        print("Captured image is invalid for face recognition")
        return {"name": None, "emotion": None, "error": "Invalid captured image"}

    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix='user_')
        best_match_image = None
        highest_similarity = 0

        for item in response.get('Contents', []):
            reference_image = item['Key']
            #if reference_image == captured_image:
            #    continue
            #if not validate_image(bucket_name, reference_image):
            #    print(f"Skipping invalid reference image: {reference_image}")
            #    continue
            try:
                compare_response = rekognition.compare_faces(
                    SourceImage={'S3Object': {'Bucket': bucket_name, 'Name': reference_image}},
                    TargetImage={'S3Object': {'Bucket': bucket_name, 'Name': captured_image}},
                    SimilarityThreshold=80
                )
                if compare_response['FaceMatches']:
                    match_confidence = compare_response['FaceMatches'][0]['Similarity']
                    if match_confidence > highest_similarity:
                        highest_similarity = match_confidence
                        best_match_image = reference_image
            except rekognition.exceptions.InvalidParameterException as e:
                print(f"Error comparing with {reference_image}: {e}")
                continue

        if best_match_image:
            emotion_response = rekognition.detect_faces(
                Image={'S3Object': {'Bucket': bucket_name, 'Name': captured_image}},
                Attributes=['ALL']
            )
            first_emotion = get_first_emotion_from_response(emotion_response)
            matched_name = best_match_image.replace("user_", "").replace(".jpg", "")
            return {"name": matched_name, "emotion": first_emotion}
        else:
            name = input("No match found. Please enter your name: ")
            new_image_name = f"user_{name}.jpg"
            s3_client.upload_file(LOCAL_IMAGE_PATH, bucket_name, new_image_name)
            print(f"Image uploaded as new user: {new_image_name}")
            return {"name": None, "emotion": None}

    except Exception as e:
        print(f"?? Error: {e.response['Error']['Message'] if hasattr(e, 'response') else e}")
        return {"name": None, "emotion": None, "error": str(e)}

if __name__ == "__main__":
    result = recognize_person()
    print(result)

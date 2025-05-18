import boto3
import os
from picamera2 import Picamera2
from time import sleep

def recognize_person():
    ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
    SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    REGION = os.getenv("AWS_REGION")
    bucket_name = "pebo-user-images"
    captured_image = "captured.jpg"
    LOCAL_IMAGE_PATH = f"/home/pi/Documents/e20-3yp-P-E-BO-Desk-Companion/code/PEBO/interaction/{captured_image}"

    rekognition = boto3.client('rekognition', region_name=REGION,
                               aws_access_key_id=ACCESS_KEY,
                               aws_secret_access_key=SECRET_KEY)
    s3_client = boto3.client('s3', region_name=REGION,
                             aws_access_key_id=ACCESS_KEY,
                             aws_secret_access_key=SECRET_KEY)
    camera = Picamera2()

    # Capture image
    camera.start()
    sleep(2)
    camera.capture_file(LOCAL_IMAGE_PATH)
    camera.stop()
    camera.close()  # ? Proper hardware release
    del camera  # ? Fully release the camera resource
    print("Image Captured.")

    s3_client.upload_file(LOCAL_IMAGE_PATH, bucket_name, captured_image)
    print(f"Image uploaded to S3 bucket: {bucket_name}/{captured_image}")

    def get_first_emotion_from_response(response):
        if 'FaceDetails' in response and len(response['FaceDetails']) > 0:
            for face in response['FaceDetails']:
                if 'Emotions' in face and len(face['Emotions']) > 0:
                    emotions_sorted = sorted(face['Emotions'], key=lambda x: x['Confidence'], reverse=True)
                    return emotions_sorted[0]['Type']
        return "No emotions detected"

    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix='user_')
        best_match_image = None
        highest_similarity = 0

        for item in response.get('Contents', []):
            reference_image = item['Key']
            if reference_image == captured_image:
                continue

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

        if best_match_image:
            emotion_response = rekognition.detect_faces(
                Image={'S3Object': {'Bucket': bucket_name, 'Name': captured_image}},
                Attributes=['ALL']
            )
            first_emotion = get_first_emotion_from_response(emotion_response)
            matched_name = best_match_image.replace("user_", "").replace(".jpg", "")
            return {"name": matched_name, "emotion": first_emotion}
        else:
            #name = input("No match found. Please enter your name: ")
            #new_image_name = f"user_{name}.jpg"
            #s3_client.upload_file(LOCAL_IMAGE_PATH, bucket_name, new_image_name)
            #print(f"Image uploaded as new user: {new_image_name}")
            return {"name": None, "emotion": None}

    except Exception as e:
        print(f"?? Error: {e}")
        return {"name": None, "emotion": None, "error": str(e)}

if __name__ == "__main__":
    result = recognize_person()
    print(result)


import speech_recognition as sr
from gtts import gTTS
import playsound
import google.generativeai as genai
import os

os.environ["GOOGLE_API_KEY"] = ""
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
# Function to capture speech from microphone
def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio)
            print("You said:", text)
            with open("conversation_log.txt", "a") as file:
                file.write("You: " + text + "\n")
            return text
        except sr.UnknownValueError:
            print("Sorry, I couldn't understand.")
            return None
        except sr.RequestError:
            print("Speech recognition service not available.")
            return None



def chat_with_gemini(prompt):
    model = genai.GenerativeModelAPI(model_name="gemini-1.5-flash")
    response = model.generate_content(prompt)
    
    response_text = response.text if hasattr(response, "text") else "Sorry, I couldn't generate a response."

    with open("conversation_log.txt", "a") as file:
        file.write("Gemini: " + response_text + "\n")

    return response_text



def speak(text):
    tts = gTTS(text=text, lang='en')
    tts.save("response.mp3")
    playsound.playsound("response.mp3")

while True:
    user_input = listen()
    if user_input:
        if user_input.lower() == "exit":
            print("Exiting...")
            break
        ai_response = chat_with_gemini(user_input)
        print("Gemini Response:", ai_response)
        speak(ai_response)

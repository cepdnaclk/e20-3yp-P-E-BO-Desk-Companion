# ~ import google.generativeai as genai
# ~ import asyncio

# ~ genai.configure(api_key="AIzaSyBFQ7s66MWXN-NVQ06rxAwni98FaY6K2xM")
# ~ model = genai.GenerativeModel("gemini-2.5-flash")

# ~ async def test_gemini():
    # ~ response = model.generate_content(
        # ~ [{"role": "user", "parts": ["Hello, I am User. How can you help me today?"]}],
        # ~ generation_config={"max_output_tokens": 100}
    # ~ )
    # ~ print(response.text)

# ~ asyncio.run(test_gemini())

# ~ import google.generativeai as genai

# ~ genai.configure(api_key="AIzaSyBFQ7s66MWXN-NVQ06rxAwni98FaY6K2xM")
# ~ print(list(genai.list_models()))

# pip install -U google-genai
import os
from google import genai

api_key = "AIzaSyBFQ7s66MWXN-NVQ06rxAwni98FaY6K2xM"

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Explain how AI works in a few words",
)
print(response.text)

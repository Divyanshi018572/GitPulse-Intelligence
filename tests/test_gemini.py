import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
print(f"Key exists: {bool(api_key)}")
print(f"Key starts with: {api_key[:10] if api_key else 'None'}")

client = genai.Client(api_key=api_key)
try:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="Say hello"
    )
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

import os
from dotenv import load_dotenv
import groq

load_dotenv()
client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))

try:
    for model in client.models.list().data:
        print(model.id)
except Exception as e:
    print(e)

import os
import logging
from google import genai
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

gemini_client = None
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    log.warning("GEMINI_API_KEY not set - AI features using Gemini will be disabled.")

groq_client = None
if GROQ_API_KEY:
    groq_client = AsyncGroq(api_key=GROQ_API_KEY)
else:
    log.warning("GROQ_API_KEY not set - Falling back to Gemini for all AI queries.")

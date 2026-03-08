import os
import logging
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger("uvicorn.error")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    print("⚠️  WARNING: OPENAI_API_KEY no está definido. Establécelo antes de usar el servidor.")

OPENAI_MODEL_TEXT = os.getenv("OPENAI_MODEL_TEXT", "gpt-4o-mini")
OPENAI_MODEL_JSON = os.getenv("OPENAI_MODEL_JSON", "gpt-4o-mini")

client = OpenAI(api_key=OPENAI_API_KEY)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200").split(",")
FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "../frontend/dist/consultia")

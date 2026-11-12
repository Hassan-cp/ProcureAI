import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# 1. Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# 2. Check API key
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY is missing from .env!")

# 3. Initialize Gemini model
llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    google_api_key=api_key,
    temperature=0,
)

# 4. Send a test question
print("Connecting to Gemini...")

response = llm.invoke(
    "What is MongoDB? Answer in one short sentence."
)

print("\nGemini Response:")
print(response.text)

import os
from pathlib import Path
from bson import ObjectId
from fastapi.encoders import jsonable_encoder

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from procurement_agent import ask_procurement


# ============================================================
# 1. ENVIRONMENT VARIABLES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

MONGO_URI = os.getenv("MONGO_READER_URI")

if not MONGO_URI:
    raise RuntimeError("MONGO_READER_URI is missing from .env")


# ============================================================
# 2. MONGODB CONNECTION
# ============================================================

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000,
)

db = client["procurement_db"]
collection = db["purchases"]


# ============================================================
# 3. FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="AI Procurement Assistant",
    description="AI-powered procurement analytics API",
    version="1.1.0",
)


# ============================================================
# 4. REQUEST MODEL
# ============================================================

class QuestionRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Procurement question in natural language",
    )


# ============================================================
# 5. HOME
# ============================================================

@app.get("/")
def home():
    return {
        "message": "AI Procurement Assistant API is running!"
    }


# ============================================================
# 6. HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


# ============================================================
# 7. PROCUREMENT STATISTICS
# ============================================================

@app.get("/api/stats")
def get_stats():
    try:
        total = collection.count_documents(
            {},
            maxTimeMS=30000,
        )

        return {
            "total_purchases": total
        }

    except PyMongoError:
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable",
        )


# ============================================================
# 8. TOTAL SPENDING
# ============================================================

@app.get("/api/total-spending")
def get_total_spending():
    try:
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_spending": {
                        "$sum": "$Total Price"
                    }
                }
            }
        ]

        results = list(
            collection.aggregate(
                pipeline,
                maxTimeMS=30000,
                allowDiskUse=False,
            )
        )

        total = (
            results[0]["total_spending"]
            if results
            else 0
        )

        return {
            "total_spending": round(total, 2),
            "currency": "USD",
        }

    except PyMongoError:
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable",
        )


# ============================================================
# 9. AI PROCUREMENT ASSISTANT
# ============================================================

@app.post("/api/ask")
def ask_ai(request: QuestionRequest):
    try:
        response = ask_procurement(
            request.question.strip()
        )

        # Convert MongoDB ObjectId to JSON-compatible strings
        safe_results = jsonable_encoder(
            response["results"],
            custom_encoder={
                ObjectId: str,
            },
        )

        return {
            "question": response["question"],
            "answer": response["answer"],
            "results": safe_results,
        }

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Unable to process this question",
        )

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="AI assistant temporarily unavailable",
        )
    
import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pymongo import MongoClient


# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

username = os.getenv("MONGO_READER_USERNAME")
password = os.getenv("MONGO_READER_PASSWORD")

if not username or not password:
    raise ValueError("MongoDB reader credentials are missing from .env")


# Create MongoDB connection
mongo_uri = (
    f"mongodb://{quote_plus(username)}:{quote_plus(password)}"
    "@127.0.0.1:27017/procurement_db?authSource=procurement_db"
)

client = MongoClient(
    mongo_uri,
    serverSelectionTimeoutMS=5000,
    socketTimeoutMS=10000,
)

database = client["procurement_db"]
collection = database["purchases"]


def get_total_records():
    """Return the number of procurement records."""
    return collection.count_documents({})


if __name__ == "__main__":
    try:
        client.admin.command("ping")

        print("Database connection: SUCCESS")
        print("User: procurement_reader")
        print(f"Total records: {get_total_records()}")

    finally:
        client.close()
        
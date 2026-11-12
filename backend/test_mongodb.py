import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pymongo import MongoClient

# Find project folder
BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env file
load_dotenv(BASE_DIR / ".env")

# Get MongoDB password
username = "admin"
password = os.getenv("MONGO_ROOT_PASSWORD")

if not password:
    raise ValueError("MONGO_ROOT_PASSWORD is missing from .env")

# Encode password safely
encoded_password = quote_plus(password)

# Create MongoDB connection URI
mongo_uri = (
    f"mongodb://{username}:{encoded_password}"
    "@127.0.0.1:27017/?authSource=admin"
)

print("Connecting to MongoDB...")

# Connect to MongoDB
client = MongoClient(
    mongo_uri,
    serverSelectionTimeoutMS=5000
)

try:
    # Test connection
    client.admin.command("ping")

    print("Successfully connected to MongoDB!")

    # Select database
    db = client["procurement_db"]

    print(f"Database selected: {db.name}")

finally:
    client.close()
    
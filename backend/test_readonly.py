import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError


# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

username = os.getenv("MONGO_READER_USERNAME")
password = os.getenv("MONGO_READER_PASSWORD")

if not username or not password:
    raise ValueError("MongoDB reader credentials are missing from .env")


# Connect using read-only credentials
mongo_uri = (
    f"mongodb://{quote_plus(username)}:{quote_plus(password)}"
    "@127.0.0.1:27017/procurement_db?authSource=procurement_db"
)

client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)

try:
    # Verify connection
    client.admin.command("ping")
    print("MongoDB connection: SUCCESS")

    # Read procurement records
    collection = client["procurement_db"]["purchases"]

    total = collection.count_documents({})

    print("Read-only user: procurement_reader")
    print(f"Total procurement records: {total}")

    # Verify that the account has no write permissions
    privileges = client["procurement_db"].command(
        {"connectionStatus": 1, "showPrivileges": True}
    )["authInfo"]["authenticatedUserPrivileges"]

    can_write = any(
        action in privilege["actions"]
        for privilege in privileges
        for action in ("insert", "update", "remove", "dropCollection")
    )

    print(f"Write permissions detected: {can_write}")

    if can_write:
        raise RuntimeError("Security check failed: user has write permissions!")

    print("Read-only security check: PASSED")

except PyMongoError as error:
    print(f"MongoDB error: {error}")

finally:
    client.close()
    
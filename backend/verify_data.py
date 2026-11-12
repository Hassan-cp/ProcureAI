import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pymongo import MongoClient

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

password = os.getenv("MONGO_ROOT_PASSWORD")

if not password:
    raise ValueError("MongoDB password is missing!")

mongo_uri = (
    f"mongodb://admin:{quote_plus(password)}"
    "@127.0.0.1:27017/?authSource=admin"
)

client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)

try:
    client.admin.command("ping")

    db = client["procurement_db"]
    collection = db["purchases"]

    # 1. Check number of documents
    count = collection.count_documents({})
    print(f"Total documents: {count}")

    # 2. Check sample document
    sample = collection.find_one(
        {},
        {
            "_id": 0,
            "Supplier Name": 1,
            "Total Price": 1,
            "Creation Date": 1,
        },
    )

    print("\nSample document:")
    print(sample)

    # 3. Check actual MongoDB data types
    pipeline = [
        {
            "$project": {
                "price_type": {"$type": "$Total Price"},
                "date_type": {"$type": "$Creation Date"},
            }
        },
        {
            "$group": {
                "_id": {
                    "price": "$price_type",
                    "date": "$date_type",
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"count": -1}},
    ]

    print("\nMongoDB data types:")
    for result in collection.aggregate(pipeline):
        print(result)

finally:
    client.close()
    
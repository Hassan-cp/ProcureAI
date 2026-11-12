import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from query_validator import validate_pipeline


# ============================================================
# 1. CONFIGURATION
# ============================================================

load_dotenv()

MONGO_URI = os.getenv("MONGO_READER_URI")

DATABASE_NAME = "procurement_db"
COLLECTION_NAME = "purchases"

MAX_EXECUTION_TIME_MS = 30000
MAX_RESULTS = 100


# ============================================================
# 2. DATABASE CONNECTION
# ============================================================

def get_collection():

    if not MONGO_URI:
        raise RuntimeError(
            "MONGO_READER_URI is missing from .env"
        )

    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
    )

    collection = client[DATABASE_NAME][COLLECTION_NAME]

    return client, collection


# ============================================================
# 3. PURCHASE DATE FILTER
# ============================================================

def filter_future_purchase_dates(pipeline):
    """
    Exclude future dates when sorting purchases
    from newest to oldest.

    This does not modify the database.
    """

    is_latest_purchase_query = any(
        isinstance(stage.get("$sort"), dict)
        and stage["$sort"].get("Purchase Date") == -1
        for stage in pipeline
    )

    if not is_latest_purchase_query:
        return pipeline

    # Get the current UTC date
    today = datetime.now(timezone.utc)

    # Filter out future purchase dates
    date_filter = {
        "$match": {
            "Purchase Date": {
                "$type": "date",
                "$lte": today,
            }
        }
    }

    # Apply the filter before sorting
    return [date_filter] + pipeline


# ============================================================
# 4. QUERY EXECUTOR
# ============================================================

def execute_query(pipeline):
    """
    Validate and execute a read-only MongoDB aggregation.

    Automatically filters future purchase dates
    when sorting purchases from newest to oldest.
    """

    # Validate the AI-generated pipeline
    safe_pipeline = validate_pipeline(pipeline)

    # Apply date filtering only when needed
    safe_pipeline = filter_future_purchase_dates(
        safe_pipeline
    )

    client, collection = get_collection()

    try:
        cursor = collection.aggregate(
            safe_pipeline,
            allowDiskUse=False,
            maxTimeMS=MAX_EXECUTION_TIME_MS,
            batchSize=MAX_RESULTS,
        )

        results = []

        for document in cursor:
            results.append(document)

            if len(results) >= MAX_RESULTS:
                break

        return results

    except PyMongoError as error:
        raise RuntimeError(
            f"MongoDB query execution failed: {error}"
        ) from error

    finally:
        client.close()


# ============================================================
# 5. TEST
# ============================================================

if __name__ == "__main__":

    test_pipeline = [
        {
            "$match": {
                "Purchase Date": {
                    "$ne": None
                }
            }
        },
        {
            "$sort": {
                "Purchase Date": -1
            }
        },
        {
            "$limit": 5
        }
    ]

    print("Testing MongoDB Purchase Date Filter...")

    try:
        results = execute_query(test_pipeline)

        print("SUCCESS: Query executed!")
        print(f"Returned {len(results)} results")

        for result in results:
            print({
                "Item Name": result.get("Item Name"),
                "Purchase Date": result.get("Purchase Date"),
            })

    except Exception as error:
        print("ERROR:", error)
        
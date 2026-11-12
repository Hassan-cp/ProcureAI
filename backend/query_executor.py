import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from query_validator import validate_pipeline


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

MONGO_URI = os.getenv("MONGO_READER_URI")

DATABASE_NAME = "procurement_db"
COLLECTION_NAME = "purchases"

MAX_EXECUTION_TIME_MS = 30000
MAX_RESULTS = 100


# ============================================================
# DATABASE CONNECTION
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
# QUERY EXECUTOR
# ============================================================

def execute_query(pipeline):
    """
    Validate and execute a read-only MongoDB aggregation.
    """

    # Validate the AI-generated pipeline
    safe_pipeline = validate_pipeline(pipeline)

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
# TEST
# ============================================================

if __name__ == "__main__":

    test_pipeline = [
        {
            "$group": {
                "_id": "$Supplier Name",
                "totalSpending": {
                    "$sum": "$Total Price"
                }
            }
        },
        {
            "$sort": {
                "totalSpending": -1
            }
        },
        {
            "$limit": 5
        }
    ]

    print("Testing MongoDB Query Executor...")

    try:
        results = execute_query(test_pipeline)

        print("SUCCESS: Query executed!")
        print(f"Returned {len(results)} results")

        for result in results:
            print(result)

    except Exception as error:
        print("ERROR:", error)

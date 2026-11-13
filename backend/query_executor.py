import os
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from query_validator import DATE_FIELDS, parse_iso_date, validate_pipeline


# ============================================================
# 1. CONFIGURATION
# ============================================================

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

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

def filter_future_purchase_dates(pipeline, now=None):
    """
    Exclude future dates when sorting purchases
    from newest to oldest.

    This does not modify the database.
    """

    # Track references through projection/group aliases. Filtering must happen
    # before $year/$max, while the original BSON date still exists.
    lineage = {"Purchase Date": True}

    def uses_purchase_date(expression):
        if isinstance(expression, str) and expression.startswith("$"):
            return lineage.get(expression[1:], False)
        if isinstance(expression, dict):
            return any(uses_purchase_date(v) for v in expression.values())
        if isinstance(expression, list):
            return any(uses_purchase_date(v) for v in expression)
        return False

    is_latest_purchase_query = False
    for stage in pipeline:
        if "$sort" in stage:
            is_latest_purchase_query |= any(
                direction == -1 and lineage.get(field, False)
                for field, direction in stage["$sort"].items()
            )
        if "$group" in stage:
            group = stage["$group"]
            is_latest_purchase_query |= any(
                isinstance(value, dict) and "$max" in value
                and uses_purchase_date(value["$max"])
                for value in group.values()
            )
            lineage = {key: uses_purchase_date(value) for key, value in group.items()}
        if "$project" in stage:
            project = stage["$project"]
            if all(type(v) is int and v == 0 for v in project.values()):
                lineage = {k: v for k, v in lineage.items() if k not in project}
            else:
                lineage = {
                    key: lineage.get(key, False) if type(value) is int and value == 1
                    else uses_purchase_date(value)
                    for key, value in project.items() if value != 0
                } | ({"_id": lineage.get("_id", False)} if "_id" not in project else {})

    if not is_latest_purchase_query:
        return pipeline

    # Get the current UTC date
    today = now or datetime.now(timezone.utc)

    # Filter out future purchase dates
    date_filter = {
        "$match": {
            "Purchase Date": {
                "$type": "date",
                "$gte": datetime(1900, 1, 1, tzinfo=timezone.utc),
                "$lte": today,
            }
        }
    }

    # Apply the filter before sorting
    return [date_filter] + pipeline


# ============================================================
# 4. QUERY EXECUTOR
# ============================================================

def convert_match_dates(content):
    """Convert date comparison literals only after pipeline validation."""
    for field, condition in content.items():
        if field in {"$and", "$or"}:
            for subcondition in condition:
                convert_match_dates(subcondition)
        elif field in DATE_FIELDS and isinstance(condition, dict):
            if set(condition) == {"$date"}:
                content[field] = parse_iso_date(condition["$date"])
                continue
            for operator, value in condition.items():
                if isinstance(value, dict) and set(value) == {"$date"}:
                    condition[operator] = parse_iso_date(value["$date"])
                elif operator in {"$in", "$nin"}:
                    condition[operator] = [
                        parse_iso_date(item["$date"]) if isinstance(item, dict) else item
                        for item in value
                    ]


def execute_query(pipeline):
    """
    Validate and execute a read-only MongoDB aggregation.

    Automatically filters future purchase dates
    when sorting purchases from newest to oldest.
    """

    # Validate the AI-generated pipeline
    safe_pipeline = validate_pipeline(pipeline)

    for stage in safe_pipeline:
        if "$match" in stage:
            convert_match_dates(stage["$match"])

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

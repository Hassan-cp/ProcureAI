import os
import re
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from pymongo import MongoClient


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

API_URL = "http://127.0.0.1:8001/api/ask"
MONGO_URI = os.getenv("MONGO_READER_URI")

if not MONGO_URI:
    raise RuntimeError("MONGO_READER_URI is missing")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
collection = client["procurement_db"]["purchases"]


# ============================================================
# TEST QUESTIONS
# ============================================================

TESTS = [
    ("Top suppliers", "Who are the top 5 suppliers by total spending?"),
    ("Top departments", "Which 5 departments have the highest total spending?"),
    ("Latest purchases", "Show the 5 most recently purchased items."),
    ("Total purchases", "How many purchases are in the database?"),
    ("Total spending", "What is the total spending?"),
    ("Fiscal years", "How much was spent in each fiscal year?"),
    ("Supplier filtering", "How many purchases were made from Staples?"),
    ("Department filtering", "How many purchases were made by the Department of Transportation?"),
    ("Most expensive items", "Show the 5 most expensive purchases."),
    ("Cheapest items", "Show the 5 cheapest purchases."),
    ("Average price", "What is the average total price per purchase?"),
    ("Missing values", "How many purchases have a missing total price?"),
    ("Item search", "Show 5 purchases containing toner in the item name."),
    ("Unclear question", "Tell me something interesting."),
    ("Unrelated question", "Who won the FIFA World Cup in 2022?"),
]


# ============================================================
# HELPERS
# ============================================================

def check_results(name, question, response):
    """
    Basic automated checks.

    These checks do not guarantee that every AI answer is correct.
    """

    answer = str(response.get("answer", ""))
    results = response.get("results", [])

    if not isinstance(results, list):
        return "FAIL", "Results must be a list"

    if not answer.strip():
        return "FAIL", "Empty AI answer"

    if name == "Latest purchases":
        today = datetime.now(timezone.utc).date()

        if not results:
            return "REVIEW", "No purchase records returned"

        for record in results:
            date_value = record.get("Purchase Date")

            if not date_value:
                return "REVIEW", "Missing purchase date"

            try:
                purchase_date = datetime.fromisoformat(
                    str(date_value).replace("Z", "+00:00")
                ).date()

                if purchase_date > today:
                    return "FAIL", f"Future purchase date: {purchase_date}"

            except ValueError:
                return "REVIEW", "Unrecognized purchase date format"

    if name == "Total purchases":
        expected = collection.count_documents({})

        if not results:
            return "REVIEW", f"Expected database count: {expected}"

        numbers = [
            value
            for record in results
            for value in record.values()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        ]

        if expected not in numbers:
            return "FAIL", f"Expected count: {expected}"

    if name == "Top suppliers":
        if not results:
            return "REVIEW", "No supplier records returned"

        expected = list(collection.aggregate([
            {"$group": {
                "_id": "$Supplier Name",
                "totalSpent": {"$sum": "$Total Price"}
            }},
            {"$sort": {"totalSpent": -1}},
            {"$limit": 5}
        ]))

        actual_names = [
            str(record.get("_id"))
            for record in results
        ]

        expected_names = [
            str(record["_id"])
            for record in expected
        ]

        if actual_names != expected_names:
            return "REVIEW", "Supplier ranking differs from database"

    return "PASS", "Basic checks passed"


# ============================================================
# RUN TESTS
# ============================================================

def main():
    print("\n" + "=" * 65)
    print("PRO CURE AI - QUICK AUTOMATED TESTS")
    print("=" * 65)

    summary = {"PASS": 0, "FAIL": 0, "REVIEW": 0}
    started = time.time()

    try:
        for index, (name, question) in enumerate(TESTS, start=1):
            print(f"\n[{index}/{len(TESTS)}] {name}")
            print(f"Question: {question}")

            try:
                response = requests.post(
                    API_URL,
                    json={"question": question},
                    timeout=75,
                )

                if response.status_code != 200:
                    status = "FAIL"
                    detail = f"HTTP {response.status_code}"
                else:
                    payload = response.json()
                    status, detail = check_results(
                        name, question, payload
                    )

            except requests.RequestException as error:
                status = "FAIL"
                detail = f"Connection/request error: {type(error).__name__}"

            except Exception as error:
                status = "FAIL"
                detail = f"Test error: {type(error).__name__}: {error}"

            summary[status] += 1

            print(f"Result: {status}")
            print(f"Details: {detail}")

        print("\n" + "=" * 65)
        print("FINAL SUMMARY")
        print("=" * 65)

        for status, count in summary.items():
            print(f"{status}: {count}")

        print(f"Total time: {time.time() - started:.1f} seconds")

        print("\nIMPORTANT:")
        print("PASS means basic checks passed, not full answer accuracy.")
        print("REVIEW means manual verification is needed.")

    finally:
        client.close()


if __name__ == "__main__":
    main()
    
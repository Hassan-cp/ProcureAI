import os
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient

# 1. Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "purchases_cleaned.csv"

# 2. Load MongoDB password
load_dotenv(BASE_DIR / ".env")

password = os.getenv("MONGO_ROOT_PASSWORD")

if not password:
    raise ValueError("MongoDB password is missing!")

# 3. Connect to MongoDB
mongo_uri = (
    f"mongodb://admin:{quote_plus(password)}"
    "@127.0.0.1:27017/?authSource=admin"
)

client = MongoClient(
    mongo_uri,
    serverSelectionTimeoutMS=5000
)

client.admin.command("ping")

db = client["procurement_db"]
collection = db["purchases"]

print("Connected to MongoDB!")

# 4. Load cleaned CSV
print("Loading cleaned dataset...")

df = pd.read_csv(
    CSV_PATH,
    low_memory=False,
    dtype={
        "Purchase Order Number": "string",
        "Requisition Number": "string",
        "Supplier Code": "string",
        "Supplier Zip Code": "string",
        "Classification Codes": "string",
        "Normalized UNSPSC": "string",
    },
)

print(f"Total rows: {len(df)}")

# 5. Convert dates to datetime
for column in ["Creation Date", "Purchase Date"]:
    df[column] = pd.to_datetime(
        df[column],
        errors="coerce",
        format="%Y-%m-%d",
    )

# 6. Convert prices to numeric
for column in ["Unit Price", "Total Price"]:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce",
    )

# 7. Convert missing values to None
df = df.astype(object).where(pd.notnull(df), None)

# 8. Prepare records
records = df.to_dict(orient="records")

for record in records:
    for column in ["Creation Date", "Purchase Date"]:
        value = record[column]

        if value is not None:
            record[column] = value.to_pydatetime()
from bson import BSON

print("Testing BSON compatibility...")

for record in records:
    BSON.encode(record)

print("All records are BSON-compatible!")



# 9. Prevent accidental duplicate imports
existing_count = collection.count_documents({})

if existing_count > 0:
    print(
        f"Collection already contains {existing_count} records."
    )
    print("Import cancelled to prevent duplicates.")

else:
    # 10. Insert records in batches
    batch_size = 1000

    print("Importing data into MongoDB...")

    for start in range(0, len(records), batch_size):
        batch = records[start:start + batch_size]

        collection.insert_many(batch)

        imported = min(start + batch_size, len(records))

        print(f"Imported {imported}/{len(records)} records")

    print("Import completed successfully!")

# 11. Verify total records
final_count = collection.count_documents({})

print(f"MongoDB records: {final_count}")

client.close()


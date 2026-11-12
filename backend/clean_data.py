from pathlib import Path
import pandas as pd

# =====================================
# STEP 1: Locate the dataset
# =====================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_PATH = BASE_DIR / "data" / "purchases.csv"
OUTPUT_PATH = BASE_DIR / "data" / "purchases_cleaned.csv"

# =====================================
# STEP 2: Read CSV
# =====================================

print("Loading dataset...")

df = pd.read_csv(
    INPUT_PATH,
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

print(f"Original rows: {len(df)}")

# =====================================
# STEP 3: Clean prices
# =====================================

print("Cleaning prices...")

price_columns = ["Unit Price", "Total Price"]

for column in price_columns:

    df[column] = (
        df[column]
        .astype("string")
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )

# =====================================
# STEP 4: Convert dates
# =====================================

print("Converting dates...")

date_columns = ["Creation Date", "Purchase Date"]

for column in date_columns:

    df[column] = pd.to_datetime(
        df[column],
        format="%m/%d/%Y",
        errors="coerce"
    )

# =====================================
# STEP 5: Check missing values
# =====================================

print("\nMissing values after cleaning:")

print(
    df[
        ["Creation Date", "Purchase Date",
         "Unit Price", "Total Price"]
    ].isnull().sum()
)

# =====================================
# STEP 6: Save cleaned dataset
# =====================================

print("\nSaving cleaned dataset...")

df.to_csv(
    OUTPUT_PATH,
    index=False,
    date_format="%Y-%m-%d"
)

print("\nData cleaning completed!")

print(f"Cleaned rows: {len(df)}")

print(f"Saved to: {OUTPUT_PATH}")
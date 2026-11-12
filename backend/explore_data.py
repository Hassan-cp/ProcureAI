from pathlib import Path
import pandas as pd

# Find the project folder
BASE_DIR = Path(__file__).resolve().parent.parent

# Locate the dataset
DATA_PATH = BASE_DIR / "data" / "purchases.csv"

# Read the CSV file
df = pd.read_csv(DATA_PATH, low_memory=False)

# Display dataset information
print("\n===== DATASET INFORMATION =====")

print("\nNumber of rows:", len(df))
print("Number of columns:", len(df.columns))

print("\nColumn names:")
for column in df.columns:
    print("-", column)

print("\nFirst 5 rows:")
print(df.head().to_string())

print("\nData types:")
print(df.dtypes.to_string())

print("\nMissing values:")
print(df.isnull().sum().to_string())

import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import OperationFailure


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

root_password = os.getenv("MONGO_ROOT_PASSWORD")
reader_username = os.getenv("MONGO_READER_USERNAME")
reader_password = os.getenv("MONGO_READER_PASSWORD")

if not all([root_password, reader_username, reader_password]):
    raise SystemExit("ERROR: Missing MongoDB credentials in .env")

root_uri = (
    f"mongodb://admin:{quote_plus(root_password)}"
    "@127.0.0.1:27017/admin?authSource=admin"
)

client = MongoClient(root_uri, serverSelectionTimeoutMS=5000)

try:
    database = client["procurement_db"]

    existing = database.command({
        "usersInfo": reader_username,
        "showPrivileges": False
    }).get("users", [])

    if existing:
        roles = existing[0].get("roles", [])
        expected = [{"role": "read", "db": "procurement_db"}]

        if roles == expected:
            print("SUCCESS: Reader user already exists with read-only role")
        else:
            raise SystemExit(
                "ERROR: Existing user has unexpected roles. "
                "Review permissions manually."
            )
    else:
        database.command(
            "createUser",
            reader_username,
            pwd=reader_password,
            roles=[{"role": "read", "db": "procurement_db"}]
        )
        print("SUCCESS: Read-only MongoDB user created")

except OperationFailure:
    print("ERROR: MongoDB authentication or permission failure")
    raise SystemExit(1)

finally:
    client.close()
    
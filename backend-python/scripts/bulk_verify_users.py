"""One-off: mark all users as email-verified so legacy accounts can log in."""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import init_database, get_collection


def main() -> None:
    init_database()
    users = get_collection("users")
    now = datetime.now(timezone.utc)
    query = {"isEmailVerified": {"$ne": True}}
    count_before = users.count_documents(query)
    result = users.update_many(
        query,
        {
            "$set": {
                "isEmailVerified": True,
                "emailVerifiedAt": now,
                "updatedAt": now,
            }
        },
    )
    total = users.count_documents({})
    verified = users.count_documents({"isEmailVerified": True})
    print(f"Unverified before: {count_before}")
    print(f"Updated: {result.modified_count}")
    print(f"Total users: {total}, verified now: {verified}")


if __name__ == "__main__":
    main()

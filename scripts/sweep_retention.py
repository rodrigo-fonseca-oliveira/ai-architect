import os
from dotenv import load_dotenv

from db.session import get_session, init_db
from app.utils.retention import sweep_audit

load_dotenv()


def main():
    init_db()
    db = get_session()
    try:
        deleted = sweep_audit(db)
        print(f"Deleted {deleted} old audit rows")
    finally:
        db.close()


if __name__ == "__main__":
    main()

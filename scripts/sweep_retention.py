from dotenv import load_dotenv

from app.utils.retention import sweep_audit
from db.session import get_session, init_db

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

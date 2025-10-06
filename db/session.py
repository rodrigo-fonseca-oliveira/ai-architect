import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

Base = declarative_base()
_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    db_url = os.getenv("DB_URL", "sqlite:///./audit.db")
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    # Recreate engine if DB_URL changed
    if _engine is None or str(getattr(_engine, "url", "")) != db_url:
        _engine = create_engine(db_url, connect_args=connect_args)
    return _engine


def get_session() -> Session:
    global _SessionLocal
    engine = get_engine()
    if _SessionLocal is None or getattr(_SessionLocal, "kw", {}).get("bind") is not engine:
        _SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return _SessionLocal()


def init_db():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

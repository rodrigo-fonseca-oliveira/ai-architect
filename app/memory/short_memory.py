import os
import sqlite3
from typing import List, Tuple
from datetime import datetime

from app.utils.logger import get_logger

logger = get_logger(__name__)

DB_PATH = os.getenv("MEMORY_DB_PATH", "./data/memory_short.db")
MAX_TURNS = int(os.getenv("MEMORY_SHORT_MAX_TURNS", "10"))


def init_short_memory(db_path: str | None = None):
    path = db_path or DB_PATH
    dir_ = os.path.dirname(path) or "."
    os.makedirs(dir_, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    c = conn.cursor()
    c.execute(
        """
      CREATE TABLE IF NOT EXISTS turns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        session_id TEXT,
        role TEXT,
        content TEXT,
        timestamp TEXT
      )
    """
    )
    c.execute(
        """
      CREATE TABLE IF NOT EXISTS summaries (
        user_id TEXT,
        session_id TEXT,
        summary TEXT,
        updated_at TEXT,
        PRIMARY KEY(user_id, session_id)
      )
    """
    )
    conn.commit()
    conn.close()


def load_turns(user_id: str, session_id: str) -> List[Tuple[str, str]]:
    init_short_memory()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute(
        """
      SELECT role, content FROM turns
      WHERE user_id=? AND session_id=?
      ORDER BY id ASC
    """,
        (user_id, session_id),
    )
    rows = c.fetchall()
    conn.close()
    return rows


def load_summary(user_id: str, session_id: str) -> str:
    init_short_memory()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute(
        """
      SELECT summary FROM summaries
      WHERE user_id=? AND session_id=?
    """,
        (user_id, session_id),
    )
    row = c.fetchone()
    conn.close()
    return row[0] if row else ""


def save_turn(user_id: str, session_id: str, role: str, content: str):
    init_short_memory()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute(
        """
      INSERT INTO turns (user_id, session_id, role, content, timestamp)
      VALUES (?, ?, ?, ?, ?)
    """,
        (user_id, session_id, role, content, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def summarize_context(turns: List[Tuple[str, str]]) -> str:
    snippet = "\n".join(f"{r}: {c}" for r, c in turns)
    return snippet if len(snippet) <= 500 else snippet[-500:]


def update_summary_if_needed(user_id: str, session_id: str) -> bool:
    turns = load_turns(user_id, session_id)
    if len(turns) > MAX_TURNS:
        summary = summarize_context(turns[-MAX_TURNS:])
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute(
            """
          REPLACE INTO summaries(user_id, session_id, summary, updated_at)
          VALUES(?,?,?,?)
        """,
            (user_id, session_id, summary, datetime.utcnow().isoformat()),
        )
        conn.commit()
        conn.close()
        return True
    return False


def clear_short_memory(user_id: str, session_id: str) -> None:
    init_short_memory()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM turns WHERE user_id=? AND session_id=?", (user_id, session_id))
    c.execute("DELETE FROM summaries WHERE user_id=? AND session_id=?", (user_id, session_id))
    conn.commit()
    conn.close()

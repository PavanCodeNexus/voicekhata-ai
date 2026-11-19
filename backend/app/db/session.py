import sqlite3
import os
from contextlib import contextmanager
from app.config import settings
from app.db.models import init_db, seed_demo_data

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable Write-Ahead Logging (WAL) for concurrent read/write speed
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_db():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()

def setup_database():
    with get_db() as conn:
        init_db(conn)
        seed_demo_data(conn)

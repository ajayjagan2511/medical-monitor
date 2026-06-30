"""
Medical Image Dataset Monitoring Agent — SQLite State Manager

Tracks previously seen datasets and run history so the agent
never sends duplicate alerts.
"""
import sqlite3
import logging
from datetime import datetime

from config import DB_PATH

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages the local SQLite database that gives the agent its memory."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None

    # ── lifecycle ─────────────────────────────

    def connect(self):
        """Open a connection and ensure tables exist."""
        self.conn = sqlite3.connect(self.db_path)
        self._create_tables()
        logger.info(f"Database connected: {self.db_path}")

    def close(self):
        """Release the file lock — must be called before GH Actions commits the db."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed.")

    # ── table setup ───────────────────────────

    def _create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seen_datasets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                platform    TEXT    NOT NULL,
                dataset_id  TEXT    NOT NULL UNIQUE,
                title       TEXT,
                url         TEXT,
                date_discovered TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS run_log (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                run_timestamp  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                datasets_found INTEGER DEFAULT 0,
                status         TEXT    DEFAULT 'success'
            )
        """)

        self.conn.commit()

    # ── dataset tracking ──────────────────────

    def is_seen(self, dataset_id: str) -> bool:
        """Return True if this dataset_id has already been recorded."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM seen_datasets WHERE dataset_id = ?", (dataset_id,)
        )
        return cursor.fetchone() is not None

    def mark_seen(self, platform: str, dataset_id: str, title: str, url: str):
        """Insert a new dataset record (silently ignores duplicates)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO seen_datasets (platform, dataset_id, title, url) "
            "VALUES (?, ?, ?, ?)",
            (platform, dataset_id, title, url),
        )
        self.conn.commit()

    # ── run history ───────────────────────────

    def get_last_run_time(self) -> str | None:
        """Return ISO-formatted timestamp of the most recent run, or None."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(run_timestamp) FROM run_log")
        row = cursor.fetchone()
        return row[0] if row and row[0] else None

    def log_run(self, datasets_found: int, status: str = "success"):
        """Record a completed run."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO run_log (datasets_found, status) VALUES (?, ?)",
            (datasets_found, status),
        )
        self.conn.commit()

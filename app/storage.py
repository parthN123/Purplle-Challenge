import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from app.models import StoreEvent


DB_PATH = Path(os.getenv("STORE_DB_PATH", "runtime/store_intelligence.db"))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect(db_path: Path | str = DB_PATH) -> Iterator[sqlite3.Connection]:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path | str = DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                store_id TEXT NOT NULL,
                camera_id TEXT NOT NULL,
                visitor_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                zone_id TEXT,
                dwell_ms INTEGER NOT NULL,
                is_staff INTEGER NOT NULL,
                confidence REAL NOT NULL,
                metadata TEXT NOT NULL,
                received_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_store_ts ON events(store_id, timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_store_visitor ON events(store_id, visitor_id)")


def insert_event(conn: sqlite3.Connection, event: StoreEvent) -> bool:
    row = (
        event.event_id,
        event.store_id,
        event.camera_id,
        event.visitor_id,
        event.event_type.value,
        event.timestamp.isoformat(),
        event.zone_id,
        event.dwell_ms,
        int(event.is_staff),
        event.confidence,
        event.metadata.model_dump_json(),
        utc_now_iso(),
    )
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO events (
            event_id, store_id, camera_id, visitor_id, event_type, timestamp,
            zone_id, dwell_ms, is_staff, confidence, metadata, received_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        row,
    )
    return cur.rowcount == 1


def fetch_events(conn: sqlite3.Connection, store_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM events WHERE store_id = ? ORDER BY timestamp ASC",
        (store_id,),
    ).fetchall()
    events: list[dict] = []
    for row in rows:
        item = dict(row)
        item["is_staff"] = bool(item["is_staff"])
        item["metadata"] = json.loads(item["metadata"])
        events.append(item)
    return events


def fetch_recent_events(conn: sqlite3.Connection, store_id: str, limit: int = 20) -> list[dict]:
    rows = conn.execute(
        """
        SELECT * FROM events
        WHERE store_id = ?
        ORDER BY received_at DESC
        LIMIT ?
        """,
        (store_id, limit),
    ).fetchall()
    events: list[dict] = []
    for row in rows:
        item = dict(row)
        item["is_staff"] = bool(item["is_staff"])
        item["metadata"] = json.loads(item["metadata"])
        events.append(item)
    return events

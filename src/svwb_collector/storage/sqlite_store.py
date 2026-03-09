from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from svwb_collector.models import Item


class SQLiteStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL,
                warning_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS sources (
                source_key TEXT PRIMARY KEY,
                source_name TEXT NOT NULL,
                is_official INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_key TEXT NOT NULL,
                item_type TEXT NOT NULL,
                external_id TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                published_at TEXT,
                payload_json TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                first_seen_run_id INTEGER NOT NULL,
                last_seen_run_id INTEGER NOT NULL,
                UNIQUE(source_key, item_type, external_id)
            );

            CREATE TABLE IF NOT EXISTS run_diffs (
                run_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                change_type TEXT NOT NULL,
                PRIMARY KEY (run_id, item_id)
            );
            """
        )
        self.conn.commit()

    def create_run(self) -> int:
        now = datetime.now(timezone.utc).isoformat()
        cur = self.conn.execute(
            "INSERT INTO runs(started_at, status, warning_count) VALUES (?, 'running', 0)",
            (now,),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def upsert_source(self, source_key: str, source_name: str, is_official: bool) -> None:
        self.conn.execute(
            """
            INSERT INTO sources(source_key, source_name, is_official) VALUES (?, ?, ?)
            ON CONFLICT(source_key) DO UPDATE SET source_name=excluded.source_name, is_official=excluded.is_official
            """,
            (source_key, source_name, 1 if is_official else 0),
        )

    def save_items(self, run_id: int, items: list[Item]) -> dict[str, int]:
        counts = {"new": 0, "updated": 0, "unchanged": 0}
        for item in items:
            self.upsert_source(item.source_key, item.source_name, item.is_official)
            payload_json = json.dumps(item.payload, ensure_ascii=False, sort_keys=True)
            content_hash = hashlib.sha256(
                json.dumps(
                    {
                        "title": item.title,
                        "url": item.url,
                        "published_at": item.published_at,
                        "payload": item.payload,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()
            row = self.conn.execute(
                "SELECT id, content_hash FROM items WHERE source_key=? AND item_type=? AND external_id=?",
                (item.source_key, item.item_type, item.external_id),
            ).fetchone()

            if row is None:
                cur = self.conn.execute(
                    """
                    INSERT INTO items(
                        source_key, item_type, external_id, title, url, published_at,
                        payload_json, content_hash, first_seen_run_id, last_seen_run_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.source_key,
                        item.item_type,
                        item.external_id,
                        item.title,
                        item.url,
                        item.published_at,
                        payload_json,
                        content_hash,
                        run_id,
                        run_id,
                    ),
                )
                item_id = int(cur.lastrowid)
                self.conn.execute(
                    "INSERT OR REPLACE INTO run_diffs(run_id, item_id, change_type) VALUES (?, ?, 'new')",
                    (run_id, item_id),
                )
                counts["new"] += 1
            else:
                change = "unchanged"
                if row["content_hash"] != content_hash:
                    change = "updated"
                    self.conn.execute(
                        """
                        UPDATE items
                        SET title=?, url=?, published_at=?, payload_json=?, content_hash=?, last_seen_run_id=?
                        WHERE id=?
                        """,
                        (item.title, item.url, item.published_at, payload_json, content_hash, run_id, row["id"]),
                    )
                    self.conn.execute(
                        "INSERT OR REPLACE INTO run_diffs(run_id, item_id, change_type) VALUES (?, ?, 'updated')",
                        (run_id, row["id"]),
                    )
                else:
                    self.conn.execute("UPDATE items SET last_seen_run_id=? WHERE id=?", (run_id, row["id"]))
                counts[change] += 1
        self.conn.commit()
        return counts

    def finish_run(self, run_id: int, warning_count: int, status: str = "success") -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE runs SET completed_at=?, status=?, warning_count=? WHERE id=?",
            (now, status, warning_count, run_id),
        )
        self.conn.commit()

    def fetch_latest_export(self) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT i.*, s.source_name, s.is_official
            FROM items i
            JOIN sources s ON s.source_key = i.source_key
            ORDER BY i.source_key, i.item_type, i.external_id
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def fetch_run_diff(self, run_id: int) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT d.change_type, i.source_key, i.item_type, i.external_id, i.title, i.url
            FROM run_diffs d
            JOIN items i ON i.id = d.item_id
            WHERE d.run_id = ?
            ORDER BY d.change_type, i.source_key
            """,
            (run_id,),
        ).fetchall()
        return [dict(row) for row in rows]

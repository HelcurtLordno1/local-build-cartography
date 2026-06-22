from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.core.config import get_settings


JSON_FIELDS = {
    "sources",
    "metadata",
    "agreed_facts",
    "disputed_points",
    "agent_outputs",
    "immediate_actions",
    "verification_steps",
    "legal_tools",
    "community_sharing",
    "historical_context",
    "layers",
    "llm_insights",
}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(path: Path | None = None) -> sqlite3.Connection:
    db_path = path or get_settings().database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_connection(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    conn = _connect(path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def decode_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    for field in JSON_FIELDS.intersection(item):
        if item[field] is not None:
            item[field] = json.loads(item[field])
    return item


def encode_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def init_db(path: Path | None = None) -> None:
    with db_connection(path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                base_url TEXT,
                credibility_base_score REAL NOT NULL DEFAULT 0.5,
                metadata TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                source_id TEXT REFERENCES sources(id),
                title TEXT NOT NULL,
                url TEXT,
                modality_type TEXT NOT NULL,
                published_at TEXT,
                ingested_at TEXT NOT NULL,
                clean_text TEXT NOT NULL,
                category TEXT NOT NULL,
                extraction_confidence REAL NOT NULL DEFAULT 0.7,
                metadata TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                canonical_title TEXT NOT NULL,
                generated_summary TEXT NOT NULL,
                category TEXT NOT NULL,
                severity_level TEXT NOT NULL,
                confidence_state TEXT NOT NULL,
                consensus_score INTEGER NOT NULL,
                geographic_scope TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                cluster_size INTEGER NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_updated_at TEXT NOT NULL,
                status TEXT NOT NULL,
                sources TEXT NOT NULL DEFAULT '[]',
                is_read INTEGER NOT NULL DEFAULT 0,
                deleted_at TEXT,
                llm_enriched INTEGER NOT NULL DEFAULT 0,
                llm_insights TEXT
            );

            CREATE TABLE IF NOT EXISTS event_articles (
                event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
                similarity_score REAL NOT NULL,
                relationship_type TEXT NOT NULL,
                is_primary_source INTEGER NOT NULL DEFAULT 0,
                added_at TEXT NOT NULL,
                PRIMARY KEY (event_id, article_id)
            );

            CREATE TABLE IF NOT EXISTS debates (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL UNIQUE REFERENCES events(id) ON DELETE CASCADE,
                agreed_facts TEXT NOT NULL DEFAULT '[]',
                disputed_points TEXT NOT NULL DEFAULT '[]',
                agent_outputs TEXT NOT NULL DEFAULT '{}',
                synthesis_output TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS action_protocols (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL UNIQUE REFERENCES events(id) ON DELETE CASCADE,
                protocol_type TEXT NOT NULL,
                immediate_actions TEXT NOT NULL DEFAULT '[]',
                verification_steps TEXT NOT NULL DEFAULT '[]',
                legal_tools TEXT NOT NULL DEFAULT '[]',
                community_sharing TEXT NOT NULL DEFAULT '[]',
                historical_context TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT
            );

            CREATE TABLE IF NOT EXISTS archaeology (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL UNIQUE REFERENCES events(id) ON DELETE CASCADE,
                layers TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            """
        )
        existing_event_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(events)").fetchall()
        }
        if "is_read" not in existing_event_columns:
            conn.execute("ALTER TABLE events ADD COLUMN is_read INTEGER NOT NULL DEFAULT 0")
        if "deleted_at" not in existing_event_columns:
            conn.execute("ALTER TABLE events ADD COLUMN deleted_at TEXT")
        if "llm_enriched" not in existing_event_columns:
            conn.execute("ALTER TABLE events ADD COLUMN llm_enriched INTEGER NOT NULL DEFAULT 0")
        if "llm_insights" not in existing_event_columns:
            conn.execute("ALTER TABLE events ADD COLUMN llm_insights TEXT")

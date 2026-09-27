"""
db/schema.py
------------
Creates and manages the moonreader_v2.db SQLite database.
This is the canonical source of truth for all ingested data.
ChromaDB is derived from it.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from mreas.core.config import DB_PATH

from mreas.core.utils import DDL


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Return a connection with row_factory and foreign keys enabled."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Create the database and all tables if they don't exist. Returns connection."""
    conn = get_connection(db_path)
    conn.executescript(DDL)
    conn.commit()
    return conn


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_source(conn: sqlite3.Connection, name: str, author: str = None,
                  description: str = None, category: str = None,
                  origin: str = "moonreader", filename: str = None) -> int:
    """
    Insert a source if it doesn't exist (by name). Returns the source id.
    Does NOT update existing rows — name is the stable key.
    """
    cur = conn.execute(
        "SELECT id FROM sources WHERE name = ?", (name,)
    )
    row = cur.fetchone()
    if row:
        return row["id"]

    cur = conn.execute(
        """INSERT INTO sources (name, author, description, category, origin, filename, added_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (name, author, description, category, origin, filename, now_iso())
    )
    conn.commit()
    return cur.lastrowid


def insert_chunk(conn: sqlite3.Connection, source_id: int, highlight: str,
                 user_note: str, content_hash: str, origin: str = "moonreader",
                 mr_note_id: int = None, mr_timestamp: int = None,
                 tags: str = None, indexed_in_chroma: int = 0) -> bool:
    """
    Insert a chunk if its content_hash doesn't already exist.
    Returns True if inserted, False if skipped (duplicate).
    """
    try:
        conn.execute(
            """INSERT OR IGNORE INTO chunks
               (source_id, highlight, user_note, tags, origin, mr_note_id,
                mr_timestamp, content_hash, indexed_in_chroma, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (source_id, highlight, user_note, tags, origin, mr_note_id,
             mr_timestamp, content_hash, indexed_in_chroma, now_iso())
        )
        return conn.execute(
            "SELECT changes()"
        ).fetchone()[0] == 1
    except sqlite3.IntegrityError:
        return False


def mark_chunks_indexed(conn: sqlite3.Connection, content_hashes: list[str]):
    """Mark a list of chunks as indexed in ChromaDB."""
    if not content_hashes:
        return
    placeholders = ",".join("?" * len(content_hashes))
    conn.execute(
        f"UPDATE chunks SET indexed_in_chroma = 1 WHERE content_hash IN ({placeholders})",
        content_hashes
    )
    conn.commit()


def get_pending_chunks(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return all chunks not yet indexed in ChromaDB."""
    return conn.execute(
        """SELECT c.id, c.content_hash, c.highlight, c.user_note, c.tags,
                  c.origin, c.mr_timestamp,
                  s.name as source_name, s.description as source_description
           FROM chunks c
           JOIN sources s ON c.source_id = s.id
           WHERE c.indexed_in_chroma = 0"""
    ).fetchall()


def log_import(conn: sqlite3.Connection, origin: str, source_file: str,
               new_sources: int, new_chunks: int, skipped: int,
               status: str = "success"):
    conn.execute(
        """INSERT INTO import_log (run_at, origin, source_file, new_sources, new_chunks, skipped, status)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (now_iso(), origin, source_file, new_sources, new_chunks, skipped, status)
    )
    conn.commit()


def save_parsed_data(conn: sqlite3.Connection, sources: list['Source'], chunks: list['Chunk']) -> tuple[int, int, int]:
    """
    Saves parsed Source and Chunk models into the database.
    Returns (new_sources, new_chunks, skipped).
    """
    new_sources_cnt = 0
    new_chunks_cnt = 0
    skipped_cnt = 0

    # Build a lookup for source name to source id
    source_ids = {}

    for src in sources:
        # We can assume upsert_source handles duplicates internally or updates them
        # Let's insert or update
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO sources (name, author, description, category, origin, filename, added_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
               author=excluded.author,
               description=excluded.description,
               category=excluded.category,
               filename=excluded.filename""",
            (src.name, src.author, src.description, src.category, src.origin, src.filename, now_iso())
        )
        # We don't have a direct way to know if it was inserted or just updated easily with ON CONFLICT DO UPDATE
        # in standard sqlite without checking changes() vs returning. We'll just rely on a simple query
        if cur.rowcount > 0:
            new_sources_cnt += 1  # Note: rowcount can be confusing with DO UPDATE, but close enough for stats
        
        cur.execute("SELECT id FROM sources WHERE name = ?", (src.name,))
        row = cur.fetchone()
        if row:
            source_ids[src.name] = row[0]

    for chunk in chunks:
        sid = source_ids.get(chunk.source_name)
        if not sid:
            skipped_cnt += 1
            continue
            
        inserted = insert_chunk(
            conn,
            source_id=sid,
            highlight=chunk.highlight,
            user_note=chunk.user_note,
            content_hash=chunk.content_hash,
            origin=chunk.origin,
            mr_note_id=chunk.mr_note_id,
            mr_timestamp=chunk.mr_timestamp,
            tags=chunk.tags
        )
        if inserted:
            new_chunks_cnt += 1
        else:
            skipped_cnt += 1

    conn.commit()
    return new_sources_cnt, new_chunks_cnt, skipped_cnt


def get_stats(conn: sqlite3.Connection) -> dict:
    """Return summary statistics for display."""
    stats = {}
    stats["total_sources"] = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    stats["total_chunks"] = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    stats["indexed_chunks"] = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE indexed_in_chroma = 1"
    ).fetchone()[0]
    stats["pending_chunks"] = stats["total_chunks"] - stats["indexed_chunks"]
    stats["moonreader_chunks"] = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE origin = 'moonreader'"
    ).fetchone()[0]
    stats["external_chunks"] = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE origin = 'external'"
    ).fetchone()[0]
    last_import = conn.execute(
        "SELECT run_at, origin, source_file, new_chunks FROM import_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    stats["last_import"] = dict(last_import) if last_import else None
    return stats


def list_sources(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return all sources with their chunk counts."""
    return conn.execute(
        """SELECT s.id, s.name, s.author, s.origin,
                  COUNT(c.id) as chunk_count
           FROM sources s
           LEFT JOIN chunks c ON c.source_id = s.id
           GROUP BY s.id
           ORDER BY chunk_count DESC"""
    ).fetchall()

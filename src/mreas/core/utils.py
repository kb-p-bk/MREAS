SAMPLE_FILE_CONTENT = """\
# External import file for moon_reader_extract
# Any extension works (.txt, .md, etc.)
# Lines starting with # are comments and are ignored.
#
# STRUCTURE:
#   - Start each source with a header block between --- lines
#   - 'source' is required; 'author' and 'tags' are optional
#   - Each highlight is a CHUNK block with 'highlight' (required) and 'note' (optional)
#   - Multiple sources can be in one file
#   - Multi-line values: indent continuation lines with 2 spaces

---
source: "Thinking, Fast and Slow"
author: "Daniel Kahneman"
tags: "psychology, cognition, decision-making"
---
CHUNK
highlight: System 1 operates automatically and quickly, with little or no effort
  and no sense of voluntary control.
note: This is the fast, intuitive mode — contrasted with the slow, deliberate System 2.
---
CHUNK
highlight: Anchoring effect: the first number you hear influences all subsequent
  numerical estimates, even when the anchor is arbitrary.
---
CHUNK
highlight: We are prone to overestimate how much we understand about the world
  and to underestimate the role of chance in events.
note: Hindsight bias and narrative fallacy both stem from this.
---
---
source: "My Reading Notes"
author:
tags: "personal, to-revisit"
---
CHUNK
highlight: Dual-process theory has interesting parallels with ML model behavior —
  fast pattern matching vs. slow chain-of-thought reasoning.
note: Possible blog post angle. Revisit after reading Kahneman chapter 3.
---
CHUNK
highlight: The planning fallacy: people underestimate time, costs, and risks
  of future actions while overestimating benefits.
---
"""

DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS sources (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    author      TEXT,
    description TEXT,
    category    TEXT,
    origin      TEXT NOT NULL DEFAULT 'moonreader',
    filename    TEXT,
    added_at    TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_name ON sources(name);

CREATE TABLE IF NOT EXISTS chunks (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id           INTEGER NOT NULL REFERENCES sources(id),
    highlight           TEXT,
    user_note           TEXT,
    tags                TEXT,
    origin              TEXT NOT NULL DEFAULT 'moonreader',
    mr_note_id          INTEGER,
    mr_timestamp        INTEGER,
    content_hash        TEXT NOT NULL,
    indexed_in_chroma   INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_chunks_hash ON chunks(content_hash);
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_chunks_indexed ON chunks(indexed_in_chroma);

CREATE TABLE IF NOT EXISTS import_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at      TEXT NOT NULL,
    origin      TEXT NOT NULL,
    source_file TEXT NOT NULL,
    new_sources INTEGER NOT NULL DEFAULT 0,
    new_chunks  INTEGER NOT NULL DEFAULT 0,
    skipped     INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'success'
);
"""

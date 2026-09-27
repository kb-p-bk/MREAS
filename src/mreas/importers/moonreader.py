"""
importer/moonreader.py
----------------------
Handles importing Moon Reader .mrpro backup files.

Key behaviors:
- Extracts only mrbooks.db from the ZIP (in-memory, no folder created)
- Deduplicates by content_hash = MD5(source_name || highlight || user_note)
- Yields Source and Chunk models.
"""

import hashlib
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from typing import Tuple

from mreas.importers.base import BaseImporter
from mreas.core.models import Source, Chunk


def _compute_hash(source_name: str, highlight: str, user_note: str) -> str:
    """
    Hash = MD5(source_name || "||" || highlight || "||" || user_note).
    """
    seed = f"{source_name.strip()}||{(highlight or '').strip()}||{(user_note or '').strip()}"
    return hashlib.md5(seed.encode("utf-8", errors="ignore")).hexdigest()


def _extract_db_bytes(mrpro_path: Path) -> bytes:
    """
    Open the .mrpro ZIP and return the raw bytes of mrbooks.db.
    """
    with zipfile.ZipFile(mrpro_path, "r") as zf:
        names_in_zip = zf.namelist()

        names_list_entry = next(
            (n for n in names_in_zip if n.endswith("_names.list")), None
        )
        if not names_list_entry:
            raise FileNotFoundError(f"_names.list not found inside {mrpro_path.name}")

        manifest_text = zf.read(names_list_entry).decode("utf-8", errors="ignore")
        manifest_lines = [l.strip() for l in manifest_text.splitlines() if l.strip()]

        base_prefix = names_list_entry.rsplit("/", 1)[0] + "/"

        db_index = None
        for idx, rel_path in enumerate(manifest_lines, start=1):
            if rel_path.endswith("databases/mrbooks.db"):
                db_index = idx
                break

        if db_index is None:
            raise FileNotFoundError(f"mrbooks.db not found in _names.list manifest inside {mrpro_path.name}")

        tag_entry = f"{base_prefix}{db_index}.tag"
        if tag_entry not in names_in_zip:
            raise FileNotFoundError(f"Expected tag file {tag_entry!r} not found in {mrpro_path.name}")

        return zf.read(tag_entry)


class MoonReaderImporter(BaseImporter):
    def parse(self, path: Path) -> Tuple[list[Source], list[Chunk]]:
        path = Path(path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        db_bytes = _extract_db_bytes(path)

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp.write(db_bytes)
            tmp_path = Path(tmp.name)

        sources = {}
        all_chunks = []

        try:
            conn = sqlite3.connect(str(tmp_path))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Build books map
            cur.execute("SELECT book, author, description, category, filename FROM books")
            for row in cur.fetchall():
                title = row["book"] or "Unknown Title"
                sources[title] = Source(
                    name=title,
                    author=row["author"],
                    description=row["description"],
                    category=row["category"],
                    filename=row["filename"],
                    origin="moonreader"
                )

            # Read all notes with book metadata
            cur.execute(
                """
                SELECT
                    n._id        AS mr_note_id,
                    n.book       AS title,
                    n.time       AS mr_timestamp,
                    n.original   AS original,
                    n.bookmark   AS bookmark,
                    n.note       AS user_note
                FROM notes n
                """
            )
            for row in cur.fetchall():
                title = row["title"] or "Unknown Title"
                highlight = row["original"] or row["bookmark"] or ""
                user_note = row["user_note"] or ""

                if not highlight.strip() and not user_note.strip():
                    continue

                h = _compute_hash(title, highlight, user_note)
                
                # Make sure source exists if there's a note but no book entry
                if title not in sources:
                     sources[title] = Source(name=title, origin="moonreader")

                all_chunks.append(Chunk(
                    source_name=title,
                    highlight=highlight,
                    user_note=user_note,
                    mr_note_id=row["mr_note_id"],
                    mr_timestamp=row["mr_timestamp"],
                    origin="moonreader",
                    content_hash=h
                ))

            conn.close()
        finally:
            tmp_path.unlink(missing_ok=True)

        return list(sources.values()), all_chunks

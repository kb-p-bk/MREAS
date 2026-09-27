"""
importer/external.py
--------------------
Handles importing external highlight files in the structured text format.

Format spec:
  - UTF-8 text file, any extension
  - Header block between --- delimiters: source (required), author, tags (optional)
  - Each chunk block starts with CHUNK on its own line
  - highlight field required per chunk; note optional
  - Multiple source sections allowed in one file
  - Lines starting with # are comments (ignored)
  - Multi-line values: indent continuation lines with 2+ spaces
"""

import hashlib
from pathlib import Path
from typing import Tuple

from mreas.importers.base import BaseImporter
from mreas.core.models import Source, Chunk

def _strip_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or \
       (s.startswith("'") and s.endswith("'")):
        return s[1:-1].strip()
    return s

def _compute_hash(source_name: str, highlight: str, user_note: str) -> str:
    seed = f"{source_name.strip()}||{(highlight or '').strip()}||{(user_note or '').strip()}"
    return hashlib.md5(seed.encode("utf-8", errors="ignore")).hexdigest()

class ExternalImporter(BaseImporter):
    def parse(self, path: Path) -> Tuple[list[Source], list[Chunk]]:
        path = Path(path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()

        # Strip comment lines
        lines = [l for l in lines if not l.lstrip().startswith("#")]
        while lines and not lines[-1].strip():
            lines.pop()

        sources = {}
        all_chunks = []
        i = 0
        n = len(lines)

        def peek_next_nonblank(start: int) -> str:
            j = start
            while j < n and not lines[j].strip():
                j += 1
            return lines[j].strip() if j < n else ""

        def read_multiline_value(start_val: str, start_idx: int) -> tuple[str, int]:
            parts = [start_val]
            j = start_idx
            while j < n:
                line = lines[j]
                if line and line[0] in (" ", "\t"):
                    parts.append(line.strip())
                    j += 1
                else:
                    break
            return " ".join(p for p in parts if p), j

        while i < n:
            while i < n and lines[i].strip() != "---":
                i += 1
            if i >= n:
                break

            next_nb = peek_next_nonblank(i + 1)
            if next_nb == "---":
                i += 1
                continue

            i += 1
            header: dict[str, str] = {}
            while i < n and lines[i].strip() != "---":
                line = lines[i]
                if not line.strip():
                    i += 1
                    continue
                if ":" in line:
                    key, _, val = line.partition(":")
                    full_val, i = read_multiline_value(val.strip(), i + 1)
                    header[key.strip().lower()] = full_val
                else:
                    i += 1

            if i < n and lines[i].strip() == "---":
                i += 1

            source_name = _strip_quotes(header.get("source", ""))
            if not source_name:
                continue

            author = _strip_quotes(header.get("author", ""))
            tags = _strip_quotes(header.get("tags", ""))
            
            if source_name not in sources:
                sources[source_name] = Source(
                    name=source_name,
                    author=author or None,
                    origin="external",
                    filename=str(path)
                )

            while i < n:
                while i < n and not lines[i].strip():
                    i += 1
                if i >= n:
                    break

                line_stripped = lines[i].strip()
                if line_stripped == "---":
                    next_nb = peek_next_nonblank(i + 1)
                    if next_nb == "---" or (next_nb and next_nb.upper() != "CHUNK"):
                        break
                    else:
                        i += 1
                        continue

                if line_stripped.upper() != "CHUNK":
                    i += 1
                    continue

                i += 1
                chunk_fields: dict[str, str] = {}
                while i < n:
                    line = lines[i]
                    stripped = line.strip()

                    if stripped == "---" or stripped.upper() == "CHUNK":
                        break
                    if not stripped:
                        i += 1
                        continue

                    if ":" in line and not (line[0] in (" ", "\t")):
                        key, _, val = line.partition(":")
                        full_val, i = read_multiline_value(val.strip(), i + 1)
                        chunk_fields[key.strip().lower()] = full_val
                    else:
                        i += 1

                highlight = chunk_fields.get("highlight", "").strip()
                note = chunk_fields.get("note", "").strip()

                if highlight:
                    h = _compute_hash(source_name, highlight, note)
                    all_chunks.append(Chunk(
                        source_name=source_name,
                        highlight=highlight,
                        user_note=note or None,
                        tags=tags or None,
                        origin="external",
                        content_hash=h
                    ))

        return list(sources.values()), all_chunks


from mreas.core.utils import SAMPLE_FILE_CONTENT

def print_sample():
    print(SAMPLE_FILE_CONTENT)

def write_sample(output_path: Path):
    output_path = Path(output_path)
    output_path.write_text(SAMPLE_FILE_CONTENT, encoding="utf-8")
    print(f"[SAMPLE] Written to {output_path}")

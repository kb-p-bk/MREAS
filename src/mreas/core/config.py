import os
from pathlib import Path

# The core module is at src/moon/core.
# The project root is src/moon/core/../../../ (i.e. moon_reader_extract)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent

DB_PATH = ROOT_DIR / "moonreader_v2.db"
CHROMA_DIR = ROOT_DIR / "chroma_db"
ARCHIVE_DIR = ROOT_DIR / "archive"

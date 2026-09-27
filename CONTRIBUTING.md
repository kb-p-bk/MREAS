# Contributing

This document outlines the architecture and provides instructions for adding new importers.

## Architecture Overview

The codebase uses a clean, decoupled architecture:
- `src/mreas/core/`: Contains the fundamental data structures (`models.py`) and configuration (`config.py`).
- `src/mreas/storage/`: Handles the persistence layer. `db.py` manages the SQLite canonical database, and `vector.py` manages the ChromaDB semantic search vector store.
- `src/mreas/importers/`: Contains modules that parse source files and yield data models.
- `src/mreas/cli/`: Contains the presentation layer (`main.py` for commands, `tui/` package for the interactive UI).

## How to Add a New Importer

If you want to add support for a new reading app's exports, you simply need to create a new importer class.

1. **Create your Importer Module**
   Create a new file in `src/mreas/importers/` (e.g., `kindle.py`).

2. **Implement the `BaseImporter` Interface**
   Your class should inherit from `BaseImporter` and implement the `parse()` method.

   ```python
   from pathlib import Path
   from typing import Tuple
   from mreas.importers.base import BaseImporter
   from mreas.core.models import Source, Chunk

   class KindleImporter(BaseImporter):
       def parse(self, path: Path) -> Tuple[list[Source], list[Chunk]]:
           sources = []
           chunks = []
           
           # ... your parsing logic here ...
           # Create Source objects (representing books/articles)
           # Create Chunk objects (representing highlights/notes)
           
           return sources, chunks
   ```

3. **Wire it to the CLI**
   In `src/mreas/cli/main.py`, create a new command for your importer (e.g., `cmd_import_kindle`), instantiate your importer, and pass the results to `save_parsed_data()`.

   ```python
   def cmd_import_kindle(args: list[str]):
       from mreas.importers.kindle import KindleImporter
       from mreas.storage.db import init_db, save_parsed_data, log_import
       from mreas.core.config import DB_PATH
       
       # Setup and parsing...
       importer = KindleImporter()
       sources, chunks = importer.parse(Path(args[0]))
       
       # Saving to DB
       conn = init_db(DB_PATH)
       new_sources, new_chunks, skipped = save_parsed_data(conn, sources, chunks)
       conn.close()
       
       # (Optionally trigger vector embedding...)
   ```

   Finally, register your command in the `COMMANDS` dict at the bottom of `main.py`.

## Development Setup

We use `uv` for dependency management and running the project.
```bash
uv sync
uv run mreas help
```

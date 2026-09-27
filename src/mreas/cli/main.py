"""
main.py
-------
Moon Reader Extract CLI entry point.

Commands:
  import <file.mrpro>          Import a Moon Reader backup file
  import-external <file>       Import an external structured text file
  embed                        Embed all pending chunks into ChromaDB
  stats                        Show database and ChromaDB statistics
  sample                       Print a sample external import file to stdout
  sample <output_file>         Write the sample file to a path
  search                       Launch the interactive search UI
Usage:
  python main.py import 2026-05-10.mrpro
  python main.py import-external my_notes.txt
  python main.py embed
  python main.py stats
  python main.py sample
  python main.py sample template.txt
  python main.py search
"""

import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass



def cmd_import(args: list[str]):
    if not args:
        print("Usage: python main.py import <file.mrpro>")
        sys.exit(1)
    from mreas.importers.moonreader import MoonReaderImporter
    from mreas.storage.vector import MoonReaderVectorStore
    from mreas.storage.db import init_db, save_parsed_data, log_import
    from mreas.core.config import DB_PATH, ARCHIVE_DIR
    import shutil

    mrpro_path = Path(args[0]).resolve()
    importer = MoonReaderImporter()
    
    print(f"[IMPORT] Parsing {mrpro_path.name}...")
    sources, chunks = importer.parse(mrpro_path)
    print(f"[IMPORT] Found {len(sources)} source(s), {len(chunks)} chunk(s). Checking for new entries...")

    conn = init_db(DB_PATH)
    new_sources, new_chunks, skipped = save_parsed_data(conn, sources, chunks)
    print(f"[IMPORT] Done. New sources: {new_sources}, New chunks: {new_chunks}, Skipped (already indexed): {skipped}")
    log_import(conn, origin="moonreader", source_file=str(mrpro_path), new_sources=new_sources, new_chunks=new_chunks, skipped=skipped)
    conn.close()
    
    if new_chunks > 0:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        dest = ARCHIVE_DIR / mrpro_path.name
        if not dest.exists():
            shutil.move(str(mrpro_path), str(dest))
            print(f"[ARCHIVE] Moved {mrpro_path.name} → archive/")
        else:
            print(f"[ARCHIVE] {mrpro_path.name} already in archive, skipping move.")

        print(f"\n[EMBED] Embedding {new_chunks} new chunk(s) into ChromaDB...")
        store = MoonReaderVectorStore()
        store.embed_pending(DB_PATH, verbose=True)
    else:
        print("\n[INFO] No new chunks to embed.")


def cmd_import_external(args: list[str]):
    if not args:
        print("Usage: python main.py import-external <file>")
        sys.exit(1)
    from mreas.importers.external import ExternalImporter
    from mreas.storage.vector import MoonReaderVectorStore
    from mreas.storage.db import init_db, save_parsed_data, log_import
    from mreas.core.config import DB_PATH

    file_path = Path(args[0])
    importer = ExternalImporter()
    
    print(f"[IMPORT] Parsing {file_path.name}...")
    sources, chunks = importer.parse(file_path)
    print(f"[IMPORT] Found {len(sources)} source(s), {len(chunks)} chunk(s). Checking for new entries...")

    conn = init_db(DB_PATH)
    new_sources, new_chunks, skipped = save_parsed_data(conn, sources, chunks)
    print(f"[IMPORT] Done. New sources: {new_sources}, New chunks: {new_chunks}, Skipped (already indexed): {skipped}")
    log_import(conn, origin="external", source_file=str(file_path), new_sources=new_sources, new_chunks=new_chunks, skipped=skipped)
    conn.close()

    if new_chunks > 0:
        print(f"\n[EMBED] Embedding {new_chunks} new chunk(s) into ChromaDB...")
        store = MoonReaderVectorStore()
        store.embed_pending(DB_PATH, verbose=True)
    else:
        print("\n[INFO] No new chunks to embed.")


def cmd_embed(_args: list[str]):
    from mreas.storage.vector import MoonReaderVectorStore
    from mreas.core.config import DB_PATH

    if not DB_PATH.exists():
        print("[ERROR] moonreader_v2.db not found. Run migration first.")
        sys.exit(1)

    store = MoonReaderVectorStore()
    count = store.embed_pending(DB_PATH, verbose=True)
    if count == 0:
        print("[INFO] Nothing to embed — all chunks are already indexed.")


def cmd_stats(_args: list[str]):
    from mreas.storage.db import get_connection, get_stats
    from mreas.core.config import DB_PATH
    from mreas.storage.vector import MoonReaderVectorStore

    print("\n── moonreader_v2.db ──────────────────────────────────")
    if not DB_PATH.exists():
        print("  Not found. Run migration or import first.")
    else:
        conn = get_connection(DB_PATH)
        s = get_stats(conn)
        conn.close()
        print(f"  Sources          : {s['total_sources']}")
        print(f"  Total chunks     : {s['total_chunks']}")
        print(f"    Moon Reader    : {s['moonreader_chunks']}")
        print(f"    External       : {s['external_chunks']}")
        print(f"  Indexed in Chroma: {s['indexed_chunks']}")
        print(f"  Pending embed    : {s['pending_chunks']}")
        if s["last_import"]:
            li = s["last_import"]
            print(f"  Last import      : {li['run_at']} ({li['origin']}) "
                  f"+{li['new_chunks']} chunks from {Path(li['source_file']).name}")

    print("\n── ChromaDB ──────────────────────────────────────────")
    try:
        store = MoonReaderVectorStore()
        print(f"  Total entries    : {store.get_total_count()}")
    except Exception as e:
        print(f"  Error reading ChromaDB: {e}")
    print()


def cmd_sample(args: list[str]):
    from mreas.importers.external import print_sample, write_sample
    if args:
        write_sample(Path(args[0]))
    else:
        print_sample()


def cmd_search(_args: list[str]):
    # Import here to avoid loading rich at startup for other commands
    import mreas.cli.tui as search
    search.search_notes()




COMMANDS = {
    "import": cmd_import,
    "import-external": cmd_import_external,
    "embed": cmd_embed,
    "stats": cmd_stats,
    "sample": cmd_sample,
    "search": cmd_search,
}

HELP = """
Moon Reader Extract

Commands:
  import <file.mrpro>          Import a Moon Reader backup
  import-external <file>       Import an external structured text file
  embed                        Embed pending chunks into ChromaDB
  stats                        Show statistics
  sample [output_file]         Print/write a sample external import file
  search                       Interactive semantic search
"""


def cli_entry_point():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(HELP)
        sys.exit(0)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd not in COMMANDS:
        print(f"[ERROR] Unknown command: {cmd}")
        print(HELP)
        sys.exit(1)

    COMMANDS[cmd](args)


if __name__ == "__main__":
    cli_entry_point()

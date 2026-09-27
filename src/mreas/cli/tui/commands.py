
from pathlib import Path
from rich.table import Table
from rich import box
from mreas.cli.tui.components import _print, RICH_AVAILABLE, console, _make_export_console, _pager_prompt, _render_page, _parse_doc
from rich.panel import Panel
from rich.text import Text

def cmd_browse(source_name: str, n: int, filename_map: dict, export_path: str | None = None, page_size: int = 5):
    from mreas.storage.db import get_connection
    from mreas.core.config import DB_PATH
    if not DB_PATH.exists():
        _print("[ERROR] moonreader_v2.db not found.", style="red")
        return
    conn = get_connection(DB_PATH)
    src = conn.execute("SELECT id, name, filename FROM sources WHERE name = ?", (source_name,)).fetchone()
    if not src:
        candidates = conn.execute("SELECT id, name, filename FROM sources WHERE LOWER(name) LIKE ?", (f"%{source_name.lower()}%",)).fetchall()
        if not candidates:
            _print(f"[yellow]Source not found: '{source_name}'[/yellow]")
            conn.close()
            return
        if len(candidates) == 1:
            src = candidates[0]
        else:
            _print(f"[yellow]Multiple matches for '{source_name}':[/yellow]")
            for c in candidates:
                _print(f"  • {c['name']}")
            conn.close()
            return
    limit_clause = f"LIMIT {n}" if n > 0 else ""
    chunks = conn.execute(
        f"SELECT highlight, user_note, mr_timestamp, tags FROM chunks WHERE source_id = ? ORDER BY mr_timestamp ASC NULLS LAST, id ASC {limit_clause}",
        (src["id"],)
    ).fetchall()
    conn.close()
    total = len(chunks)
    if total == 0:
        _print(f"[yellow]No bookmarks found for '{src['name']}'[/yellow]")
        return
    filename = filename_map.get(src["name"]) or (Path(src["filename"]).name if src["filename"] else None)
    header_parts = [f"\n── {total} bookmark(s) from '{src['name']}'"]
    if n > 0: header_parts[0] += f" (first {n})"
    if filename and filename != src["name"]: header_parts.append(f"    {filename}")
    header = "\n".join(header_parts)
    _print(header, style="bold")
    export_console = _make_export_console(export_path) if export_path else None
    if export_console: export_console.print(header)
    def render_chunk(global_idx, total_items, chunk, ec):
        highlight = (chunk["highlight"] or "").strip()
        user_note = (chunk["user_note"] or "").strip()
        tags = chunk["tags"]
        if RICH_AVAILABLE:
            body = Text(overflow="fold")
            body.append(highlight, style="white")
            if user_note:
                body.append("\n\n✎ ", style="dim yellow")
                body.append(user_note, style="italic yellow")
            if tags:
                body.append(f"\n🏷 {tags}", style="dim cyan")
            title_line = f"[bold]{global_idx}/{total_items}[/bold]  [green]HIGHLIGHT[/green]"
            panel = Panel(body, title=title_line, title_align="left", box=box.ROUNDED, expand=True)
            console.print(panel)
            if ec: ec.print(panel)
        else:
            print(f"\n[{global_idx}/{total_items}] {highlight}")
            if user_note: print(f"  NOTE: {user_note}")
            print("-" * 50)
    if export_console:
        for i, chunk in enumerate(chunks, start=1):
            render_chunk(i, total, chunk, export_console)
    total_pages = (total + page_size - 1) // page_size
    page = 0
    while True:
        _render_page(chunks, page, page_size, total, render_fn=render_chunk, export_console=None)
        if total_pages == 1: break
        action = _pager_prompt(is_first=(page == 0), is_last=(page == total_pages - 1))
        if action == "n": page += 1
        elif action == "p": page -= 1
        elif action == "stay": continue
        else: break
    if export_path:
        _print(f"\n[dim]Exported all {total} bookmark(s) to {export_path}[/dim]", style="dim")

def cmd_list_sources(store, export_path: str | None = None):
    from mreas.storage.db import get_connection, list_sources
    from mreas.core.config import DB_PATH
    if not DB_PATH.exists():
        _print("\n[INFO] moonreader_v2.db not found. Scanning ChromaDB...", style="dim")
        names = store.list_sources_in_chroma()
        if RICH_AVAILABLE:
            table = Table(title="Indexed Sources (ChromaDB)", box=box.SIMPLE)
            table.add_column("#", style="dim", width=4)
            table.add_column("Source", style="bold")
            for i, name in enumerate(names, 1):
                table.add_row(str(i), name)
            console.print(table)
        else:
            for i, name in enumerate(names, 1):
                print(f"  {i:3}. {name}")
        return
    conn = get_connection(DB_PATH)
    sources = list_sources(conn)
    conn.close()
    if RICH_AVAILABLE:
        table = Table(title="Indexed Sources", box=box.SIMPLE)
        table.add_column("#", style="dim", width=4)
        table.add_column("Source", style="bold")
        table.add_column("Author", style="dim")
        table.add_column("Origin", style="cyan")
        table.add_column("Chunks", justify="right", style="green")
        for i, row in enumerate(sources, 1):
            table.add_row(str(i), row["name"], row["author"] or "", row["origin"], str(row["chunk_count"]))
        console.print(table)
        if export_path:
            ec = _make_export_console(export_path)
            if ec:
                ec.print(table)
                _print(f"\n[dim]Exported to {export_path}[/dim]", style="dim")
    else:
        print(f"\n{'#':>4}  {'Chunks':>6}  Source")
        print("-" * 60)
        lines = []
        for i, row in enumerate(sources, 1):
            line = f"{i:>4}  {row['chunk_count']:>6}  {row['name']}"
            print(line)
            lines.append(line)
        if export_path:
            with open(export_path, "a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

def cmd_stats(store):
    from mreas.storage.db import get_connection, get_stats
    from mreas.core.config import DB_PATH
    if RICH_AVAILABLE:
        table = Table(title="Statistics", box=box.SIMPLE, show_header=False)
        table.add_column("Key", style="dim")
        table.add_column("Value", style="bold")
        if DB_PATH.exists():
            conn = get_connection(DB_PATH)
            s = get_stats(conn)
            conn.close()
            table.add_row("Sources", str(s["total_sources"]))
            table.add_row("Total chunks", str(s["total_chunks"]))
            table.add_row("  Moon Reader", str(s["moonreader_chunks"]))
            table.add_row("  External", str(s["external_chunks"]))
            table.add_row("Indexed in ChromaDB", str(s["indexed_chunks"]))
            table.add_row("Pending embed", str(s["pending_chunks"]))
            if s["last_import"]:
                li = s["last_import"]
                table.add_row("Last import", f"{li['run_at']} ({li['origin']}) +{li['new_chunks']} from {Path(li['source_file']).name}")
        else:
            table.add_row("moonreader_v2.db", "not found")
        table.add_row("ChromaDB entries", str(store.get_total_count()))
        console.print(table)
    else:
        print(f"\nChromaDB entries: {store.get_total_count()}")
        if DB_PATH.exists():
            from mreas.storage.db import get_connection, get_stats
            conn = get_connection(DB_PATH)
            s = get_stats(conn)
            conn.close()
            print(f"Sources: {s['total_sources']}")
            print(f"Chunks: {s['total_chunks']} (pending: {s['pending_chunks']})")


import re
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

try:
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None

def _print(msg: str, style: str = ""):
    if RICH_AVAILABLE and style:
        console.print(msg, style=style)
    else:
        print(msg)

def _parse_export(raw: str) -> tuple[str, str | None]:
    m = re.search(r'\s+>\s+(\S+)\s*$', raw)
    if m:
        export_path = m.group(1)
        raw = raw[:m.start()].strip()
        return raw, export_path
    return raw, None

def parse_query(raw: str) -> tuple[str, str | None, int]:
    raw = raw.strip()
    source_filter = None
    source_match = re.match(r'^@["\'](.+?)["\']', raw)
    if source_match:
        source_filter = source_match.group(1)
        raw = raw[source_match.end():].strip()
    k = 5
    k_match = re.search(r'\s+(\d+)$', raw)
    if k_match:
        k = int(k_match.group(1))
        raw = raw[: k_match.start()].strip()
    return raw, source_filter, k

def parse_browse(raw: str) -> tuple[str | None, int]:
    raw = raw.strip()
    if raw.lower().startswith("browse"):
        raw = raw[len("browse"):].strip()
    source_match = re.match(r'^@["\'](.+?)["\']', raw)
    if not source_match:
        source_match = re.match(r'^@(\S.*?)(?:\s+(\d+))?$', raw)
        if source_match:
            return source_match.group(1).strip(), int(source_match.group(2) or 0)
        return None, 0
    source_name = source_match.group(1)
    rest = raw[source_match.end():].strip()
    n = int(rest) if rest.isdigit() else 0
    return source_name, n

def _parse_doc(doc: str) -> tuple[str, str]:
    highlight_lines = []
    note_lines = []
    mode = None
    for line in doc.splitlines():
        if line.startswith("HIGHLIGHT:"):
            mode = "highlight"
            val = line[len("HIGHLIGHT:"):].strip()
            if val: highlight_lines.append(val)
        elif line.startswith("MY NOTE:"):
            mode = "note"
            val = line[len("MY NOTE:"):].strip()
            if val: note_lines.append(val)
        elif line.startswith("BOOK:"):
            mode = None
        elif mode == "highlight" and line.strip():
            highlight_lines.append(line.strip())
        elif mode == "note" and line.strip():
            note_lines.append(line.strip())
    return " ".join(highlight_lines).strip(), " ".join(note_lines).strip()

def _make_export_console(path: str):
    if not RICH_AVAILABLE: return None
    try:
        f = open(path, "a", encoding="utf-8")
        return Console(file=f, highlight=False, markup=False, no_color=True, width=100)
    except Exception as e:
        _print(f"[ERROR] Cannot open export file: {e}", style="red")
        return None

def _pager_prompt(is_first: bool = False, is_last: bool = False) -> str:
    if RICH_AVAILABLE:
        n_part = "[dim]\\[n]ext[/dim]" if is_last else "[bold]\\[n]ext[/bold]"
        p_part = "[dim]\\[p]rev[/dim]" if is_first else "[bold]\\[p]rev[/bold]"
        hint = f"  [dim]─[/dim] {n_part}  {p_part}  [bold]\\[q]uit[/bold]  [dim]─[/dim]"
        console.print(hint)
        try:
            key = console.input("  [dim]>[/dim] ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            return "q"
    else:
        print("  -- [n]ext  [p]rev  [q]uit paging --")
        try:
            key = input("  > ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            return "q"
    if key in ("n", ""):
        if is_last: return "q"
        return "n"
    if key == "p":
        if is_first:
            _print("  [dim](already on first page)[/dim]", style="dim")
            return "stay"
        return "p"
    return "q"

def _render_page(items: list, page: int, page_size: int, total_items: int, render_fn, export_console=None):
    start = page * page_size
    end = min(start + page_size, total_items)
    page_items = items[start:end]
    total_pages = (total_items + page_size - 1) // page_size
    page_header = f"\n── Page {page + 1}/{total_pages} (items {start + 1}–{end} of {total_items}) ──"
    _print(page_header, style="bold")
    if export_console:
        export_console.print(page_header)
    for local_i, item in enumerate(page_items):
        global_idx = start + local_i + 1
        render_fn(global_idx, total_items, item, export_console)

def _render_result_rich(idx: int, total: int, doc: str, meta: dict, distance: float, scoped: bool = False, filename: str | None = None, export_console = None):
    source = meta.get("source") or meta.get("book") or "Unknown"
    origin = meta.get("origin", "moonreader")
    doc_type = meta.get("type", "highlight")
    highlight, user_note = _parse_doc(doc)
    if doc_type == "description": badge = "[dim]SUMMARY[/dim]"
    elif origin == "external": badge = "[cyan]EXTERNAL[/cyan]"
    else: badge = "[green]HIGHLIGHT[/green]"
    if scoped: score_str = "[dim]scoped[/dim]"
    else:
        similarity = max(0.0, 1.0 - distance)
        score_color = "green" if similarity > 0.7 else "yellow" if similarity > 0.4 else "red"
        score_str = f"[{score_color}]score: {similarity:.2f}[/{score_color}]"
    title_line = f"[bold]{idx}/{total}[/bold]  [bold blue]{source}[/bold blue]  {badge}  {score_str}"
    body = Text(overflow="fold")
    if filename: body.append(f" {filename}\n\n", style="dim italic")
    if highlight: body.append(highlight, style="white")
    if user_note:
        body.append("\n\n✎ ", style="dim yellow")
        body.append(user_note, style="italic yellow")
    panel = Panel(body, title=title_line, title_align="left", box=box.ROUNDED, expand=True)
    console.print(panel)
    if export_console: export_console.print(panel)

def _render_result_plain(idx: int, total: int, doc: str, meta: dict, distance: float, scoped: bool = False, filename: str | None = None, export_file=None):
    source = meta.get("source") or meta.get("book") or "Unknown"
    doc_type = meta.get("type", "highlight")
    badge = "[SUMMARY]" if doc_type == "description" else "[HIGHLIGHT]"
    highlight, user_note = _parse_doc(doc)
    lines = [f"\n[{idx}/{total}] {badge} {source}"]
    if filename: lines.append(f"  File: {filename}")
    if highlight: lines.append(f"  {highlight}")
    if user_note: lines.append(f"  NOTE: {user_note}")
    lines.append("-" * 50)
    output = "\n".join(lines)
    print(output)
    if export_file: export_file.write(output + "\n")

def render_results(results: dict, query: str, source_filter: str | None, page_size: int = 5, filename_map: dict | None = None, export_path: str | None = None):
    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    seen = set()
    deduped = []
    for id_, doc, meta, dist in zip(ids, docs, metas, distances):
        source = (meta.get("source") or meta.get("book") or "").strip()
        highlight, _ = _parse_doc(doc)
        fp = (source, highlight.strip())
        if fp not in seen:
            seen.add(fp)
            deduped.append((id_, doc, meta, dist))
    total = len(deduped)
    if total == 0:
        msg = f"No results for '{query}'"
        if source_filter: msg += f" in '{source_filter}'"
        _print(f"\n{msg}", style="yellow")
        return
    scope_str = f" in '{source_filter}'" if source_filter else ""
    header = f"\n── {total} result(s) for '{query}'{scope_str} ──"
    _print(header, style="bold")
    export_console = _make_export_console(export_path) if export_path else None
    if export_console:
        export_console.print(header)
        for i, (id_, doc, meta, dist) in enumerate(deduped, start=1):
            source = meta.get("source") or meta.get("book") or ""
            filename = (filename_map or {}).get(source)
            _render_result_rich(i, total, doc, meta, dist, scoped=source_filter is not None, filename=filename, export_console=export_console)
    def render_item(global_idx, total_items, item, ec):
        id_, doc, meta, dist = item
        source = meta.get("source") or meta.get("book") or ""
        filename = (filename_map or {}).get(source)
        if RICH_AVAILABLE:
            _render_result_rich(global_idx, total_items, doc, meta, dist, scoped=source_filter is not None, filename=filename, export_console=None)
        else:
            _render_result_plain(global_idx, total_items, doc, meta, dist, scoped=source_filter is not None, filename=filename)
    total_pages = (total + page_size - 1) // page_size
    page = 0
    while True:
        _render_page(deduped, page, page_size, total, render_fn=render_item, export_console=None)
        if total_pages == 1: break
        action = _pager_prompt(is_first=(page == 0), is_last=(page == total_pages - 1))
        if action == "n": page += 1
        elif action == "p": page -= 1
        elif action == "stay": continue
        else: break
    if export_path:
        _print(f"\n[dim]Exported all {total} result(s) to {export_path}[/dim]", style="dim")


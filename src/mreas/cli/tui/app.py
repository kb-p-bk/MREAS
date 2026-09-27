
import sys
import time
from pathlib import Path
from mreas.cli.tui.components import RICH_AVAILABLE, console, _print, _parse_export, parse_query, parse_browse, render_results
from mreas.cli.tui.commands import cmd_browse, cmd_list_sources, cmd_stats
from mreas.cli.tui.constants import HELP_TEXT, HELP_TEXT_PLAIN, PREFETCH_LIMIT
from rich.panel import Panel

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.styles import Style
    PT_AVAILABLE = True
except ImportError:
    PT_AVAILABLE = False

PT_STYLE = Style.from_dict({
    "prompt":                              "bold ansicyan",
    "completion-menu.completion":          "bg:#1e1e2e fg:#cdd6f4",
    "completion-menu.completion.current":  "bg:#89b4fa fg:#1e1e2e bold",
    "completion-menu.meta.completion":     "bg:#1e1e2e fg:#6c7086",
}) if PT_AVAILABLE else None

class SourceCompleter(Completer):
    def __init__(self, source_names: list[str]):
        self.source_names = source_names

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        stripped = text.lstrip()
        at_pos = None
        if stripped.startswith("@"):
            at_pos = len(text) - len(stripped)
        elif stripped.lower().startswith("browse "):
            rest = stripped[len("browse "):].lstrip()
            if rest.startswith("@"):
                at_pos = len(text) - len(rest)
        if at_pos is None:
            return
        after_at = text[at_pos + 1:]
        if after_at.startswith('"') or after_at.startswith("'"):
            partial = after_at[1:]
        else:
            partial = after_at
        partial_lower = partial.lower()
        for name in self.source_names:
            if partial_lower in name.lower():
                completion_text = f'"{name}"'
                start_pos = -(len(after_at))
                yield Completion(completion_text, start_position=start_pos, display=name)

def _load_source_data() -> tuple[list[str], dict[str, str]]:
    try:
        from mreas.storage.db import get_connection
        from mreas.core.config import DB_PATH
        if DB_PATH.exists():
            conn = get_connection(DB_PATH)
            rows = conn.execute("SELECT s.name, s.filename, COUNT(c.id) as cnt FROM sources s LEFT JOIN chunks c ON c.source_id = s.id GROUP BY s.id ORDER BY cnt DESC").fetchall()
            conn.close()
            names = [r[0] for r in rows]
            filename_map = {}
            for r in rows:
                if r[1]:
                    stem = Path(r[1]).name
                    if stem and stem != r[0]:
                        filename_map[r[0]] = stem
            return names, filename_map
    except Exception:
        pass
    return [], {}

def search_notes():
    from mreas.storage.vector import MoonReaderVectorStore
    store = MoonReaderVectorStore()
    total = store.get_total_count()
    source_names, filename_map = _load_source_data()

    if RICH_AVAILABLE:
        console.print(Panel(f"[bold green]Moon Reader Extract[/bold green] — [dim]{total} entries indexed, {len(source_names)} sources[/dim]\nType [cyan]help[/cyan] for commands, [cyan]@[/cyan] then [cyan]TAB[/cyan] to search sources."))
    else:
        print(f"\nMoon Reader Extract — {total} entries indexed")
        print("Type 'help' for commands.\n")

    session = None
    if PT_AVAILABLE:
        completer = SourceCompleter(source_names)
        session = PromptSession(completer=completer, style=PT_STYLE, complete_while_typing=True)

    while True:
        try:
            if session:
                raw_input = session.prompt(HTML("<prompt>search></prompt> "))
            else:
                raw_input = input("search> ")
        except (KeyboardInterrupt, EOFError):
            break

        if not raw_input.strip():
            continue

        raw_input, export_path = _parse_export(raw_input)
        cmd_lower = raw_input.lower()

        if cmd_lower in ("q", "quit", "exit"):
            break
        elif cmd_lower == "help":
            if RICH_AVAILABLE:
                console.print(HELP_TEXT)
            else:
                print(HELP_TEXT_PLAIN)
            continue
        elif cmd_lower == "list":
            cmd_list_sources(store, export_path)
            continue
        elif cmd_lower == "stats":
            cmd_stats(store)
            continue
        elif cmd_lower.startswith("browse"):
            source_name, n = parse_browse(raw_input)
            if source_name:
                cmd_browse(source_name, n, filename_map, export_path)
            else:
                _print("[yellow]Usage: browse @\"Source Name\"[/yellow]")
            continue

        query, source_filter, k = parse_query(raw_input)
        if not query and not source_filter:
            continue

        if not query and source_filter:
            _print(f"[yellow]No search query provided. Did you mean `browse @\"{source_filter}\"`?[/yellow]")
            continue

        start_t = time.perf_counter()
        results = store.query(query, source_filter=source_filter, n_results=PREFETCH_LIMIT)
        elap = (time.perf_counter() - start_t) * 1000
        _print(f"[dim]Query took {elap:.0f}ms[/dim]", style="dim")

        render_results(results, query, source_filter, page_size=k, filename_map=filename_map, export_path=export_path)


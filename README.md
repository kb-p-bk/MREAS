# Moon Reader Extract And Search (MREAS)

A third party CLI tool for importing, embedding, and semantically searching highlights and notes from Moon Reader backups. Supports Moon Reader's native `.mrpro` backup format as well as external structured text files. All content is stored in a local SQLite database and indexed in ChromaDB for fast semantic search. 
This project is unofficial and unaffiliated with Moon Reader 

---

## Features

- Import Moon Reader `.mrpro` backup files
- Import external structured text files (notes, highlights from other sources)
- **Extensible Architecture**: Support for new data sources can be added by creating a new importer module.
- Embed content chunks into ChromaDB using vector embeddings
- Semantic search across all your imported sources
- Database and ChromaDB statistics

---

## Installation & Setup (with uv)

1. **Install dependencies and sync virtual environment:**
```bash
uv sync
```

2. **(Optional) Install global CLI wrappers to run from anywhere:**
```powershell
# PowerShell:
.\install_cli.ps1

# Or Command Prompt:
install_cli.bat
```
This places `mreas` and `mre` wrappers into `~/.local/bin` (which is already in your `PATH`).

---

## Usage

You can run commands from **any directory** using the `mreas` (or `mre`) command:

```bash
mreas <command> [arguments]
```

*(Alternatively, from the project directory: `uv run mreas <command>` or `python main.py <command>`)*

### Commands

| Command | Description |
|---|---|
| `import <file.mrpro>` | Import a Moon Reader backup file |
| `import-external <file>` | Import an external structured text file |
| `embed` | Embed all pending chunks into ChromaDB |
| `stats` | Show database and ChromaDB statistics |
| `sample` | Print a sample external import file to stdout |
| `sample <output_file>` | Write the sample external import file to a path |
| `search` | Launch the interactive semantic search UI |

### Examples

```bash
# Check database and ChromaDB stats
mreas stats

# Launch interactive semantic search
mreas search

# Import a Moon Reader backup (from any path)
mreas import "C:\path\to\your\backup.mrpro"

# Import an external notes file
mreas import-external my_notes.txt

# Embed any newly imported chunks
mreas embed

# Print the sample external file format
mreas sample

# Save the sample to a file
mreas sample template.txt

# Launch interactive search
mreas search
```

---

## Workflow

**Regular import flow:**
```bash
# 1. Import your backup (embedding happens automatically)
mreas import 2026-05-10.mrpro

# 2. Check everything looks right
mreas stats

# 3. Search your notes
mreas search
```

> Importing automatically triggers embedding for any new chunks. You only need to run `embed` manually if chunks were added to the database outside of an import command.

---

## Interactive Search (TUI)

Launch the interactive search terminal interface with:

```bash
mreas search
# or shortcut:
mre search
```

### Search & Browse Syntax

| Syntax | Description | Example |
|---|---|---|
| `<query>` | Semantic search across all sources (default 5 results/page) | `fast pattern matching` |
| `<query> <k>` | Search with custom results per page | `decision making 10` |
| `@<partial>` + `Tab` | Autocomplete book/source title | `@Exam` &rarr; `@"Example Book Title"` |
| `@"Source" <query>` | Scope search to a specific book/source | `@"Example Book Title" heuristics` |
| `@"Source" <query> <k>` | Scoped search with custom page size | `@"Example Book Title" fascism 8` |
| `browse @"Source"` | Read all bookmarks from a source in order | `browse @"Example Book Title"` |
| `browse @"Source" <n>` | Browse first *n* bookmarks from a source | `browse @"Example Book Title" 20` |
| `list` | List all indexed books/sources with chunk counts | `list` |
| `stats` | Show database and ChromaDB counts from within search | `stats` |
| `help` | Display search help | `help` |
| `q` / `quit` / `exit` | Exit search | `q` |

### Pagination Controls
When results span multiple pages:
- **`Enter`** or **`n`**: Next page
- **`p`**: Previous page
- **`q`**: Quit paging and return to search prompt

### Exporting Results
Append `> filename` to any search, browse, or list command to export **all matching results** to a text file:
```text
memory and learning > memory_notes.txt
browse @"Example Book Title" > book_highlights.txt
list > all_books.txt
```

---

## External File Format

If you want to import notes from sources other than Moon Reader, use the external import format. To see the expected structure:

```bash
mreas sample
```

Or save a template to edit:

```bash
mreas sample my_notes.txt
```

---

## Getting Help

```bash
mreas --help
```
## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for architecture overview and instructions on adding new importers.

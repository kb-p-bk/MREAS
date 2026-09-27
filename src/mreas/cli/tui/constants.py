
PREFETCH_LIMIT = 50

HELP_TEXT = """
[bold]Search:[/bold]
  [cyan]<query>[/cyan]                       Search all sources (5 per page)
  [cyan]<query> <k>[/cyan]                   Set page size to k results
  [cyan]@"Source Name" <query>[/cyan]        Scope to a specific source
  [cyan]@"Source Name" <query> <k>[/cyan]    Scoped + custom page size

[bold]Pagination:[/bold]
  After results appear: [cyan]n[/cyan] / Enter = next page, [cyan]p[/cyan] = prev page, [cyan]q[/cyan] = quit paging

[bold]Browse:[/bold]
  [cyan]browse @"Source Name"[/cyan]         List all bookmarks (paginated)
  [cyan]browse @"Source Name" <n>[/cyan]     Browse first n bookmarks

[bold]@ Autocomplete:[/bold]
  Type [cyan]@[/cyan] then press [cyan]TAB[/cyan] to see matching sources.
  Works with any substring: [cyan]@musso TAB[/cyan], [cyan]@dawn TAB[/cyan]

[bold]Export — append [cyan]> filename[/cyan] to any command:[/bold]
  [cyan]memory and learning > results.txt[/cyan]
  [cyan]browse @"Mussolini" > mussolini.txt[/cyan]
  [cyan]@"A New World Begins" revolution > out.txt[/cyan]
  [cyan]list > sources.txt[/cyan]
  (exports ALL pages/results, not just the current page)

[bold]Commands:[/bold]
  [cyan]list[/cyan]                          List all indexed sources
  [cyan]stats[/cyan]                         Show statistics
  [cyan]help[/cyan]                          Show this help
  [cyan]q / quit / exit[/cyan]               Quit
"""

HELP_TEXT_PLAIN = """
Search:
  <query>                     Search all sources (5 per page)
  <query> <k>                 Set page size to k results
  @"Source Name" <query>      Scope to a specific source
  Type @ then TAB for source autocomplete

Pagination:
  n / Enter = next page   p = prev page   q = quit paging

Browse:
  browse @"Source Name"       List all bookmarks (paginated)
  browse @"Source Name" <n>   Browse first n bookmarks

Export (append to any command, exports all pages):
  memory and learning > results.txt
  browse @"Mussolini" > mussolini.txt
  list > sources.txt

Commands:
  list    List all indexed sources
  stats   Show statistics
  help    Show this help
  q       Quit
"""

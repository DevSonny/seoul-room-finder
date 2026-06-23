# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Overview

A housing guide generator for Kyung Hee University (Seoul) exchange students on a
one-semester stay. It produces a responsive web guide and an Excel workbook of
curated room listings, neighborhood guides, and English-friendly rental platforms
near the KHU Seoul campus (Hoegi-dong area).

## Build / run

```bash
python3 build.py
```

This writes `rooms.html` and `rooms.xlsx` next to `build.py`. The Excel output
requires `openpyxl` (`pip install openpyxl`); it is imported lazily inside
`build_xlsx`, so the HTML can still build without it if you call `build_html`
directly. No other dependencies — everything else is Python 3 stdlib.

There are no tests, linters, or build configuration files (no `package.json`,
`Makefile`, or `requirements.txt`).

> **⚠️ `build.py` is currently out of sync with the committed HTML.** The
> committed `rooms.html` / `index.html` are the "v2" redesign (Inter font, CSS
> variables, JS sort/filter/pagination, mobile cards), but the v2 commit changed
> only those HTML files — **not** `build.py`. The generator still emits the older,
> simpler v1 page. **Running `python3 build.py` will overwrite the v2 design with v1.**
> Before regenerating, either (a) port the v2 markup/styles back into `build_html`,
> or (b) edit the HTML files directly and treat `build.py` as legacy.

## Architecture

**Single-file design.** `build.py` (~370 lines) is both the data source and the
generator. To change anything in the output, edit `build.py` and re-run it.

Data blocks (edit these to change content):
- `featured` — concrete room listings.
- `areas` — neighborhood guide rows (tuples).
- `platforms` — rental platform rows (tuples).
- `suggestions` — extra tips (title/detail pairs).

Generators and helpers:
- `build_html()` — returns the full HTML page as a string.
- `build_xlsx(path)` — writes the 4-sheet workbook (Featured / Neighborhood guide /
  Platforms / Tips) via `openpyxl`; `style_sheet` is the shared sheet formatter.
- `naver(q)`, `ziptoss_en(area)` — build live search URLs.
- `th(cells)`, `td(...)` — HTML table row/cell helpers.

The `__main__` block (bottom of the file) writes `rooms.html` and `rooms.xlsx`.

## Output files

`rooms.html`, `index.html` (the landing page copy), and `rooms.xlsx` are the
deliverables. In a synced project these would be pure build artifacts of `build.py`
— but see the warning above: the committed HTML is the hand-maintained v2 design,
while `build.py` still produces v1. Until they are reconciled, treat the HTML files
as the source of truth for the published guide and `build.py` as the (stale) Excel +
v1 generator. `build.py` writes `rooms.html` only, never `index.html`.

## Conventions

- `snake_case` for functions; `SNAPSHOT` constant holds the data snapshot date.
- HTML is built with f-strings and direct string concatenation (no template engine);
  escape user-facing strings with `html.escape()`.
- Mobile-responsive layout with a 720px breakpoint (tables collapse to cards).
- Snapshot date and "prices change — verify on platform" caveat appear in both
  outputs; keep `SNAPSHOT` current when refreshing data.

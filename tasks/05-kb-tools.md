- [x] Build the Python KB tools (ingest/compile/query/lint)

## Why
The plugin is the UI; the tools are the engine. Each tool is a tiny python
script runnable with `uv run`. None of them call an LLM directly — they
generate prompts and hand them off to `claude` (Claude Code) as a subprocess,
or write prompt files into `.llm-kb/queue/` for the user to run by hand.

## Scripts
- `tools/ingest/ingest.py` — normalize a new file into `raw/` (strip weird
  characters in filename, add frontmatter with `source`, `ingested_at`).
- `tools/compile/compile.py` — walk `raw/`, diff against `wiki/`, emit a
  compile prompt that Claude Code should run. Writes `log.md` entry.
- `tools/query/query.py "<question>"` — emit a query prompt that references
  the current `index.md`, and pre-create the answer stub under
  `wiki/derived/`.
- `tools/lint/lint.py` — scan wiki/ for dangling links, duplicate headings,
  empty files, orphan raw files, stale frontmatter. Emits a lint report.

## Done when
- `tools/pyproject.toml` exists (uv-managed).
- Each script has a `--help` that works and a dry-run mode.
- `uv run tools/lint/lint.py --vault /Users/caesarchi/Dropbox/caesar_obsidian`
  exits 0 on a clean vault.

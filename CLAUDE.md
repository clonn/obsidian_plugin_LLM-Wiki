# CLAUDE.md — project_Obsidian_graph

This repo hosts two deliverables that work together:

1. **`plugin/`** — Obsidian plugin (`llm-kb`) that exposes a command palette
   bridge to run the Karpathy-style knowledge-base workflow from inside Obsidian.
2. **`tools/`** — Python + shell utilities (managed with **`uv`**) that run the
   compile / query / lint loops against the user's Obsidian vault.

## Target Obsidian vault

```
/Users/caesarchi/Dropbox/caesar_obsidian
```

All KB structure lives **inside the vault**, not in this repo:

```
caesar_obsidian/
├─ raw/              # ingested sources — immutable
├─ wiki/             # AI-compiled concept articles
│  ├─ concepts/
│  ├─ projects/
│  ├─ people/
│  └─ derived/       # query answers, slides, charts
├─ index.md          # entry point, summaries of every file
├─ log.md            # compile / query / lint run log
└─ _archive/         # legacy unorganized notes that were migrated
```

## Golden rules

1. **Every step is a commit.** No "later." Commit after every atomic change.
2. **Python tooling = `uv` only.** Never `pip install` directly, never a bare
   `python` venv. Use `uv run`, `uv add`, `uv sync`.
3. **No destructive moves in the user's vault without a dry-run first.** Every
   reorganization script must support `--dry-run` and default to it.
4. **Traditional Chinese (zh-TW)** for all KB content (notes, wiki articles,
   log entries). Code + comments in English.
5. **Self-verify, don't ask.** When uncertain, read the vault, read the code,
   read Karpathy's gist — don't block on questions.
6. **Tasks are tracked as files** under `tasks/` — one `.md` per task, each
   with a checkbox that gets flipped to `[x]` on completion and committed.

## References
- Karpathy gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Karpathy tweet: https://x.com/karpathy/status/2039805659525644595
- Obsidian API: https://docs.obsidian.md/Home
- graphify: https://graphify.net/

## Architecture (Karpathy's four phases)

1. **Ingest** → raw/ (web clipper, PDFs, transcripts — append-only)
2. **Compile** → wiki/ (LLM reads raw/, emits concept articles + backlinks + index)
3. **Query** → ask questions against wiki/, file answers back into wiki/derived/
4. **Lint** → scan for contradictions, gaps, dead links → loop back to Compile

The Obsidian plugin is the **front door**: it surfaces these four actions as
commands and shows KB status in the sidebar. The heavy lifting is done by
Claude Code running the tools in `tools/` against the vault.

## Subagent
`.claude/agents/kb-verifier.md` defines a verifier subagent that checks the
integrity of the KB (every raw file referenced somewhere, no dangling links,
no empty files, no duplicate titles). Run it after every compile / lint pass.

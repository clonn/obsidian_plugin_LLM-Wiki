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
- AgriciDaniel claude-obsidian: https://github.com/AgriciDaniel/claude-obsidian
- Obsidian API: https://docs.obsidian.md/Home
- graphify: https://graphify.net/

## Architecture (Karpathy's four phases + AgriciDaniel extensions)

1. **Ingest** → raw/ (web clipper, PDFs, transcripts — append-only)
2. **Compile** → wiki/ (LLM reads raw/, emits concept articles + backlinks + index)
3. **Query** → ask questions against wiki/, file answers back into wiki/derived/
4. **Lint** → scan for contradictions, gaps, dead links → loop back to Compile

Extensions from AgriciDaniel's claude-obsidian:
5. **Hot cache** → `wiki/hot.md` preserves session context (~500 words)
6. **Save** → `/save` converts conversation insights into permanent wiki notes
7. **Autoresearch** → `/autoresearch` autonomous web research → wiki pages
8. **Wiki-ingest** → `/wiki-ingest` enhanced ingestion with entity/concept extraction

The Obsidian plugin is the **front door**: it surfaces these actions as
commands and shows KB status in the sidebar. The heavy lifting is done by
Claude Code running the tools in `tools/` against the vault.

## Vault structure (expanded)

```
caesar_obsidian/
├─ raw/              # ingested sources — immutable
├─ wiki/             # AI-compiled concept articles
│  ├─ concepts/
│  ├─ projects/
│  ├─ people/
│  ├─ derived/       # query answers, synthesis
│  └─ hot.md         # session context cache
├─ notes/            # user's hand-written notes, categorized
├─ index.md          # entry point, summaries of every file
├─ log.md            # compile / query / lint run log
├─ 知識圖譜.canvas    # visual knowledge map
└─ _archive/         # archived: sensitive, junk, ops, prompts
```

## Claude Code hooks (`.claude/settings.json`)

- **SessionStart** — reads `wiki/hot.md` to restore context
- **PostToolUse** — auto-commits wiki/ and raw/ changes on Write/Edit

## Skills (`.claude/skills/`)

- `/save` — file conversation insights as permanent wiki notes
- `/autoresearch <topic>` — autonomous web research loop
- `/wiki-ingest <source>` — enhanced ingestion with entity extraction

## Python tools (`tools/`)

| Module | Description |
|--------|-------------|
| `compile.compile` | Compile prompt generator (`--status`, `--incremental`) |
| `query.query` | Multi-mode query (`--mode quick\|standard\|deep`) |
| `search.search` | TF-IDF search with CJK support (`--json-out`) |
| `lint.lint` | 8-category lint (`--category`, `--json-out`) |
| `link.autolink` | Title-mention auto-linker |
| `graph.export_graph` | JSON graph export |
| `graph.analyze` | Deep graph analysis + canvas generation |
| `graph.strengthen` | Wiki cross-links + isolated→hub connections |
| `status.dashboard` | Knowledge coverage dashboard |
| `ingest.ingest` | Single-file ingestion |
| `batch_ingest.batch_ingest` | Bulk ingestion |

## Subagents

- `.claude/agents/kb-verifier.md` — independent integrity checker (read-only)

Run the verifier after every compile / lint pass.

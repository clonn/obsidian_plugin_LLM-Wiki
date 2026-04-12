# project_Obsidian_graph

A Karpathy-style LLM knowledge base for an Obsidian vault, plus the Obsidian
plugin that drives it.

> Vault target: `/Users/caesarchi/Dropbox/caesar_obsidian`

See [`CLAUDE.md`](./CLAUDE.md) for architecture, invariants, and how this repo
is organized. See [`tasks/`](./tasks/) for the execution log.

## How to use

### 1. In Obsidian

Enable the **LLM Knowledge Base** plugin (it's already symlinked into the
vault at `.obsidian/plugins/llm-kb`). Open the Command Palette
(<kbd>Cmd+P</kbd>) and type `LLM-KB` to see:

- **Ingest current note into raw/** — copies the active note to
  `raw/YYYY-MM-DD_<slug>.md`
- **Compile wiki from raw/** — runs the compile prompt builder
- **Ask the wiki** — opens a question modal
- **Lint wiki** — scans for issues
- **Open index.md** — jump to the KB entry point
- **Open log sidebar** — streaming output of CLI runs

### 2. From the terminal (tools/)

```bash
cd tools && uv sync          # one-time
uv run python -m compile.compile  --vault ~/Dropbox/caesar_obsidian
uv run python -m query.query      --vault ~/Dropbox/caesar_obsidian "你的問題"
uv run python -m lint.lint        --vault ~/Dropbox/caesar_obsidian
uv run python -m ingest.ingest    --vault ~/Dropbox/caesar_obsidian /path/to/file.md
```

### 3. The daily loop (Karpathy workflow)

1. **Collect** — Web Clipper or drag files into `raw/`.
2. **Compile** — `LLM-KB: Compile wiki from raw/` → hand the prompt to
   Claude Code.
3. **Query** — Ask questions, answers go into `wiki/derived/`.
4. **Lint** — Run periodically to catch contradictions and dead links.

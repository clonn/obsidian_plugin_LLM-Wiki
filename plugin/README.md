# llm-kb — Obsidian plugin

Karpathy-style LLM knowledge base commands inside Obsidian. Bridges the
vault to the python tools in `../tools/`.

## Commands

| Command                         | What it does                                              |
|---------------------------------|-----------------------------------------------------------|
| **LLM-KB: Ingest current note** | Move active note into `raw/YYYY-MM-DD_<slug>.md`          |
| **LLM-KB: Compile wiki**        | Runs `uv run python -m compile.compile --vault <vault>`   |
| **LLM-KB: Ask the wiki**        | Opens a modal, runs `query.query` with your question      |
| **LLM-KB: Lint wiki**           | Runs `uv run python -m lint.lint --vault <vault>`         |
| **LLM-KB: Open index.md**       | Quick jump to index.md                                    |
| **LLM-KB: Open log sidebar**    | Reveal the streaming log pane                             |

Status bar shows `raw:N · wiki:M`.

## Install (dev mode)

```bash
cd plugin
npm install
npm run build      # produces main.js
```

Then symlink the plugin folder into your vault's plugin dir:

```bash
mkdir -p "/Users/caesarchi/Dropbox/caesar_obsidian/.obsidian/plugins"
ln -s "$(pwd)" \
  "/Users/caesarchi/Dropbox/caesar_obsidian/.obsidian/plugins/llm-kb"
```

Enable it in **Settings → Community plugins → LLM Knowledge Base**.

## Settings

- **Tools path** — absolute path to `project_Obsidian_graph/tools/`
  (defaults to `/Users/caesarchi/workspace/clonn/project_Obsidian_graph/tools`)
- **uv command** — the uv binary (default `uv`)
- **Claude Code command** — the Claude CLI binary (default `claude`)
- **Language** — `zh-TW` or `en` (default `zh-TW`)

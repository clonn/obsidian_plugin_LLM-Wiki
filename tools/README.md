# tools/

Python utilities for the LLM knowledge base, managed with **`uv`**.

```bash
cd tools
uv sync                  # one-time
uv run audit/vault_audit.py --vault ~/Dropbox/caesar_obsidian
uv run lint/lint.py      --vault ~/Dropbox/caesar_obsidian
uv run organize/reorganize.py --vault ~/Dropbox/caesar_obsidian --dry-run
```

Each subfolder is a single-purpose CLI. None of them call an LLM directly —
they produce prompt bundles that get handed off to Claude Code.

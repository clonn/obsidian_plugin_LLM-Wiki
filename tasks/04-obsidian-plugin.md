- [ ] Build the `llm-kb` Obsidian plugin

## Why
The user wants an in-Obsidian front door to the Karpathy workflow so they
don't have to keep switching to a terminal.

## Scope (MVP)
Plugin id: `llm-kb`. Commands:
1. **LLM-KB: Ingest current note into raw/** — moves/copies the active note
   under `raw/` with a timestamped filename.
2. **LLM-KB: Compile wiki from raw/** — shells out to
   `tools/compile/compile.py` via Node `child_process` and streams log to a
   sidebar view.
3. **LLM-KB: Ask the wiki** — prompt modal, writes the query + answer stub to
   `wiki/derived/` as a new note.
4. **LLM-KB: Lint wiki** — runs `tools/lint/lint.py`, shows issues in a
   sidebar view.
5. **LLM-KB: Open index.md** — quick jump.

Plus a **status bar** item showing counts: `raw:N · wiki:M · last-compile:…`.

Plus a **settings tab** for:
- path to `tools/` (where the python scripts live)
- Claude Code CLI command (default: `claude`)
- Language for compile output (default: `zh-TW`)

## Done when
- `plugin/` contains a working Obsidian plugin:
  - `manifest.json`, `package.json`, `tsconfig.json`, `esbuild.config.mjs`
  - `src/main.ts` with the commands + settings tab + status bar
  - `src/sidebarView.ts` for the log panel
  - `README.md` with install instructions
- `npm run build` produces `main.js` inside `plugin/`
- Installation doc explains symlinking into
  `<vault>/.obsidian/plugins/llm-kb/`

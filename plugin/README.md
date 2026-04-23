# obsidian-llm-wiki

Karpathy-style LLM knowledge base commands inside Obsidian. Bridges your
vault to a set of Python tools driven by [Claude Code](https://claude.com/claude-code).

Inspired by
[Karpathy's knowledge-base gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
— four phases: **ingest → compile → query → lint**, plus autolink, graph
analysis, dashboard, and a pipeline that scans a `Clippings/` folder and
routes new material into `raw/`.

## Commands

| Command                          | What it does                                                 |
|----------------------------------|--------------------------------------------------------------|
| **Ingest current note**          | Move active note into `raw/YYYY-MM-DD_<slug>.md`             |
| **Compile status**               | Report vault coverage / stale articles                       |
| **Compile: generate prompt**     | Generate the incremental compile prompt for Claude Code      |
| **Ask wiki (quick / std / deep)**| Query the wiki in 3 depth modes                              |
| **Lint wiki**                    | 8-category integrity check                                   |
| **Pipeline: scan & ingest**      | `Clippings/ → raw/ → compile → link`                         |
| **Pipeline: watch mode**         | Continuous version of the above                              |
| **Search wiki**                  | TF-IDF search (CJK-aware)                                    |
| **Auto-link notes**              | Title-mention auto-linker                                    |
| **Export / Analyze / Strengthen graph** | Link-graph tooling (+ canvas generation)              |
| **Knowledge dashboard**          | Coverage + hot-node summary                                  |
| **Open index.md / log sidebar**  | Quick navigation                                             |

Status bar shows `raw:N · wiki:M`.

## Requirements

This plugin is a thin Obsidian front-end for Python tools that live in a
separate repo:

- [`clonn/obsidian_plugin_LLM-Wiki`](https://github.com/clonn/obsidian_plugin_LLM-Wiki)
  — contains the `tools/` directory invoked by every command.
- [`uv`](https://docs.astral.sh/uv/) — runs the Python tools.
- [Claude Code](https://claude.com/claude-code) — used by the compile /
  query loops. Optional for commands that only touch the filesystem.

## Install

### From the Obsidian community registry

Once listed: **Settings → Community plugins → Browse → LLM Wiki**.

### Manual install

1. Download `main.js`, `manifest.json`, `styles.css` from the
   [latest release](https://github.com/clonn/obsidian_plugin_LLM-Wiki/releases).
2. Place them inside your vault:
   ```
   <your-vault>/.obsidian/plugins/obsidian-llm-wiki/
   ```
3. Enable in **Settings → Community plugins**.

### From source

```bash
git clone https://github.com/clonn/obsidian_plugin_LLM-Wiki.git
cd obsidian_plugin_LLM-Wiki/plugin
npm install
npm run build        # produces main.js
```

Then symlink the `plugin/` folder into your vault's plugins directory:

```bash
ln -s "$(pwd)" "<your-vault>/.obsidian/plugins/obsidian-llm-wiki"
```

## Settings

| Setting                         | Default    | Notes                                           |
|---------------------------------|------------|-------------------------------------------------|
| **Tools path**                  | *(empty)*  | Absolute path to the `tools/` dir of the repo   |
| **uv command**                  | `uv`       | Full path recommended on macOS (e.g. `/opt/homebrew/bin/uv`) |
| **Claude Code command**         | `claude`   | CLI binary used by compile prompts              |
| **Language**                    | `zh-TW`    | `zh-TW` or `en` — language for compile / query  |
| **Auto-run pipeline on startup**| `true`     | Runs `pipeline.pipeline --apply` after load     |

If **Tools path** is empty, auto-run is skipped with a notice.

## License

MIT © [clonn](https://github.com/clonn)

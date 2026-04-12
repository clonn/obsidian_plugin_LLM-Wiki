# LLM-Wiki: Karpathy-Style LLM Knowledge Base for Obsidian

A complete implementation of [Andrej Karpathy's LLM knowledge base system](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — an Obsidian plugin + Python CLI tools that let an LLM act as a **compiler** for your personal knowledge base. No vector databases, no embeddings. Just markdown, backlinks, and a large-context LLM.

## What this is

You collect raw sources (articles, PDFs, transcripts). The LLM reads them and compiles a structured, interlinked wiki. You query the wiki, and the answers get filed back in. Over time, the wiki grows into a comprehensive knowledge graph — maintained by AI, directed by you.

```
raw/  ──Ingest──►  LLM Compiler  ──Compile──►  wiki/
                       ▲                          │
                       │         Query ◄──────────┘
                       │           │
                       └───Lint────┘
```

---

## Quick Start (One Command)

### Prerequisites

| Tool | Install |
|------|---------|
| [Obsidian](https://obsidian.md/) v1.5+ | Download from obsidian.md |
| [Node.js](https://nodejs.org/) v20+ | `brew install node` |
| [uv](https://docs.astral.sh/uv/) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Claude Code](https://claude.ai/code) | `npm install -g @anthropic-ai/claude-code` |

### Install

```bash
git clone https://github.com/clonn/obsidian_plugin_LLM-Wiki.git
cd obsidian_plugin_LLM-Wiki

# One command does everything:
./install.sh ~/path/to/your/obsidian-vault
```

The install script will:
1. Build the Obsidian plugin (`npm install` + `npm run build`)
2. Install Python tools (`uv sync`)
3. Symlink the plugin into your vault's `.obsidian/plugins/`
4. Register `llm-kb` in `community-plugins.json`
5. Create the KB folder structure (`raw/`, `wiki/`, `notes/`, `_archive/`)

Then **restart Obsidian** and:
1. **Settings** > **Community plugins** > turn off **Restricted mode**
2. Find **LLM Knowledge Base** in the list > **Enable**
3. <kbd>Cmd+P</kbd> > type `LLM-KB` > you're in

> **Tip:** If the vault is at `~/Dropbox/caesar_obsidian` or
> `~/Library/CloudStorage/Dropbox/caesar_obsidian`, the script auto-detects
> it — just run `./install.sh` with no arguments.

### Manual Install (if you prefer)

<details>
<summary>Click to expand manual steps</summary>

```bash
# 1. Build plugin
cd plugin && npm install && npm run build && cd ..

# 2. Install Python tools
cd tools && uv sync && cd ..

# 3. Symlink into vault (use your actual vault path)
VAULT="$HOME/Library/CloudStorage/Dropbox/caesar_obsidian"
mkdir -p "$VAULT/.obsidian/plugins"
ln -sfn "$(pwd)/plugin" "$VAULT/.obsidian/plugins/llm-kb"

# 4. Create KB folders
mkdir -p "$VAULT"/{raw,wiki/concepts,wiki/projects,wiki/people,wiki/derived,_archive,notes}
```

Then restart Obsidian and enable the plugin.

</details>

---

## Usage

### In Obsidian (Cmd+P)

| Command | What it does |
|---------|-------------|
| **LLM-KB: Ingest current note** | Copy active note into `raw/YYYY-MM-DD_<slug>.md` with frontmatter |
| **LLM-KB: Compile wiki** | Generate a compile prompt for Claude Code |
| **LLM-KB: Ask the wiki** | Open a question modal, create answer stub in `wiki/derived/` |
| **LLM-KB: Lint wiki** | Scan for empty files, dangling links, duplicates, orphans |
| **LLM-KB: Open index.md** | Jump to the knowledge base entry point |
| **LLM-KB: Open log sidebar** | Show streaming output of CLI runs |

Status bar shows live counts: `raw:N · wiki:M`.

### From Terminal

```bash
cd tools

# Audit your vault
uv run python -m audit.vault_audit --vault <YOUR_VAULT>

# Ingest a new source
uv run python -m ingest.ingest --vault <YOUR_VAULT> /path/to/article.md

# Compile raw/ into wiki/ (generates a prompt for Claude Code)
uv run python -m compile.compile --vault <YOUR_VAULT>

# Ask a question
uv run python -m query.query --vault <YOUR_VAULT> "your question here"

# Lint — check wiki integrity
uv run python -m lint.lint --vault <YOUR_VAULT>

# Reorganize — sort scattered files into notes/<category>/
uv run python -m organize.reorganize --vault <YOUR_VAULT> --dry-run   # preview first
uv run python -m organize.reorganize --vault <YOUR_VAULT> --apply     # then apply
```

### With Claude Code

The compile and query tools generate **prompt bundles** in `.llm-kb/queue/`. Hand them to Claude Code:

```bash
# Option A: let Claude Code read and execute the prompt
claude "Read .llm-kb/queue/compile_*.md and execute the instructions"

# Option B: use the Obsidian plugin sidebar — it streams output live
```

---

## Architecture (Karpathy's Four Phases)

Based on [Karpathy's tweet](https://x.com/karpathy/status/2039805659525644595):

| Phase | Action | Where |
|-------|--------|-------|
| **1. Ingest** | Collect sources (Web Clipper, PDFs, transcripts) | `raw/` (append-only) |
| **2. Compile** | LLM reads `raw/`, builds concept articles with backlinks | `wiki/` |
| **3. Query** | Ask questions, file answers back into the wiki | `wiki/derived/` |
| **4. Lint** | Scan for contradictions, gaps, dead links → loop back to Compile | `wiki/` |

The wiki keeps growing. Every question you ask becomes part of the knowledge base.

---

## Vault Structure

```
your-vault/
├── raw/                    # Ingested sources (append-only)
├── wiki/                   # LLM-compiled articles
│   ├── concepts/           #   frameworks, methods, terms
│   ├── projects/           #   project-specific articles
│   ├── people/             #   people profiles
│   └── derived/            #   query answers filed back
├── notes/                  # Your organized working notes
│   ├── ai-tooling/         #   Claude, LLM tools, AI guides
│   ├── blog-drafts/        #   drafts
│   ├── business/           #   strategy, company ops
│   ├── cymkube/            #   Cymkube / DX Team
│   ├── finance/            #   trading, payments
│   ├── infra/              #   servers, credentials
│   ├── openclaw/           #   OpenClaw / lobster
│   ├── people-meetings/    #   contacts, meeting notes
│   ├── sowork/             #   sowork HR OS
│   └── assets/             #   images
├── _archive/               # Frozen legacy notes
├── index.md                # KB entry point (auto-maintained)
├── log.md                  # Execution history
└── .llm-kb/queue/          # Prompt bundles for Claude Code
```

## Repo Structure

```
obsidian_plugin_LLM-Wiki/
├── install.sh              # One-command setup
├── plugin/                 # Obsidian plugin (TypeScript)
│   ├── src/main.ts         #   commands, status bar, settings
│   ├── manifest.json
│   ├── main.js             #   built artifact (checked in)
│   └── styles.css
├── tools/                  # Python CLIs (uv-managed)
│   ├── audit/              #   vault_audit.py
│   ├── ingest/             #   ingest.py
│   ├── compile/            #   compile.py
│   ├── query/              #   query.py
│   ├── lint/               #   lint.py
│   ├── organize/           #   reorganize.py
│   └── pyproject.toml
├── .claude/agents/
│   └── kb-verifier.md      #   independent verification subagent
├── tasks/                  #   execution log (all checked off)
├── CLAUDE.md               #   AI assistant instructions
└── README.md
```

## Plugin Settings

Open **Settings > LLM Knowledge Base** in Obsidian:

| Setting | Default | Description |
|---------|---------|-------------|
| Tools path | auto-detected | Absolute path to the `tools/` directory |
| uv command | `uv` | Path to the uv binary |
| Claude Code command | `claude` | Path to the Claude Code CLI |
| Language | `zh-TW` | Output language (Traditional Chinese / English) |

---

## The Daily Workflow

```
Morning:
  1. Read articles → Obsidian Web Clipper saves to raw/
  2. Cmd+P → "LLM-KB: Compile wiki" → Claude Code builds wiki articles

Anytime:
  3. Cmd+P → "LLM-KB: Ask the wiki" → ask questions, answers saved

Weekly:
  4. Cmd+P → "LLM-KB: Lint wiki" → fix contradictions, fill gaps
  5. Review index.md → see the big picture
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Plugin not showing in Obsidian | Restart Obsidian. Check Settings > Community plugins > Restricted mode is **OFF** |
| `ENOENT: no such file or directory` | Symlink is broken. Re-run `./install.sh <vault-path>` |
| `uv: command not found` | Install uv: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Compile says "0 raw files" | Ingest some notes first: Cmd+P > "LLM-KB: Ingest current note" |
| Reorganize says "0 operations" | Files are already organized. This is normal after first run. |
| Plugin settings show wrong path | Open Settings > LLM Knowledge Base > update "Tools path" |
| macOS Dropbox path issue | Dropbox moved to `~/Library/CloudStorage/Dropbox/` on newer macOS. The install script handles this automatically. |

## References

| Resource | Link |
|----------|------|
| Karpathy's system (Gist) | [github.com/karpathy/442a6bf...](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) |
| Karpathy's tweet | [x.com/karpathy/status/2039805659525644595](https://x.com/karpathy/status/2039805659525644595) |
| Obsidian API docs | [docs.obsidian.md](https://docs.obsidian.md/Home) |
| Obsidian Web Clipper | [obsidian.md/clipper](https://obsidian.md/clipper) |
| graphify | [graphify.net](https://graphify.net/) |
| uv (Python package manager) | [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| Claude Code | [claude.ai/code](https://claude.ai/code) |

## License

MIT

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

## Quick Start

### Prerequisites

- [Obsidian](https://obsidian.md/) (v1.5+)
- [Node.js](https://nodejs.org/) (v20+)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Claude Code](https://claude.ai/code) (the LLM compiler brain)

### Step 1: Clone and build

```bash
git clone https://github.com/clonn/obsidian_plugin_LLM-Wiki.git
cd obsidian_plugin_LLM-Wiki

# Build the Obsidian plugin
cd plugin
npm install
npm run build          # produces main.js

# Install the Python tools
cd ../tools
uv sync                # creates .venv and installs deps
```

### Step 2: Link the plugin into your vault

```bash
# Replace <YOUR_VAULT> with your Obsidian vault path
VAULT="$HOME/Dropbox/caesar_obsidian"

mkdir -p "$VAULT/.obsidian/plugins"
ln -sfn "$(pwd)/../plugin" "$VAULT/.obsidian/plugins/llm-kb"
```

Then in Obsidian:
1. **Settings** > **Community plugins** > turn off **Restricted mode**
2. Find **LLM Knowledge Base** in the installed list and **Enable** it
3. (Optional) Go to plugin settings to adjust paths

### Step 3: Initialize the KB structure in your vault

The system expects these folders inside your vault. Create them if they don't exist:

```bash
VAULT="$HOME/Dropbox/caesar_obsidian"

mkdir -p "$VAULT/raw"
mkdir -p "$VAULT/wiki/concepts"
mkdir -p "$VAULT/wiki/projects"
mkdir -p "$VAULT/wiki/people"
mkdir -p "$VAULT/wiki/derived"
mkdir -p "$VAULT/_archive"
```

Or simply run the organize tool which sets everything up:

```bash
cd tools
uv run python -m organize.reorganize --vault "$VAULT" --dry-run   # preview
uv run python -m organize.reorganize --vault "$VAULT" --apply      # execute
```

### Step 4: Start the loop

You're ready. Open Obsidian and press <kbd>Cmd+P</kbd>, type `LLM-KB`.

---

## Usage

### In Obsidian (Command Palette)

| Command | What it does |
|---------|-------------|
| **LLM-KB: Ingest current note** | Copy active note into `raw/YYYY-MM-DD_<slug>.md` with frontmatter |
| **LLM-KB: Compile wiki** | Generate a compile prompt for Claude Code |
| **LLM-KB: Ask the wiki** | Open a question modal, create answer stub in `wiki/derived/` |
| **LLM-KB: Lint wiki** | Scan for empty files, dangling links, duplicates, orphans |
| **LLM-KB: Open index.md** | Jump to the knowledge base entry point |
| **LLM-KB: Open log sidebar** | Show streaming output of CLI runs |

The status bar shows live counts: `raw:N · wiki:M`.

### From Terminal (CLI)

```bash
cd tools

# Audit — read-only inventory of your vault
uv run python -m audit.vault_audit --vault ~/Dropbox/caesar_obsidian

# Ingest — add a new source to raw/
uv run python -m ingest.ingest --vault ~/Dropbox/caesar_obsidian /path/to/article.md

# Compile — generate prompt for Claude Code to compile raw/ into wiki/
uv run python -m compile.compile --vault ~/Dropbox/caesar_obsidian

# Query — ask a question, stub the answer in wiki/derived/
uv run python -m query.query --vault ~/Dropbox/caesar_obsidian "LLM 知識庫的四個階段是什麼？"

# Lint — check wiki integrity
uv run python -m lint.lint --vault ~/Dropbox/caesar_obsidian

# Reorganize — classify and move scattered files into notes/<category>/
uv run python -m organize.reorganize --vault ~/Dropbox/caesar_obsidian --dry-run
uv run python -m organize.reorganize --vault ~/Dropbox/caesar_obsidian --apply
```

### With Claude Code (the LLM compiler)

The tools generate **prompt bundles** in `.llm-kb/queue/`. Hand these to Claude Code:

```bash
# After running compile, Claude Code reads the prompt and does the work:
claude "Read the file at .llm-kb/queue/compile_2026-04-11T23-47-25.md and execute it"
```

Or use the plugin's sidebar — it streams the output live.

---

## Architecture (Karpathy's Four Phases)

Based on Andrej Karpathy's [LLM knowledge base architecture](https://x.com/karpathy/status/2039805659525644595):

### Phase 1: Ingest

Sources land in `raw/`. The Web Clipper, PDFs, transcripts, meeting notes — all go here. **Append-only, never modified.**

### Phase 2: Compile (LLM Compiler)

Claude Code reads `raw/` and builds structured wiki articles:
- `wiki/concepts/` — frameworks, methods, technical terms
- `wiki/projects/` — active and past projects
- `wiki/people/` — contacts, collaborators
- Auto-generated backlinks, cross-references, and `index.md` summary

### Phase 3: Query & Enhance

Ask questions against the wiki. Answers get filed into `wiki/derived/` — every exploration adds to the knowledge base, nothing is lost.

### Phase 4: Lint & Maintain

Periodic scans for:
- Contradictions between articles
- Missing information (impute via web search)
- Dead links and orphan files
- New connections between concepts

After linting, the cycle returns to Phase 2. The wiki keeps growing.

---

## Vault Structure

```
your-vault/
├── raw/                    # Phase 1: ingested sources (append-only)
├── wiki/                   # Phase 2: LLM-compiled articles
│   ├── concepts/           #   frameworks, methods, terms
│   ├── projects/           #   project-specific articles
│   ├── people/             #   people profiles
│   └── derived/            #   Phase 3: query answers
├── notes/                  # User's organized working notes
│   ├── ai-tooling/
│   ├── blog-drafts/
│   ├── business/
│   ├── cymkube/
│   ├── finance/
│   ├── infra/
│   ├── openclaw/
│   ├── people-meetings/
│   ├── sowork/
│   └── assets/             #   images
├── _archive/               # Frozen legacy notes
│   ├── trash/
│   └── tiny/
├── index.md                # KB entry point (auto-maintained)
├── log.md                  # Execution history
└── .llm-kb/queue/          # Prompt bundles for Claude Code
```

## Repo Structure

```
project_Obsidian_graph/
├── plugin/                 # Obsidian plugin (TypeScript + esbuild)
│   ├── src/
│   │   ├── main.ts         # Plugin entry: commands, status bar, settings
│   │   ├── settings.ts     # Settings tab (tools path, uv cmd, language)
│   │   ├── sidebarView.ts  # Log streaming sidebar
│   │   └── runner.ts       # child_process wrapper
│   ├── manifest.json
│   ├── main.js             # Built artifact (checked in)
│   └── package.json
├── tools/                  # Python CLIs (managed with uv)
│   ├── audit/              # vault_audit.py — read-only inventory
│   ├── ingest/             # ingest.py — normalize into raw/
│   ├── compile/            # compile.py — emit compile prompts
│   ├── query/              # query.py — stub + prompt for questions
│   ├── lint/               # lint.py — integrity checks
│   ├── organize/           # reorganize.py — classify & move files
│   └── pyproject.toml
├── .claude/agents/
│   └── kb-verifier.md      # Independent verification subagent
├── tasks/                  # Execution log (checkbox-tracked)
├── CLAUDE.md               # AI assistant instructions
└── README.md               # This file
```

## Plugin Settings

| Setting | Default | Description |
|---------|---------|-------------|
| Tools path | `~/workspace/clonn/project_Obsidian_graph/tools` | Where the Python CLIs live |
| uv command | `uv` | The uv binary |
| Claude Code command | `claude` | Claude Code CLI binary |
| Language | `zh-TW` | Output language (Traditional Chinese / English) |

## The Daily Workflow

```
Morning:
  1. Read articles → Web Clipper saves to raw/
  2. Cmd+P → "LLM-KB: Compile wiki" → Claude Code builds wiki articles

Anytime:
  3. Cmd+P → "LLM-KB: Ask the wiki" → ask questions, answers saved

Weekly:
  4. Cmd+P → "LLM-KB: Lint wiki" → fix contradictions, fill gaps
  5. Review index.md → see the big picture
```

## References

- **Karpathy's system** — [GitHub Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | [Tweet](https://x.com/karpathy/status/2039805659525644595)
- **Obsidian API** — [docs.obsidian.md](https://docs.obsidian.md/Home)
- **Obsidian Web Clipper** — [obsidian.md/clipper](https://obsidian.md/clipper)
- **graphify** — [graphify.net](https://graphify.net/)
- **uv** — [docs.astral.sh/uv](https://docs.astral.sh/uv/)
- **Claude Code** — [claude.ai/code](https://claude.ai/code)

## License

MIT

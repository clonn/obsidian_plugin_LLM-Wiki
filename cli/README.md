# obsidian-llm-wiki

CLI for the Karpathy-style LLM knowledge base system. Works with any Obsidian vault.

## Install

```bash
npm install -g obsidian-llm-wiki
```

Or use without installing:

```bash
npx obsidian-llm-wiki init ~/my-vault
```

## Prerequisites

- [Node.js](https://nodejs.org/) v18+
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [Claude Code](https://claude.ai/code) — the LLM compiler brain

## Commands

```bash
# Set up everything: KB folders, Obsidian plugin, Python tools
llm-kb init ~/my-obsidian-vault

# Ingest a source into raw/
llm-kb ingest ~/Downloads/article.md

# Generate a compile prompt for Claude Code
llm-kb compile

# Ask a question (creates stub in wiki/derived/)
llm-kb query "What are the key concepts?"

# Check wiki integrity
llm-kb lint

# Read-only vault inventory
llm-kb audit

# Show KB stats
llm-kb status
```

## How it works

```
llm-kb init    → creates raw/, wiki/, notes/, index.md, installs Obsidian plugin
llm-kb ingest  → normalizes files into raw/ with frontmatter
llm-kb compile → generates a prompt for Claude Code to compile raw/ → wiki/
llm-kb query   → stubs an answer file + generates a query prompt
llm-kb lint    → checks for empty files, dangling links, duplicates
llm-kb status  → shows raw/wiki/notes counts and last activity
```

The CLI generates prompt bundles — Claude Code does the actual LLM work.

## License

MIT

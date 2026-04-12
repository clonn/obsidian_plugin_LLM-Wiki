#!/usr/bin/env node

import { parseArgs } from "node:util";
import { init } from "../lib/init.mjs";
import { compile } from "../lib/compile.mjs";
import { query } from "../lib/query.mjs";
import { lint } from "../lib/lint.mjs";
import { ingest } from "../lib/ingest.mjs";
import { audit } from "../lib/audit.mjs";
import { status } from "../lib/status.mjs";
import { search } from "../lib/search.mjs";

const HELP = `
  obsidian-llm-wiki — Karpathy-style LLM knowledge base CLI

  Usage:
    llm-kb init    [vault-path]         Set up KB structure + Obsidian plugin
    llm-kb ingest  <file> [--vault V]   Ingest a file into raw/
    llm-kb compile [--vault V]          Generate compile prompt for Claude Code
    llm-kb query   <question> [--vault V]  Ask the wiki
    llm-kb search  <query> [--vault V]  Full-text search across wiki + notes
    llm-kb lint    [--vault V]          Check wiki integrity
    llm-kb audit   [--vault V]          Read-only vault inventory
    llm-kb status  [--vault V]          Show KB stats
    llm-kb help                         Show this help

  Options:
    --vault, -v <path>   Obsidian vault path (auto-detected if omitted)

  Examples:
    npx obsidian-llm-wiki init ~/my-vault
    llm-kb ingest ~/Downloads/article.md
    llm-kb compile
    llm-kb query "What are the four phases of LLM KB?"
    llm-kb lint
`;

const commands = {
  init,
  ingest,
  compile,
  query,
  lint,
  audit,
  status,
  search,
  help: () => {
    console.log(HELP);
    process.exit(0);
  },
};

async function main() {
  const args = process.argv.slice(2);
  const cmd = args[0];

  if (!cmd || cmd === "help" || cmd === "--help" || cmd === "-h") {
    commands.help();
    return;
  }

  if (!(cmd in commands)) {
    console.error(`Unknown command: ${cmd}\n`);
    console.error(`Run "llm-kb help" for usage.`);
    process.exit(1);
  }

  // Parse --vault / -v from remaining args
  const rest = args.slice(1);
  let vault = null;
  const positional = [];

  for (let i = 0; i < rest.length; i++) {
    if (rest[i] === "--vault" || rest[i] === "-v") {
      vault = rest[++i];
    } else if (rest[i].startsWith("--vault=")) {
      vault = rest[i].split("=")[1];
    } else if (!rest[i].startsWith("-")) {
      positional.push(rest[i]);
    }
  }

  await commands[cmd]({ vault, positional });
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});

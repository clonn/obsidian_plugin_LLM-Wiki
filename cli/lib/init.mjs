import {
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
  symlinkSync,
  unlinkSync,
  lstatSync,
} from "node:fs";
import { join, resolve } from "node:path";
import { execFileSync } from "node:child_process";
import { detectVault, requireUv, findToolsDir } from "./helpers.mjs";

const KB_DIRS = [
  "raw",
  "wiki/concepts",
  "wiki/projects",
  "wiki/people",
  "wiki/derived",
  "_archive",
  "notes",
];

function makeIndex() {
  const today = new Date().toISOString().slice(0, 10);
  return `---
title: LLM Knowledge Base — Index
updated: ${today}
---

# LLM Knowledge Base

> Entry point for your Karpathy-style knowledge base.
> Run \`llm-kb compile\` after ingesting sources into \`raw/\`.

## Quick nav

- **raw/** — ingested sources (append-only)
- **wiki/** — LLM-compiled concept articles
- **notes/** — your hand-written notes
- **_archive/** — frozen legacy content

## Karpathy's four phases

1. **Ingest** — collect sources into raw/
2. **Compile** — LLM reads raw/, builds wiki articles
3. **Query** — ask questions, file answers into wiki/derived/
4. **Lint** — scan for contradictions, gaps, dead links

---

<!-- BEGIN:auto-summary -->
_No articles compiled yet. Run \`llm-kb compile\` to get started._
<!-- END:auto-summary -->
`;
}

function makeLog() {
  const today = new Date().toISOString().slice(0, 10);
  return `---
title: LLM KB — Execution Log
updated: ${today}
---

# Execution Log

## ${today} · KB initialized

- Folders created: ${KB_DIRS.join(", ")}
- Ready for ingest → compile → query → lint cycle
`;
}

export async function init({ vault: vaultArg, positional }) {
  const vaultPath = positional[0] || vaultArg;
  let vault;
  try {
    vault = detectVault(vaultPath);
  } catch {
    if (!vaultPath) throw new Error("Usage: llm-kb init <vault-path>");
    vault = resolve(vaultPath.replace(/^~/, process.env.HOME));
    mkdirSync(join(vault, ".obsidian"), { recursive: true });
    console.log(`Created new vault at ${vault}`);
  }

  console.log(`\n=== llm-kb init ===`);
  console.log(`Vault: ${vault}\n`);

  // 1. Create KB directories
  console.log("[1/4] Creating KB folders...");
  for (const dir of KB_DIRS) {
    mkdirSync(join(vault, dir), { recursive: true });
  }
  console.log("  Done");

  // 2. Create index.md + log.md if missing
  console.log("[2/4] Creating index.md and log.md...");
  const indexPath = join(vault, "index.md");
  if (!existsSync(indexPath)) {
    writeFileSync(indexPath, makeIndex(), "utf-8");
    console.log("  Created index.md");
  } else {
    console.log("  index.md already exists, skipping");
  }
  const logPath = join(vault, "log.md");
  if (!existsSync(logPath)) {
    writeFileSync(logPath, makeLog(), "utf-8");
    console.log("  Created log.md");
  } else {
    console.log("  log.md already exists, skipping");
  }

  // 3. Check uv + sync tools
  console.log("[3/4] Checking Python tools...");
  requireUv();
  try {
    const toolsDir = findToolsDir();
    execFileSync("uv", ["sync", "--quiet"], { cwd: toolsDir, stdio: "pipe" });
    console.log(`  Tools synced at ${toolsDir}`);
  } catch (e) {
    console.log(`  Warning: could not sync tools (${e.message})`);
    console.log("  You can sync manually: cd tools && uv sync");
  }

  // 4. Install plugin symlink
  console.log("[4/4] Linking Obsidian plugin...");
  try {
    const pluginSrc = resolve(findToolsDir(), "..", "plugin");
    const pluginsDir = join(vault, ".obsidian/plugins");
    const pluginDst = join(pluginsDir, "llm-kb");

    mkdirSync(pluginsDir, { recursive: true });

    // Remove existing symlink if any
    try {
      const stat = lstatSync(pluginDst);
      if (stat.isSymbolicLink()) unlinkSync(pluginDst);
    } catch { /* doesn't exist, fine */ }

    symlinkSync(pluginSrc, pluginDst);

    // Build if main.js missing
    if (!existsSync(join(pluginSrc, "main.js"))) {
      console.log("  Building plugin...");
      execFileSync("npm", ["install", "--silent"], {
        cwd: pluginSrc,
        stdio: "pipe",
      });
      execFileSync("npm", ["run", "build", "--silent"], {
        cwd: pluginSrc,
        stdio: "pipe",
      });
    }

    // Register in community-plugins.json
    const cpPath = join(vault, ".obsidian/community-plugins.json");
    let plugins = [];
    if (existsSync(cpPath)) {
      try {
        plugins = JSON.parse(readFileSync(cpPath, "utf-8"));
      } catch { /* reset */ }
    }
    if (!plugins.includes("llm-kb")) {
      plugins.push("llm-kb");
      writeFileSync(cpPath, JSON.stringify(plugins, null, 2), "utf-8");
    }
    console.log("  Plugin linked and registered");
  } catch (e) {
    console.log(`  Warning: plugin setup skipped (${e.message})`);
  }

  console.log(`
════════════════════════════════════════════
  Done! Restart Obsidian, then:

  1. Settings > Community plugins > Restricted mode OFF
  2. Enable "LLM Knowledge Base"
  3. Cmd+P > "LLM-KB" to see commands

  CLI commands:
    llm-kb ingest <file>      Add source to raw/
    llm-kb compile            Compile raw/ → wiki/
    llm-kb query "question"   Ask the wiki
    llm-kb lint               Check integrity
    llm-kb status             Show KB stats
════════════════════════════════════════════
`);
}

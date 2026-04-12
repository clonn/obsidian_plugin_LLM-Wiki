import { join } from "node:path";
import { existsSync, readFileSync } from "node:fs";
import { detectVault, countMd } from "./helpers.mjs";

export async function status({ vault, positional }) {
  const v = detectVault(vault || positional[0]);

  const raw = countMd(join(v, "raw"));
  const wiki = countMd(join(v, "wiki"));
  const notes = countMd(join(v, "notes"));
  const derived = countMd(join(v, "wiki/derived"));
  const archive = countMd(join(v, "_archive"));

  console.log(`\n  LLM-KB status — ${v}\n`);
  console.log(`  raw/          ${raw} files`);
  console.log(`  wiki/         ${wiki} articles (${derived} derived)`);
  console.log(`  notes/        ${notes} notes`);
  console.log(`  _archive/     ${archive} archived`);
  console.log();

  // Last log entry
  const logPath = join(v, "log.md");
  if (existsSync(logPath)) {
    const lines = readFileSync(logPath, "utf-8").split("\n");
    const lastEntry = lines.find((l) => l.startsWith("## "));
    if (lastEntry) {
      console.log(`  Last activity: ${lastEntry.replace("## ", "")}`);
    }
  }

  // Plugin status
  const pluginPath = join(v, ".obsidian/plugins/llm-kb/main.js");
  console.log(
    `  Plugin:       ${existsSync(pluginPath) ? "installed" : "NOT installed (run: llm-kb init)"}`
  );
  console.log();
}

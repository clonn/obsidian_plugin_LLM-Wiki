import { execFileSync, spawn } from "node:child_process";
import { existsSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { homedir } from "node:os";

/** Auto-detect vault path from common locations. */
export function detectVault(explicit) {
  if (explicit) {
    const p = resolve(explicit.replace(/^~/, homedir()));
    if (!existsSync(join(p, ".obsidian"))) {
      throw new Error(`Not an Obsidian vault (no .obsidian/): ${p}`);
    }
    return p;
  }

  const candidates = [
    join(homedir(), "Library/CloudStorage/Dropbox/caesar_obsidian"),
    join(homedir(), "Dropbox/caesar_obsidian"),
    join(homedir(), "Documents/caesar_obsidian"),
    join(homedir(), "obsidian-vault"),
  ];

  for (const c of candidates) {
    if (existsSync(join(c, ".obsidian"))) return c;
  }

  throw new Error(
    "Could not auto-detect vault. Pass --vault <path> or positional arg."
  );
}

/** Check if uv is installed. */
export function requireUv() {
  try {
    execFileSync("uv", ["--version"], { stdio: "pipe" });
  } catch {
    throw new Error(
      "uv not found. Install it:\n  curl -LsSf https://astral.sh/uv/install.sh | sh"
    );
  }
}

/** Locate the tools/ directory — checks sibling in repo, then npm package. */
export function findToolsDir() {
  // When running from the repo
  const repoTools = resolve(
    new URL(".", import.meta.url).pathname,
    "../../tools"
  );
  if (existsSync(join(repoTools, "pyproject.toml"))) return repoTools;

  // When installed globally via npm, tools/ is bundled
  const pkgTools = resolve(
    new URL(".", import.meta.url).pathname,
    "../templates/tools"
  );
  if (existsSync(join(pkgTools, "pyproject.toml"))) return pkgTools;

  throw new Error(
    "Cannot find tools/ directory. Are you in the obsidian_plugin_LLM-Wiki repo?"
  );
}

/** Run a uv python module with streaming output. Returns exit code. */
export function uvRun(toolsDir, module, args = []) {
  return new Promise((resolve, reject) => {
    const child = spawn("uv", ["run", "python", "-m", module, ...args], {
      cwd: toolsDir,
      stdio: "inherit",
      shell: false,
    });
    child.on("error", reject);
    child.on("close", (code) => resolve(code ?? 0));
  });
}

/** Count .md files in a directory recursively. */
export function countMd(dir) {
  if (!existsSync(dir)) return 0;
  let n = 0;
  const walk = (d) => {
    for (const e of readdirSync(d, { withFileTypes: true })) {
      if (e.name.startsWith(".")) continue;
      const full = join(d, e.name);
      if (e.isDirectory()) walk(full);
      else if (e.name.endsWith(".md") && e.name !== "README.md") n++;
    }
  };
  walk(dir);
  return n;
}

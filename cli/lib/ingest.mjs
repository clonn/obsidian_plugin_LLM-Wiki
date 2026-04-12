import { detectVault, requireUv, findToolsDir, uvRun } from "./helpers.mjs";

export async function ingest({ vault, positional }) {
  const file = positional[0];
  if (!file) {
    console.error("Usage: llm-kb ingest <file> [--vault <path>]");
    process.exit(1);
  }
  const v = detectVault(vault);
  requireUv();
  const tools = findToolsDir();
  const code = await uvRun(tools, "ingest.ingest", ["--vault", v, file]);
  process.exit(code);
}

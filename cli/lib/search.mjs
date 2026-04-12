import { detectVault, requireUv, findToolsDir, uvRun } from "./helpers.mjs";

export async function search({ vault, positional }) {
  const query = positional[0];
  if (!query) {
    console.error('Usage: llm-kb search "your query" [--vault <path>]');
    process.exit(1);
  }
  const v = detectVault(vault);
  requireUv();
  const tools = findToolsDir();
  const code = await uvRun(tools, "search.search", ["--vault", v, query]);
  process.exit(code);
}

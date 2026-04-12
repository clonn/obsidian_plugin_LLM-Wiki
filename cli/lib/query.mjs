import { detectVault, requireUv, findToolsDir, uvRun } from "./helpers.mjs";

export async function query({ vault, positional }) {
  const question = positional[0];
  if (!question) {
    console.error('Usage: llm-kb query "your question" [--vault <path>]');
    process.exit(1);
  }
  const v = detectVault(vault);
  requireUv();
  const tools = findToolsDir();
  const code = await uvRun(tools, "query.query", ["--vault", v, question]);
  process.exit(code);
}

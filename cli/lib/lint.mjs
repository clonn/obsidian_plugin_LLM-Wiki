import { detectVault, requireUv, findToolsDir, uvRun } from "./helpers.mjs";

export async function lint({ vault, positional }) {
  const v = detectVault(vault || positional[0]);
  requireUv();
  const tools = findToolsDir();
  const code = await uvRun(tools, "lint.lint", ["--vault", v]);
  process.exit(code);
}

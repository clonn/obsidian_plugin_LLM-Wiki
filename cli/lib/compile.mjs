import { detectVault, requireUv, findToolsDir, uvRun } from "./helpers.mjs";

export async function compile({ vault, positional }) {
  const v = detectVault(vault || positional[0]);
  requireUv();
  const tools = findToolsDir();
  const code = await uvRun(tools, "compile.compile", ["--vault", v]);
  process.exit(code);
}

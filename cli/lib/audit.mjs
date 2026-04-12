import { detectVault, requireUv, findToolsDir, uvRun } from "./helpers.mjs";

export async function audit({ vault, positional }) {
  const v = detectVault(vault || positional[0]);
  requireUv();
  const tools = findToolsDir();
  const code = await uvRun(tools, "audit.vault_audit", ["--vault", v]);
  process.exit(code);
}

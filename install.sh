#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────
# install.sh — one-command setup for llm-kb Obsidian plugin
# ─────────────────────────────────────────────────────────

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$REPO_DIR/plugin"
TOOLS_DIR="$REPO_DIR/tools"

# ── Detect vault path ──────────────────────────────────
detect_vault() {
  # Try common Obsidian vault locations
  local candidates=(
    "$HOME/Library/CloudStorage/Dropbox/caesar_obsidian"
    "$HOME/Dropbox/caesar_obsidian"
    "$HOME/Documents/caesar_obsidian"
  )
  for c in "${candidates[@]}"; do
    if [ -d "$c/.obsidian" ]; then
      echo "$c"
      return 0
    fi
  done
  return 1
}

if [ -n "${1:-}" ]; then
  VAULT="$1"
elif VAULT="$(detect_vault)"; then
  echo "Auto-detected vault: $VAULT"
else
  echo "Usage: ./install.sh <vault-path>"
  echo ""
  echo "Could not auto-detect your Obsidian vault."
  echo "Pass the path to your vault as the first argument."
  exit 1
fi

if [ ! -d "$VAULT/.obsidian" ]; then
  echo "Error: $VAULT does not look like an Obsidian vault (no .obsidian/ dir)"
  exit 1
fi

echo ""
echo "=== llm-kb installer ==="
echo "  Repo:   $REPO_DIR"
echo "  Vault:  $VAULT"
echo "  Plugin: $PLUGIN_DIR"
echo "  Tools:  $TOOLS_DIR"
echo ""

# ── Step 1: Build the plugin ──────────────────────────
echo "[1/4] Building Obsidian plugin..."
cd "$PLUGIN_DIR"
if [ ! -d node_modules ]; then
  npm install --silent
fi
npm run build --silent
echo "  ✓ main.js built ($(wc -c < main.js | tr -d ' ') bytes)"

# ── Step 2: Install Python tools ──────────────────────
echo "[2/4] Installing Python tools (uv sync)..."
cd "$TOOLS_DIR"
if ! command -v uv &>/dev/null; then
  echo "  Error: uv not found. Install it: https://docs.astral.sh/uv/"
  exit 1
fi
uv sync --quiet
echo "  ✓ Python dependencies installed"

# ── Step 3: Symlink plugin into vault ────────────────
echo "[3/4] Linking plugin into vault..."
PLUGINS_DIR="$VAULT/.obsidian/plugins"
mkdir -p "$PLUGINS_DIR"

TARGET="$PLUGINS_DIR/llm-kb"
if [ -L "$TARGET" ]; then
  rm "$TARGET"
fi
ln -sfn "$PLUGIN_DIR" "$TARGET"
echo "  ✓ $TARGET → $PLUGIN_DIR"

# ── Step 4: Register in community-plugins.json ───────
echo "[4/4] Registering plugin..."
CPJSON="$VAULT/.obsidian/community-plugins.json"
if [ ! -f "$CPJSON" ]; then
  echo '["llm-kb"]' > "$CPJSON"
  echo "  ✓ Created $CPJSON"
elif ! grep -q '"llm-kb"' "$CPJSON"; then
  # Insert "llm-kb" into the array
  python3 -c "
import json, pathlib
p = pathlib.Path('$CPJSON')
d = json.loads(p.read_text())
if 'llm-kb' not in d:
    d.append('llm-kb')
    p.write_text(json.dumps(d, indent=2))
    print('  ✓ Added llm-kb to community-plugins.json')
else:
    print('  ✓ Already registered')
"
else
  echo "  ✓ Already registered"
fi

# ── Step 5: Create KB structure if missing ───────────
echo ""
echo "Ensuring KB folders exist in vault..."
for dir in raw wiki/concepts wiki/projects wiki/people wiki/derived _archive notes; do
  mkdir -p "$VAULT/$dir"
done
echo "  ✓ raw/ wiki/ _archive/ notes/ exist"

# ── Done ─────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════"
echo "  Done! Restart Obsidian, then:"
echo ""
echo "  1. Settings → Community plugins → toggle OFF 'Restricted mode'"
echo "  2. Find 'LLM Knowledge Base' → Enable"
echo "  3. Cmd+P → type 'LLM-KB' to see commands"
echo ""
echo "  Plugin settings (optional):"
echo "    Tools path: $TOOLS_DIR"
echo "═══════════════════════════════════════════════"

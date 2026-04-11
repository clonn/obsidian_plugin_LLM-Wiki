- [ ] Audit the existing vault

## Why
Before touching anything we need a read-only audit of
`/Users/caesarchi/Dropbox/caesar_obsidian` — how many files, where they live,
size distribution, empty files, duplicates, language, orphans.

Output goes into `tools/audit/` as JSON + a human-readable markdown report so
we can refer back to it from later phases and commit it.

## Done when
- `tools/audit/vault_audit.py` runs with `uv run` and produces:
  - `tools/audit/reports/vault_inventory.json`
  - `tools/audit/reports/vault_inventory.md`
- Report lists: total files, md files, empty md files, largest files,
  file-count per top-level directory, suspicious duplicates (same title).
- Committed.

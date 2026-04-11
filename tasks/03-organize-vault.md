- [ ] Organize vault — remove empties, categorize, move into folders

## Why
103 .md files are piled at the vault root with no categories. The user wants
them triaged: delete empties, group by topic (cymkube, openclaw, AI tooling,
blog drafts, finance, people, templates...), and move each file under the
right folder.

## Done when
- Organization script in `tools/organize/reorganize.py` with `--dry-run`
  default and `--apply` flag.
- Script uses frontmatter + filename + first 200 bytes to classify.
- Dry-run report committed to `tools/organize/reports/reorg_plan.md`.
- User's vault is physically reorganized (files moved to topic folders, empty
  files removed, "Untitled"-type files triaged).
- `_archive/` receives anything ambiguous rather than being deleted.
- Before the move, the vault's git repo gets a clean commit so the move is
  reversible.

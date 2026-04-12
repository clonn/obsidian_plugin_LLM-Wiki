"""Repair corrupted inline wikilinks from the first autolink run.

The autolinker's first run created nested wikilinks like:
  [[notes/cymkube/Cymkube|cymkube]]projects/Cymkube|cymkube]]concepts/Cymkube-3D-SDK|cymkube]]

The correct output should be just the first wikilink:
  [[notes/cymkube/Cymkube|cymkube]]

This script finds and fixes all such patterns across the vault.

Usage:
    uv run python tools/repair_inline_links.py --vault ~/Dropbox/caesar_obsidian --dry-run
    uv run python tools/repair_inline_links.py --vault ~/Dropbox/caesar_obsidian --apply
"""

from __future__ import annotations

import re
from pathlib import Path

import click


# Pattern: a valid [[...]] wikilink immediately followed by more text ending
# in one or more extra `]]` — the hallmark of the nested corruption.
# We match: [[path|label]]garbage1|garbage2]]  (with optional more ]] tails)
CORRUPT_PATTERN = re.compile(
    r"\[\["           # opening [[
    r"([^\[\]]+?)"    # group 1: first link target+display (e.g. notes/cymkube/Cymkube|cymkube)
    r"\]\]"           # first ]]
    r"("              # group 2: the corrupted tail
    r"(?:[^\[\]]*?\]\])+"  # one or more chunks of (non-bracket text + ]])
    r")"
)


def _is_corrupted(match: re.Match) -> bool:
    """Verify the tail is actually corruption, not normal text followed by another link."""
    tail = match.group(2)
    # Corruption tails contain | (display text separator) without opening [[
    # and end with ]] without a matching [[
    return "|" in tail and "[[" not in tail


def repair_file(path: Path, apply: bool) -> list[str]:
    """Repair a single file. Returns list of changes made."""
    text = path.read_text(encoding="utf-8", errors="replace")
    changes: list[str] = []

    def replacer(m: re.Match) -> str:
        if not _is_corrupted(m):
            return m.group(0)
        fixed = f"[[{m.group(1)}]]"
        changes.append(f"  {m.group(0)[:80]}...  →  {fixed}")
        return fixed

    new_text = CORRUPT_PATTERN.sub(replacer, text)

    if changes and apply:
        path.write_text(new_text, encoding="utf-8")

    return changes


@click.command()
@click.option(
    "--vault",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option("--apply", is_flag=True, default=False, help="Apply fixes (default: dry-run).")
@click.option("--dry-run", is_flag=True, default=False, help="Show what would be fixed.")
def main(vault: Path, apply: bool, dry_run: bool) -> None:
    """Repair corrupted inline wikilinks from the first autolink run."""
    if dry_run:
        apply = False

    dirs = ["wiki", "notes"]
    total_fixes = 0
    total_files = 0

    for d in dirs:
        target = vault / d
        if not target.exists():
            continue
        for md in sorted(target.rglob("*.md")):
            changes = repair_file(md, apply=apply)
            if changes:
                total_files += 1
                total_fixes += len(changes)
                rel = md.relative_to(vault)
                click.echo(f"\n{'FIXED' if apply else 'WOULD FIX'}: {rel} ({len(changes)} repairs)")
                for c in changes:
                    click.echo(c)

    click.echo(f"\n{'Applied' if apply else 'Dry-run'}: {total_fixes} repairs in {total_files} files")


if __name__ == "__main__":
    main()

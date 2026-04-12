#!/usr/bin/env python3
"""
repair_headings.py

Repairs corrupted markdown headings in an Obsidian vault.

The auto-linker introduced two classes of corruption on heading lines:

  CLASS 1 — Normal wikilink:
    [[path/to/page|Display Text]]
    → Display Text

  CLASS 2 — Double-corruption (linker ran on already-linked text):
    [[path|Text]]dangling_garbage|Text2]]
    The first ]] closes the original link; "dangling_garbage|Text2]]" is the
    broken remnant of the second (failed) wrapping attempt.
    → Text  (or Text2 — they are usually identical)

Both classes may appear multiple times per heading line.

Only heading lines (lines starting with `#`) are ever modified.

Usage:
    uv run repair_headings.py [--dry-run]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

VAULT = Path("/Users/caesarchi/Library/CloudStorage/Dropbox/caesar_obsidian")
SEARCH_DIRS = [VAULT / "wiki", VAULT / "notes"]


# ---------------------------------------------------------------------------
# Core repair logic
# ---------------------------------------------------------------------------

# Phase 1: consume a full [[...]] token, optionally followed immediately by a
# dangling remnant that ends with ]].
#
# The dangling remnant looks like:  some/path|DisplayText]]
# It appears right after the closing ]] of the first token, with no space,
# bracket, or other delimiter between them.
#
# Regex structure:
#
#   \[\[          opening [[
#   ([^\[\]]+)    FULL link body — captured as group 1
#   \]\]          closing ]]
#   (             optional dangling remnant (group 2), two sub-variants:
#     variant A — WITH pipe:  garbage|DisplayText]]
#       [^\[\]\s|]*  path garbage (no spaces, brackets, or pipe)
#       \|           pipe separator
#       ([^\[\]]+)   display text — captured as group 3
#       \]\]         dangling closing ]]
#     variant B — NO pipe:    garbage]]   (just discard)
#       \S[^\[\]]*   starts immediately (non-space char), then any non-bracket chars
#       \]\]         dangling closing ]]
#       (?!\S)       must NOT be followed immediately by a non-space char (avoids
#                    greedily consuming real heading text that happens to sit next
#                    to a wikilink)
#   )?
#
# Display-text extraction:
#   - If group 2 matched (WITH-pipe dangling): return group 2
#   - Else: normal link OR no-pipe dangling — return display from group 1

_WIKILINK_RE = re.compile(
    r"\[\[([^\[\]]+)\]\]"                        # group 1: full link body
    r"(?:"
        r"[^\[\]\s|]*\|([^\[\]]+)\]\]"           # group 2: WITH-pipe dangling display
        r"|"
        r"\S[^\[\]]*\]\]"                        # NO-pipe dangling: starts non-space
    r")?"
)


def _display_from_body(body: str) -> str:
    """Extract display text from a normal wikilink body (the part between [[ and ]])."""
    if "|" in body:
        return body.rsplit("|", 1)[-1].strip()
    # No alias: use the last path segment as display text
    return body.rsplit("/", 1)[-1].strip()


def repair_line(line: str) -> tuple[str, bool]:
    """Return (repaired_line, was_changed).

    Only modifies heading lines (those starting with `#`).
    """
    stripped = line.lstrip()
    if not stripped.startswith("#"):
        return line, False
    if "[[" not in line and "]]" not in line:
        return line, False

    def replacer(m: re.Match) -> str:
        with_pipe_display = m.group(2)
        if with_pipe_display:
            # Double-corruption with pipe: keep the dangling display text
            return with_pipe_display.strip()
        # Normal wikilink OR no-pipe dangling (both resolved from group 1)
        return _display_from_body(m.group(1))

    repaired = _WIKILINK_RE.sub(replacer, line)

    # After substitution there may still be a bare dangling ]] with no matching
    # [[, e.g. when the corrupted token had NO pipe (just path]]). Strip those.
    # We do this carefully: only remove ]] that are not part of a valid [[ ]].
    repaired = re.sub(r"(?<!\[)\]\]", "", repaired)

    # Collapse double-spaces that may appear after removal, but preserve
    # the leading hashes and a single space before the title text.
    hash_end = len(repaired) - len(repaired.lstrip("#"))
    prefix = repaired[:hash_end]          # the `##` part
    rest = repaired[hash_end:].lstrip(" ")
    if rest:
        rest = re.sub(r" {2,}", " ", rest)
        repaired = prefix + " " + rest
    else:
        repaired = prefix

    # Preserve original line ending
    original_ending = ""
    for ending in ("\r\n", "\n", "\r"):
        if line.endswith(ending):
            original_ending = ending
            break
    repaired = repaired.rstrip("\r\n") + original_ending

    changed = repaired != line
    return repaired, changed


def repair_file(path: Path, dry_run: bool) -> list[tuple[int, str, str]]:
    """Repair one file.  Returns list of (lineno, original, repaired) for changed lines."""
    try:
        original_text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"  [SKIP] Cannot decode as UTF-8: {path}", file=sys.stderr)
        return []

    lines = original_text.splitlines(keepends=True)
    changes: list[tuple[int, str, str]] = []
    new_lines: list[str] = []

    for i, line in enumerate(lines, start=1):
        repaired, changed = repair_line(line)
        new_lines.append(repaired)
        if changed:
            changes.append((i, line.rstrip("\r\n"), repaired.rstrip("\r\n")))

    if changes and not dry_run:
        path.write_text("".join(new_lines), encoding="utf-8")

    return changes


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview changes without writing files (default: off)",
    )
    args = parser.parse_args()

    total_files_changed = 0
    total_lines_changed = 0

    for search_dir in SEARCH_DIRS:
        if not search_dir.exists():
            print(f"[WARN] Directory not found, skipping: {search_dir}", file=sys.stderr)
            continue

        md_files = sorted(search_dir.rglob("*.md"))
        print(f"\nScanning {len(md_files)} files in {search_dir.relative_to(VAULT)} ...")

        for md_path in md_files:
            changes = repair_file(md_path, dry_run=args.dry_run)
            if not changes:
                continue

            total_files_changed += 1
            total_lines_changed += len(changes)

            rel = md_path.relative_to(VAULT)
            verb = "Would fix" if args.dry_run else "Fixed"
            print(f"\n  {verb}: {rel}")
            for lineno, original, repaired in changes:
                print(f"    line {lineno}:")
                print(f"      BEFORE: {original}")
                print(f"      AFTER:  {repaired}")

    print()
    print("=" * 60)
    if args.dry_run:
        print("DRY RUN — no files were written.")
    print(
        f"Total: {total_lines_changed} heading line(s) repaired "
        f"across {total_files_changed} file(s)."
    )


if __name__ == "__main__":
    main()

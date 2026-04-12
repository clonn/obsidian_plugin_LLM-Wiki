"""Auto-link notes by scanning for mentions of wiki article titles.

Scans every .md file in notes/ and wiki/, finds plain-text mentions of
other article titles/aliases, and wraps them in [[...]] wikilinks.
This connects the isolated nodes in Obsidian's graph view.

Usage:
    uv run python -m link.autolink --vault ~/Dropbox/caesar_obsidian --dry-run
    uv run python -m link.autolink --vault ~/Dropbox/caesar_obsidian --apply
"""

from __future__ import annotations

import re
from pathlib import Path

import click
import frontmatter


def _build_link_index(vault: Path) -> list[dict]:
    """Build an index of all linkable targets: wiki articles + notes."""
    targets = []

    for d in [vault / "wiki", vault / "notes"]:
        if not d.exists():
            continue
        for p in sorted(d.rglob("*.md")):
            if p.name in {"README.md", ".gitkeep"}:
                continue

            rel = str(p.relative_to(vault))
            # Obsidian link format: [[path/without/.md]]
            link_target = rel.replace(".md", "")

            names = {p.stem}  # base filename

            # Extract title + aliases from frontmatter
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
                if text.startswith("---\n"):
                    post = frontmatter.loads(text)
                    title = post.get("title", "")
                    if title:
                        names.add(title)
                    aliases = post.get("aliases", [])
                    if isinstance(aliases, list):
                        for a in aliases:
                            if isinstance(a, str) and len(a) >= 2:
                                names.add(a)
            except Exception:
                pass

            # Filter out very short names (1 char) that would match too broadly
            names = {n for n in names if len(n) >= 2}

            if names:
                targets.append({
                    "path": rel,
                    "link": link_target,
                    "names": names,
                })

    return targets


def _build_skip_zones(text: str) -> list[tuple[int, int]]:
    """Build list of (start, end) zones to skip: frontmatter, headings, code blocks, existing links."""
    zones = []

    # Frontmatter (--- ... ---)
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            zones.append((0, end + 4))

    lines = text.split("\n")
    pos = 0
    in_code = False
    for line in lines:
        line_start = pos
        line_end = pos + len(line)

        # Code blocks
        if line.strip().startswith("```"):
            in_code = not in_code
            zones.append((line_start, line_end))
        elif in_code:
            zones.append((line_start, line_end))
        # Headings — never link inside headings
        elif line.lstrip().startswith("#"):
            zones.append((line_start, line_end))

        pos = line_end + 1  # +1 for \n

    # Existing [[ ]] links
    for m in re.finditer(r"\[\[[^\]]+\]\]", text):
        zones.append((m.start(), m.end()))

    return zones


def _in_skip_zone(pos: int, end: int, zones: list[tuple[int, int]]) -> bool:
    for zs, ze in zones:
        if pos >= zs and pos < ze:
            return True
        if end > zs and end <= ze:
            return True
    return False


def _find_mentions(
    text: str,
    targets: list[dict],
    own_path: str,
) -> list[tuple[str, str, int]]:
    """Find plain-text mentions of target names that aren't already linked.

    Returns list of (matched_text, link_target, position).
    Skips: frontmatter, headings, code blocks, existing wikilinks.
    """
    mentions = []
    skip_zones = _build_skip_zones(text)

    # Already linked targets — avoid double-linking
    existing_links = set(re.findall(r"\[\[([^\]|]+)", text))

    for t in targets:
        if t["path"] == own_path:
            continue  # don't self-link
        link = t["link"]

        # Skip if already linked to this target
        if link in existing_links or t["path"] in existing_links:
            continue

        for name in t["names"]:
            # Case-insensitive search, word-boundary aware
            # For CJK: no word boundaries needed
            if re.search(r"[\u4e00-\u9fff]", name):
                pattern = re.escape(name)
            else:
                pattern = r"\b" + re.escape(name) + r"\b"

            for m in re.finditer(pattern, text, re.IGNORECASE):
                pos = m.start()
                end = m.end()

                if _in_skip_zone(pos, end, skip_zones):
                    continue

                mentions.append((m.group(), link, pos))
                break  # one link per target per file is enough

    return mentions


def _apply_links(text: str, mentions: list[tuple[str, str, int]]) -> str:
    """Replace mentions with [[link|display]] wikilinks, back-to-front."""
    # Sort by position descending so replacements don't shift indices
    sorted_mentions = sorted(mentions, key=lambda x: -x[2])

    for matched, link, pos in sorted_mentions:
        display = matched
        replacement = f"[[{link}|{display}]]"
        text = text[:pos] + replacement + text[pos + len(matched):]

    return text


def _add_related_section(
    text: str,
    mentions: list[tuple[str, str, int]],
) -> str:
    """Append a '## Related' section with links if not already present."""
    if "## Related" in text or "## 相關" in text:
        return text

    links = list(dict.fromkeys(f"[[{link}]]" for _, link, _ in mentions))
    if not links:
        return text

    section = "\n\n## 相關\n\n" + "\n".join(f"- {l}" for l in links[:10]) + "\n"
    return text.rstrip() + section


@click.command()
@click.option(
    "--vault",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option("--dry-run", is_flag=True, default=True, help="Show what would change (default).")
@click.option("--apply", is_flag=True, default=False, help="Actually modify files.")
def main(vault: Path, dry_run: bool, apply: bool) -> None:
    """Auto-link notes by scanning for mentions of wiki article titles."""
    if apply:
        dry_run = False

    targets = _build_link_index(vault)
    click.echo(f"  Link index: {len(targets)} linkable targets")
    click.echo()

    total_links = 0
    files_changed = 0

    for d in [vault / "notes", vault / "wiki"]:
        if not d.exists():
            continue
        for p in sorted(d.rglob("*.md")):
            if p.name in {"README.md", ".gitkeep"}:
                continue

            rel = str(p.relative_to(vault))
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            mentions = _find_mentions(text, targets, rel)
            if not mentions:
                continue

            files_changed += 1
            total_links += len(mentions)

            click.echo(f"  {rel} — {len(mentions)} new links:")
            for matched, link, _ in mentions:
                click.echo(f"    + [[{link}|{matched}]]")

            if not dry_run:
                new_text = _apply_links(text, mentions)
                new_text = _add_related_section(new_text, mentions)
                p.write_text(new_text, encoding="utf-8")

    click.echo()
    if dry_run:
        click.echo(f"  DRY RUN: {total_links} links in {files_changed} files would be added.")
        click.echo(f"  Run with --apply to make changes.")
    else:
        click.echo(f"  Applied: {total_links} links in {files_changed} files.")


if __name__ == "__main__":
    main()

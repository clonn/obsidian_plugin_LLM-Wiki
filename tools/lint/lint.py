"""Lint the LLM knowledge base.

Checks:
  - no empty markdown files anywhere
  - every file inside `wiki/` has required frontmatter fields
  - every `[[wiki/...]]` link inside wiki/ resolves to a real file
  - no duplicate titles inside wiki/
  - every file in `raw/` appears in at least one wiki article's `sources:`

Exit code 0 if clean, 1 if any issue was found.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

import click
import frontmatter

WIKI_LINK_RE = re.compile(r"\[\[([^\]\|#]+)(?:\|[^\]]+)?\]\]")

REQUIRED_WIKI_FRONTMATTER = {"title"}


def _walk(d: Path) -> list[Path]:
    if not d.exists():
        return []
    return sorted(p for p in d.rglob("*.md"))


def _rel(p: Path, root: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


def lint(vault: Path) -> list[str]:
    issues: list[str] = []

    # Empty markdown files anywhere (except templated READMEs).
    for p in vault.rglob("*.md"):
        if any(part in {".git", ".obsidian", "_archive"} for part in p.parts):
            continue
        if p.stat().st_size == 0:
            issues.append(f"EMPTY: {_rel(p, vault)}")

    # wiki/ frontmatter + duplicate titles.
    wiki = vault / "wiki"
    wiki_files = [
        p for p in _walk(wiki)
        if p.name not in {"README.md"} and p.name != ".gitkeep"
    ]
    titles: dict[str, list[str]] = defaultdict(list)
    wiki_rel_set: set[str] = set()
    for p in wiki_files:
        rel = _rel(p, vault)
        wiki_rel_set.add(rel)
        try:
            post = frontmatter.load(p)
        except Exception as e:
            issues.append(f"FRONTMATTER_PARSE: {rel} — {e}")
            continue
        missing = REQUIRED_WIKI_FRONTMATTER - set(post.metadata.keys())
        if missing:
            issues.append(f"FRONTMATTER_MISSING: {rel} → {sorted(missing)}")
        title = str(post.metadata.get("title", "")).strip()
        if title:
            titles[title].append(rel)
    for title, paths in titles.items():
        if len(paths) > 1:
            issues.append(f"DUPLICATE_TITLE: '{title}' → {paths}")

    # Dangling [[wiki/...]] links inside wiki/.
    for p in wiki_files:
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in WIKI_LINK_RE.finditer(text):
            target = m.group(1).strip()
            if not target.startswith("wiki/"):
                continue
            norm = target if target.endswith(".md") else target + ".md"
            if norm not in wiki_rel_set:
                issues.append(
                    f"DANGLING_LINK: {_rel(p, vault)} → {target}"
                )

    # Orphan raw/ files (no wiki article references them).
    raw = vault / "raw"
    raw_files = [
        p for p in _walk(raw)
        if p.name not in {"README.md"}
    ]
    # build source-set across wiki frontmatter
    sourced: set[str] = set()
    for p in wiki_files:
        try:
            post = frontmatter.load(p)
        except Exception:
            continue
        for s in post.metadata.get("sources") or []:
            sourced.add(str(s))
    for p in raw_files:
        rel = _rel(p, vault)
        if rel not in sourced:
            issues.append(f"ORPHAN_RAW: {rel}")

    return issues


@click.command()
@click.option(
    "--vault",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--report",
    default=None,
    type=click.Path(path_type=Path),
    help="Write a markdown lint report to this path.",
)
def main(vault: Path, report: Path | None) -> None:
    """Lint the knowledge base. Exit 0 if clean."""
    issues = lint(vault)
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
        body = "# KB lint report\n\n"
        if issues:
            body += "\n".join(f"- {i}" for i in issues) + "\n"
        else:
            body += "All clean.\n"
        report.write_text(body, encoding="utf-8")

    if not issues:
        click.echo("lint: PASS (0 issues)")
        sys.exit(0)

    click.echo(f"lint: FAIL ({len(issues)} issues)")
    for i in issues[:50]:
        click.echo(f"  - {i}")
    if len(issues) > 50:
        click.echo(f"  … (+{len(issues) - 50} more)")
    sys.exit(1)


if __name__ == "__main__":
    main()

"""Lint the LLM knowledge base.

Checks (8 categories):
  EMPTY           — empty markdown files anywhere
  FRONTMATTER     — missing/invalid frontmatter in wiki/ files
  DANGLING_LINK   — broken [[wiki/...]] links inside wiki/
  DUPLICATE_TITLE — duplicate titles inside wiki/
  ORPHAN_RAW      — raw/ files not referenced in any wiki sources:
  UNLINKED_MENTION— wiki article titles mentioned as plain text but not wikilinked
  STALE           — wiki articles with updated: date older than 30 days
  INDEX_DRIFT     — wiki articles on disk but not listed in index.md

Exit code 0 if clean, 1 if any issue was found.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import click
import frontmatter

WIKI_LINK_RE = re.compile(r"\[\[([^\]\|#]+)(?:\|[^\]]+)?\]\]")

REQUIRED_WIKI_FRONTMATTER = {"title"}

ALL_CATEGORIES = [
    "EMPTY",
    "FRONTMATTER",
    "DANGLING_LINK",
    "DUPLICATE_TITLE",
    "ORPHAN_RAW",
    "UNLINKED_MENTION",
    "STALE",
    "INDEX_DRIFT",
]


def _walk(d: Path) -> list[Path]:
    if not d.exists():
        return []
    return sorted(p for p in d.rglob("*.md"))


def _rel(p: Path, root: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


def _skip_parts(p: Path) -> bool:
    return any(part in {".git", ".obsidian", "_archive", ".llm-kb"} for part in p.parts)


def _wiki_files(vault: Path) -> list[Path]:
    wiki = vault / "wiki"
    return [
        p for p in _walk(wiki)
        if p.name not in {"README.md", ".gitkeep"}
    ]


def _check_empty(vault: Path) -> list[tuple[str, str]]:
    """EMPTY — empty markdown files anywhere."""
    issues = []
    for p in vault.rglob("*.md"):
        if _skip_parts(p):
            continue
        if p.stat().st_size == 0:
            issues.append(("EMPTY", _rel(p, vault)))
    return issues


def _check_frontmatter(vault: Path, wiki_files: list[Path]) -> list[tuple[str, str]]:
    """FRONTMATTER — missing/invalid frontmatter in wiki/ files."""
    issues = []
    for p in wiki_files:
        rel = _rel(p, vault)
        try:
            post = frontmatter.load(p)
        except Exception as e:
            issues.append(("FRONTMATTER", f"{rel} — parse error: {e}"))
            continue
        missing = REQUIRED_WIKI_FRONTMATTER - set(post.metadata.keys())
        if missing:
            issues.append(("FRONTMATTER", f"{rel} → missing {sorted(missing)}"))
    return issues


def _check_dangling_link(vault: Path, wiki_files: list[Path], wiki_rel_set: set[str]) -> list[tuple[str, str]]:
    """DANGLING_LINK — broken [[wiki/...]] links inside wiki/."""
    issues = []
    for p in wiki_files:
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in WIKI_LINK_RE.finditer(text):
            target = m.group(1).strip()
            if not target.startswith("wiki/"):
                continue
            norm = target if target.endswith(".md") else target + ".md"
            if norm not in wiki_rel_set:
                issues.append(("DANGLING_LINK", f"{_rel(p, vault)} → {target}"))
    return issues


def _check_duplicate_title(vault: Path, wiki_files: list[Path]) -> list[tuple[str, str]]:
    """DUPLICATE_TITLE — duplicate titles inside wiki/."""
    issues = []
    titles: dict[str, list[str]] = defaultdict(list)
    for p in wiki_files:
        try:
            post = frontmatter.load(p)
        except Exception:
            continue
        title = str(post.metadata.get("title", "")).strip()
        if title:
            titles[title].append(_rel(p, vault))
    for title, paths in titles.items():
        if len(paths) > 1:
            issues.append(("DUPLICATE_TITLE", f"'{title}' → {paths}"))
    return issues


def _check_orphan_raw(vault: Path, wiki_files: list[Path]) -> list[tuple[str, str]]:
    """ORPHAN_RAW — raw/ files not referenced in any wiki sources:."""
    issues = []
    raw = vault / "raw"
    raw_files = [p for p in _walk(raw) if p.name not in {"README.md"}]
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
            issues.append(("ORPHAN_RAW", rel))
    return issues


def _check_unlinked_mention(vault: Path, wiki_files: list[Path]) -> list[tuple[str, str]]:
    """UNLINKED_MENTION — wiki article titles mentioned as plain text but not wikilinked."""
    issues = []

    # Collect all wiki article titles and their stems.
    title_to_rel: dict[str, str] = {}
    for p in wiki_files:
        try:
            post = frontmatter.load(p)
        except Exception:
            continue
        title = str(post.metadata.get("title", "")).strip()
        if title and len(title) >= 3:
            title_to_rel[title] = _rel(p, vault)

    if not title_to_rel:
        return issues

    # Build regex: match title NOT inside [[ ]]
    # We'll scan wiki/ and notes/ files.
    scan_dirs = [vault / "wiki", vault / "notes"]
    scan_files: list[Path] = []
    for d in scan_dirs:
        scan_files.extend(_walk(d))

    found: list[tuple[str, str, str]] = []  # (file_rel, title, article_rel)

    for p in scan_files:
        if _skip_parts(p):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        file_rel = _rel(p, vault)

        # Extract all wikilinked targets in this file to avoid false positives.
        wikilinked = set()
        for m in WIKI_LINK_RE.finditer(text):
            wikilinked.add(m.group(1).strip())

        for title, article_rel in title_to_rel.items():
            # Don't flag the file that defines the title.
            if file_rel == article_rel:
                continue
            # Check if title appears as plain text (not inside [[ ]]).
            # Simple heuristic: title appears in text but not as a wikilink target.
            if title in text:
                # Check it's not already wikilinked.
                already_linked = any(
                    title in lnk or lnk.endswith(title)
                    for lnk in wikilinked
                )
                if not already_linked:
                    found.append((file_rel, title, article_rel))

    # Limit to top 20.
    for file_rel, title, article_rel in found[:20]:
        issues.append(("UNLINKED_MENTION", f"{file_rel} mentions '{title}' (from {article_rel}) without wikilink"))

    return issues


def _check_stale(vault: Path, wiki_files: list[Path]) -> list[tuple[str, str]]:
    """STALE — wiki articles with updated: date older than 30 days."""
    issues = []
    cutoff = date.today() - timedelta(days=30)

    for p in wiki_files:
        try:
            post = frontmatter.load(p)
        except Exception:
            continue
        updated_val = post.metadata.get("updated")
        if updated_val is None:
            continue
        # Parse the date — could be a date object already or a string.
        try:
            if isinstance(updated_val, date):
                updated_date = updated_val
            else:
                updated_date = date.fromisoformat(str(updated_val).strip()[:10])
        except (ValueError, TypeError):
            continue

        if updated_date < cutoff:
            issues.append(("STALE", f"{_rel(p, vault)} (last updated: {updated_date.isoformat()})"))

    return issues


def _check_index_drift(vault: Path, wiki_files: list[Path]) -> list[tuple[str, str]]:
    """INDEX_DRIFT — wiki articles on disk but not listed in index.md."""
    issues = []
    index_path = vault / "index.md"
    if not index_path.exists():
        return issues

    try:
        index_text = index_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return issues

    for p in wiki_files:
        rel = _rel(p, vault)
        stem = p.stem
        # Check if the file is referenced in index.md by relative path or stem name.
        if rel not in index_text and stem not in index_text:
            issues.append(("INDEX_DRIFT", f"{rel} not listed in index.md"))

    return issues


def lint(vault: Path, categories: list[str] | None = None) -> list[tuple[str, str]]:
    """Run all lint checks and return a list of (category, detail) tuples."""
    active = set(categories) if categories else set(ALL_CATEGORIES)
    wf = _wiki_files(vault)
    wiki_rel_set = {_rel(p, vault) for p in wf}

    issues: list[tuple[str, str]] = []

    if "EMPTY" in active:
        issues.extend(_check_empty(vault))
    if "FRONTMATTER" in active:
        issues.extend(_check_frontmatter(vault, wf))
    if "DANGLING_LINK" in active:
        issues.extend(_check_dangling_link(vault, wf, wiki_rel_set))
    if "DUPLICATE_TITLE" in active:
        issues.extend(_check_duplicate_title(vault, wf))
    if "ORPHAN_RAW" in active:
        issues.extend(_check_orphan_raw(vault, wf))
    if "UNLINKED_MENTION" in active:
        issues.extend(_check_unlinked_mention(vault, wf))
    if "STALE" in active:
        issues.extend(_check_stale(vault, wf))
    if "INDEX_DRIFT" in active:
        issues.extend(_check_index_drift(vault, wf))

    return issues


def _format_grouped(issues: list[tuple[str, str]]) -> str:
    """Format issues grouped by category."""
    grouped: dict[str, list[str]] = defaultdict(list)
    for cat, detail in issues:
        grouped[cat].append(detail)

    cat_count = len(grouped)
    total = len(issues)
    lines = [f"lint: FAIL ({total} issues across {cat_count} categories)"]

    for cat in ALL_CATEGORIES:
        if cat not in grouped:
            continue
        items = grouped[cat]
        lines.append(f"  {cat} ({len(items)}):")
        for item in items:
            lines.append(f"    - {item}")

    return "\n".join(lines)


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
@click.option(
    "--category",
    default=None,
    type=click.Choice(ALL_CATEGORIES, case_sensitive=False),
    multiple=True,
    help="Filter to specific check categories (repeatable).",
)
@click.option(
    "--json-out",
    is_flag=True,
    default=False,
    help="Output results as JSON.",
)
def main(vault: Path, report: Path | None, category: tuple[str, ...], json_out: bool) -> None:
    """Lint the knowledge base. Exit 0 if clean."""
    cats = list(category) if category else None
    issues = lint(vault, categories=cats)

    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
        body = "# KB lint report\n\n"
        if issues:
            body += _format_grouped(issues) + "\n"
        else:
            body += "All clean.\n"
        report.write_text(body, encoding="utf-8")

    if json_out:
        grouped: dict[str, list[str]] = defaultdict(list)
        for cat, detail in issues:
            grouped[cat].append(detail)
        result = {
            "status": "PASS" if not issues else "FAIL",
            "total": len(issues),
            "categories": {cat: items for cat, items in grouped.items()},
        }
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if not issues else 1)

    if not issues:
        click.echo("lint: PASS (0 issues)")
        sys.exit(0)

    click.echo(_format_grouped(issues))
    sys.exit(1)


if __name__ == "__main__":
    main()

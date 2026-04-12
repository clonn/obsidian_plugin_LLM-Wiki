"""Knowledge base dashboard — shows what you have and what needs attention.

Outputs a structured JSON report:
  - coverage: how many raw files have been compiled into wiki articles
  - reviewed: which wiki articles have been marked as reviewed
  - orphans: raw files not yet compiled
  - stale: wiki articles whose source raw files were modified after compile
  - stats: total counts

Usage:
    uv run python -m status.dashboard --vault ~/Dropbox/caesar_obsidian
    uv run python -m status.dashboard --vault ~/Dropbox/caesar_obsidian --json
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import click
import frontmatter


def _scan_wiki(vault: Path) -> list[dict]:
    """Scan all wiki articles and extract metadata."""
    articles = []
    wiki = vault / "wiki"
    if not wiki.exists():
        return articles

    for p in sorted(wiki.rglob("*.md")):
        if p.name in {"README.md", ".gitkeep"}:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        rel = str(p.relative_to(vault))
        meta: dict = {
            "path": rel,
            "title": p.stem,
            "category": p.relative_to(wiki).parts[0] if len(p.relative_to(wiki).parts) > 1 else "root",
            "sources": [],
            "reviewed": False,
            "size": len(text),
            "backlinks": 0,
        }

        if text.startswith("---\n"):
            try:
                post = frontmatter.loads(text)
                meta["title"] = post.get("title", p.stem)
                meta["sources"] = post.get("sources", [])
                meta["reviewed"] = post.get("reviewed", False)
                bl = post.get("backlinks", [])
                meta["backlinks"] = len(bl) if isinstance(bl, list) else 0
            except Exception:
                pass

        # Count [[wiki/...]] links in body
        meta["outlinks"] = len(re.findall(r"\[\[wiki/", text))
        articles.append(meta)

    return articles


def _scan_raw(vault: Path) -> list[str]:
    """List all raw/ files."""
    raw = vault / "raw"
    if not raw.exists():
        return []
    return sorted(
        str(p.relative_to(vault))
        for p in raw.rglob("*.md")
        if p.name != "README.md"
    )


def build_dashboard(vault: Path) -> dict:
    articles = _scan_wiki(vault)
    raw_files = _scan_raw(vault)

    # Which raw files are referenced by wiki articles
    referenced_raw: set[str] = set()
    for a in articles:
        for s in a["sources"]:
            referenced_raw.add(s)

    orphan_raw = [r for r in raw_files if r not in referenced_raw]
    compiled_raw = [r for r in raw_files if r in referenced_raw]

    reviewed = [a for a in articles if a["reviewed"]]
    needs_review = [a for a in articles if not a["reviewed"]]

    # Group articles by category
    by_category: dict[str, int] = {}
    for a in articles:
        cat = a["category"]
        by_category[cat] = by_category.get(cat, 0) + 1

    coverage_pct = (len(compiled_raw) / len(raw_files) * 100) if raw_files else 0
    review_pct = (len(reviewed) / len(articles) * 100) if articles else 0

    return {
        "summary": {
            "total_raw": len(raw_files),
            "compiled_raw": len(compiled_raw),
            "orphan_raw": len(orphan_raw),
            "coverage_pct": round(coverage_pct, 1),
            "total_articles": len(articles),
            "reviewed": len(reviewed),
            "needs_review": len(needs_review),
            "review_pct": round(review_pct, 1),
        },
        "by_category": by_category,
        "orphans": orphan_raw,
        "needs_review": [
            {"path": a["path"], "title": a["title"], "sources": len(a["sources"])}
            for a in needs_review
        ],
        "reviewed_articles": [
            {"path": a["path"], "title": a["title"]}
            for a in reviewed
        ],
    }


@click.command()
@click.option(
    "--vault",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option("--json-out", "use_json", is_flag=True, default=False)
def main(vault: Path, use_json: bool) -> None:
    """Show knowledge base coverage and review status."""
    data = build_dashboard(vault)

    if use_json:
        click.echo(json.dumps(data, ensure_ascii=False))
        return

    s = data["summary"]
    click.echo()
    click.echo("  ╔══════════════════════════════════════╗")
    click.echo("  ║     LLM Knowledge Base Dashboard     ║")
    click.echo("  ╚══════════════════════════════════════╝")
    click.echo()
    click.echo(f"  📥 Raw sources:     {s['total_raw']}")
    click.echo(f"  ✅ Compiled:        {s['compiled_raw']} ({s['coverage_pct']}%)")
    click.echo(f"  ⏳ Not compiled:    {s['orphan_raw']}")
    click.echo()
    click.echo(f"  📖 Wiki articles:   {s['total_articles']}")
    click.echo(f"  ✅ Reviewed:        {s['reviewed']} ({s['review_pct']}%)")
    click.echo(f"  👁️  Needs review:   {s['needs_review']}")
    click.echo()

    click.echo("  📂 By category:")
    for cat, count in sorted(data["by_category"].items()):
        click.echo(f"     {cat}: {count}")
    click.echo()

    if data["orphans"]:
        click.echo(f"  ⏳ Orphan raw files (not yet compiled):")
        for o in data["orphans"][:10]:
            click.echo(f"     - {o}")
        if len(data["orphans"]) > 10:
            click.echo(f"     ... and {len(data['orphans']) - 10} more")
        click.echo()

    if data["needs_review"]:
        click.echo(f"  👁️  Articles needing review:")
        for a in data["needs_review"][:10]:
            click.echo(f"     - {a['title']} ({a['path']})")
        if len(data["needs_review"]) > 10:
            click.echo(f"     ... and {len(data['needs_review']) - 10} more")
    click.echo()


if __name__ == "__main__":
    main()

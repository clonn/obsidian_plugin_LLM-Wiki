"""Batch-ingest all notes/ files into raw/ for compilation.

Usage:
    uv run python -m ingest.batch_ingest --vault ~/Dropbox/caesar_obsidian --dry-run
    uv run python -m ingest.batch_ingest --vault ~/Dropbox/caesar_obsidian --apply
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import click
import frontmatter

SKIP_DIRS = {".git", ".obsidian", "_archive", ".llm-kb", "raw", "wiki"}


def _slug(title: str) -> str:
    out = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "-", title).strip("-")
    return out[:80] or "untitled"


def gather_notes(vault: Path) -> list[Path]:
    """Collect all .md files under notes/ (and loose root .md except index/log)."""
    files = []
    notes = vault / "notes"
    if notes.exists():
        for p in sorted(notes.rglob("*.md")):
            if p.name == "README.md":
                continue
            if p.stat().st_size < 50:
                continue
            files.append(p)
    return files


@click.command()
@click.option("--vault", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--apply", is_flag=True)
def main(vault: Path, apply: bool) -> None:
    """Batch-ingest notes/ into raw/."""
    raw = vault / "raw"
    notes = gather_notes(vault)
    today = date.today().isoformat()

    existing_raw = {p.name for p in raw.rglob("*.md")} if raw.exists() else set()

    to_ingest: list[tuple[Path, Path]] = []
    skipped = 0

    for src in notes:
        slug = _slug(src.stem)
        dst_name = f"{today}_{slug}.md"

        # Avoid duplicates
        if dst_name in existing_raw:
            skipped += 1
            continue

        dst = raw / dst_name
        to_ingest.append((src, dst))
        existing_raw.add(dst_name)  # prevent collisions within batch

    click.echo(f"\nBatch ingest: {len(to_ingest)} files to ingest, {skipped} already in raw/")

    if not apply:
        for src, dst in to_ingest[:10]:
            click.echo(f"  {src.relative_to(vault)} → {dst.name}")
        if len(to_ingest) > 10:
            click.echo(f"  ... (+{len(to_ingest) - 10} more)")
        click.echo("\nDRY-RUN. Re-run with --apply.")
        return

    raw.mkdir(parents=True, exist_ok=True)
    n = 0
    for src, dst in to_ingest:
        try:
            post = frontmatter.load(src)
        except Exception:
            post = frontmatter.Post(src.read_text(encoding="utf-8", errors="replace"))
        post.metadata.setdefault("title", src.stem)
        post.metadata["ingested_at"] = today
        post.metadata["source"] = f"vault:{src.relative_to(vault)}"
        dst.write_text(frontmatter.dumps(post), encoding="utf-8")
        n += 1

    click.echo(f"Ingested {n} files into raw/")


if __name__ == "__main__":
    main()

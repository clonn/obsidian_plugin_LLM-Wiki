"""Ingest a file into the vault's raw/ zone.

Usage:
    uv run ingest/ingest.py --vault ~/Dropbox/caesar_obsidian <source>

Behavior:
  - Copies <source> into `raw/YYYY-MM-DD_<slug>.md`.
  - If the source is already a markdown file, prepends a frontmatter block
    that records `source`, `ingested_at`, and original `title`.
  - If the source is a .pdf/.html/.txt, wraps it in a md stub that points
    to the original file stored next to the .md.
  - Appends a one-line entry to log.md under today's date.
"""

from __future__ import annotations

import re
import shutil
from datetime import date
from pathlib import Path

import click
import frontmatter


def _slug(title: str) -> str:
    out = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "-", title).strip("-")
    return out[:80] or "untitled"


def _append_log(vault: Path, line: str) -> None:
    log = vault / "log.md"
    if not log.exists():
        log.write_text("# Execution Log\n\n", encoding="utf-8")
    with log.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


@click.command()
@click.option(
    "--vault",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option("--source-url", default=None, help="Original URL, if known.")
@click.argument(
    "source",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def main(vault: Path, source_url: str | None, source: Path) -> None:
    """Ingest <source> into the vault's raw/ zone."""
    raw = vault / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    slug = _slug(source.stem)
    dst = raw / f"{today}_{slug}{source.suffix}"

    if source.suffix.lower() in {".md", ".markdown"}:
        try:
            post = frontmatter.load(source)
        except Exception:
            post = frontmatter.Post(source.read_text(encoding="utf-8"))
        post.metadata.setdefault("title", source.stem)
        post.metadata["ingested_at"] = today
        if source_url:
            post.metadata["source"] = source_url
        else:
            post.metadata.setdefault("source", f"local:{source.name}")
        dst.write_text(frontmatter.dumps(post), encoding="utf-8")
    else:
        # non-markdown: copy file alongside, create wrapper stub
        asset = raw / f"{today}_{slug}{source.suffix}"
        shutil.copy2(source, asset)
        stub = frontmatter.Post(
            f"![[raw/{asset.name}]]\n",
            title=source.stem,
            ingested_at=today,
            source=source_url or f"local:{source.name}",
            kind=source.suffix.lstrip(".").lower(),
        )
        dst = raw / f"{today}_{slug}.md"
        dst.write_text(frontmatter.dumps(stub), encoding="utf-8")

    _append_log(vault, f"- {today} · ingested `{dst.name}`")
    click.echo(f"ingested → {dst}")


if __name__ == "__main__":
    main()

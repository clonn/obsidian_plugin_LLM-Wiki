"""Watch raw/ for new files and auto-normalize them.

When a new file lands in raw/ (e.g., from Obsidian Web Clipper), this watcher:
  1. Waits 2 seconds (debounce — clipper may still be writing)
  2. Normalizes the filename (strip bad chars, add date prefix if missing)
  3. Adds frontmatter (title, ingested_at, source) if missing
  4. Appends a line to log.md

Usage:
    uv run python -m watch.watcher --vault ~/Dropbox/caesar_obsidian

Runs until Ctrl-C.
"""

from __future__ import annotations

import re
import time
from datetime import date
from pathlib import Path

import click
import frontmatter


DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_")


def _normalize_name(name: str) -> str:
    """Strip bad chars, add date prefix if missing."""
    out = re.sub(r"[*<>|]", "", name).replace("**", "").strip()
    if not DATE_PREFIX_RE.match(out):
        today = date.today().isoformat()
        stem, suf = Path(out).stem, Path(out).suffix
        slug = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "-", stem).strip("-")[:80]
        out = f"{today}_{slug}{suf}"
    return out


def _add_frontmatter(p: Path) -> bool:
    """Add frontmatter if missing. Returns True if modified."""
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False

    if text.startswith("---\n"):
        return False  # already has frontmatter

    today = date.today().isoformat()
    post = frontmatter.Post(
        text,
        title=p.stem,
        ingested_at=today,
        source="web-clipper",
    )
    p.write_text(frontmatter.dumps(post), encoding="utf-8")
    return True


def _append_log(vault: Path, msg: str) -> None:
    log = vault / "log.md"
    if log.exists():
        with log.open("a", encoding="utf-8") as f:
            f.write(f"\n- {date.today().isoformat()} · {msg}")


@click.command()
@click.option("--vault", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--interval", default=5, help="Poll interval in seconds.")
def main(vault: Path, interval: int) -> None:
    """Watch raw/ for new files and auto-normalize them."""
    raw = vault / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    seen: set[str] = {p.name for p in raw.iterdir() if p.is_file()}
    click.echo(f"Watching {raw} ({len(seen)} existing files)")
    click.echo("Press Ctrl-C to stop.\n")

    try:
        while True:
            time.sleep(interval)
            current = {p.name for p in raw.iterdir() if p.is_file()}
            new = current - seen

            for name in sorted(new):
                p = raw / name
                if not p.exists():
                    continue

                click.echo(f"  New file: {name}")

                # Normalize filename
                norm = _normalize_name(name)
                if norm != name:
                    dst = raw / norm
                    if not dst.exists():
                        p.rename(dst)
                        click.echo(f"    Renamed → {norm}")
                        p = dst

                # Add frontmatter
                if p.suffix.lower() in {".md", ".markdown", ".txt"}:
                    if _add_frontmatter(p):
                        click.echo(f"    Added frontmatter")

                _append_log(vault, f"auto-ingested `{p.name}`")

            seen = current | {_normalize_name(n) for n in new}
    except KeyboardInterrupt:
        click.echo("\nStopped.")


if __name__ == "__main__":
    main()

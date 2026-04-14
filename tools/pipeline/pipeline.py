"""Automated knowledge pipeline: detect new files → ingest → compile → link.

Watches multiple drop zones (Clippings/, vault root, notes/) for new .md files,
moves them into raw/ with proper frontmatter, and optionally triggers compile.

Flow:
  Clippings/ ──┐
  vault root ──┼──→ raw/ ──→ compile prompt ──→ autolink
  notes/new  ──┘

Usage:
    uv run python -m pipeline.pipeline --vault ~/Dropbox/caesar_obsidian --dry-run
    uv run python -m pipeline.pipeline --vault ~/Dropbox/caesar_obsidian --apply
    uv run python -m pipeline.pipeline --vault ~/Dropbox/caesar_obsidian --watch
"""

from __future__ import annotations

import re
import shutil
import time
from datetime import date, datetime
from pathlib import Path

import click
import frontmatter


DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_")

# Folders to scan for new content (relative to vault)
DROP_ZONES = ["Clippings"]

# Files/folders that should never be ingested
IGNORE_NAMES = {"README.md", ".gitkeep", ".DS_Store", "index.md", "log.md",
                "知識圖譜.canvas", "未命名.canvas"}
IGNORE_DIRS = {".obsidian", ".git", "_archive", ".llm-kb", "raw", "wiki", "notes",
               "_templates", "_attachments"}


def _slug(name: str) -> str:
    """Create a normalized slug from a filename."""
    stem = Path(name).stem
    slug = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "-", stem).strip("-")
    return slug[:80] or "untitled"


def _make_raw_name(name: str) -> str:
    """Ensure date prefix and clean slug."""
    if DATE_PREFIX_RE.match(name):
        return name
    today = date.today().isoformat()
    slug = _slug(name)
    return f"{today}_{slug}.md"


def _ensure_frontmatter(path: Path, source_label: str) -> str:
    """Read file, add frontmatter if missing. Returns the content to write."""
    text = path.read_text(encoding="utf-8", errors="replace")

    if text.startswith("---\n"):
        # Already has frontmatter — just ensure ingested_at is present
        try:
            post = frontmatter.loads(text)
            if "ingested_at" not in post.metadata:
                post.metadata["ingested_at"] = date.today().isoformat()
                post.metadata["source"] = source_label
                return frontmatter.dumps(post)
        except Exception:
            pass
        return text

    today = date.today().isoformat()
    post = frontmatter.Post(
        text,
        title=path.stem,
        ingested_at=today,
        source=source_label,
    )
    return frontmatter.dumps(post)


def scan_drop_zones(vault: Path) -> list[dict]:
    """Scan all drop zones and vault root for new .md files to ingest."""
    candidates = []

    # 1. Scan Clippings/ and other drop zones
    for zone in DROP_ZONES:
        zone_path = vault / zone
        if not zone_path.exists():
            continue
        for f in sorted(zone_path.rglob("*.md")):
            if f.name in IGNORE_NAMES:
                continue
            raw_name = _make_raw_name(f.name)
            candidates.append({
                "source": str(f.relative_to(vault)),
                "source_path": f,
                "raw_name": raw_name,
                "zone": zone,
                "source_label": f"clipping:{f.name}",
            })

    # 2. Scan vault root for stray .md files
    for f in sorted(vault.glob("*.md")):
        if f.name in IGNORE_NAMES:
            continue
        if f.is_dir():
            continue
        # Skip if it's index.md, log.md, or already known
        if f.name in {"index.md", "log.md"}:
            continue
        raw_name = _make_raw_name(f.name)
        candidates.append({
            "source": f.name,
            "source_path": f,
            "raw_name": raw_name,
            "zone": "root",
            "source_label": f"vault-root:{f.name}",
        })

    return candidates


def _already_ingested(vault: Path, raw_name: str) -> bool:
    """Check if a file with this name already exists in raw/."""
    return (vault / "raw" / raw_name).exists()


def ingest_file(vault: Path, candidate: dict, apply: bool) -> dict | None:
    """Ingest a single file into raw/. Returns action record or None if skipped."""
    raw_name = candidate["raw_name"]
    src = candidate["source_path"]

    if _already_ingested(vault, raw_name):
        return None

    raw_dir = vault / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / raw_name

    content = _ensure_frontmatter(src, candidate["source_label"])

    if apply:
        dest.write_text(content, encoding="utf-8")
        # Don't delete source from Clippings — keep as reference
        # But do move stray root files to avoid clutter
        if candidate["zone"] == "root":
            src.unlink()

    return {
        "source": candidate["source"],
        "raw": f"raw/{raw_name}",
        "zone": candidate["zone"],
        "action": "ingested" if apply else "would ingest",
    }


def run_pipeline(vault: Path, apply: bool) -> list[dict]:
    """Run the full pipeline scan."""
    candidates = scan_drop_zones(vault)
    actions = []

    for c in candidates:
        result = ingest_file(vault, c, apply=apply)
        if result:
            actions.append(result)

    return actions


@click.command()
@click.option("--vault", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--apply", is_flag=True, default=False, help="Apply ingestion (default: dry-run).")
@click.option("--dry-run", is_flag=True, default=False, help="Show what would be ingested.")
@click.option("--watch", is_flag=True, default=False, help="Watch continuously (poll every 30s).")
@click.option("--interval", default=30, help="Watch poll interval in seconds.")
def main(vault: Path, apply: bool, dry_run: bool, watch: bool, interval: int) -> None:
    """Automated knowledge pipeline: detect → ingest → compile → link."""
    if dry_run:
        apply = False

    if watch:
        apply = True
        click.echo(f"  Pipeline watching {vault}")
        click.echo(f"  Drop zones: {', '.join(DROP_ZONES)} + vault root")
        click.echo(f"  Poll interval: {interval}s")
        click.echo(f"  Press Ctrl-C to stop.\n")

        try:
            while True:
                actions = run_pipeline(vault, apply=True)
                if actions:
                    ts = datetime.now().strftime("%H:%M:%S")
                    click.echo(f"  [{ts}] Ingested {len(actions)} files:")
                    for a in actions:
                        click.echo(f"    {a['source']} → {a['raw']}")

                    # Append to log
                    log = vault / "log.md"
                    if log.exists():
                        with log.open("a", encoding="utf-8") as f:
                            f.write(f"\n- {date.today().isoformat()} · pipeline auto-ingest: {len(actions)} files")

                time.sleep(interval)
        except KeyboardInterrupt:
            click.echo("\n  Pipeline stopped.")
        return

    # One-shot mode
    actions = run_pipeline(vault, apply=apply)

    if not actions:
        click.echo("  Pipeline: nothing new to ingest.")
        return

    mode = "Applied" if apply else "Dry-run"
    click.echo(f"\n  {mode} pipeline: {len(actions)} files")
    for a in actions:
        click.echo(f"    [{a['zone']}] {a['source']} → {a['raw']}")

    if apply:
        # Append to log
        log = vault / "log.md"
        if log.exists():
            with log.open("a", encoding="utf-8") as f:
                f.write(f"\n- {date.today().isoformat()} · pipeline ingest: {len(actions)} files")

    click.echo(f"\n  Next steps:")
    click.echo(f"    1. Run compile: uv run python -m compile.compile --vault {vault} --incremental")
    click.echo(f"    2. Run autolink: uv run python -m link.autolink --vault {vault} --apply")
    click.echo(f"    3. Run lint: uv run python -m lint.lint --vault {vault}")


if __name__ == "__main__":
    main()

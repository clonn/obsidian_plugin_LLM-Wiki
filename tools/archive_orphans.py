"""Archive orphan raw files that were intentionally skipped during compile.

Groups them into _archive/ subcategories based on content analysis:
- sensitive: files containing API keys, credentials, passwords
- junk: empty files, stubs with no content
- cymkube-ops: Cymkube internal operations (prompts, supplier info, product notes)
- prompts: AI prompt templates and specifications
- business-ops: client research, vendor info

Usage:
    uv run python tools/archive_orphans.py --vault ~/Dropbox/caesar_obsidian --dry-run
    uv run python tools/archive_orphans.py --vault ~/Dropbox/caesar_obsidian --apply
"""

from __future__ import annotations

import shutil
from pathlib import Path

import click

# Mapping: raw filename (without date prefix) → archive subcategory
ARCHIVE_MAP: dict[str, str] = {
    # Sensitive — credentials, API keys
    "API-KEY.md": "sensitive",
    "ai-partner.md": "sensitive",
    "notebooklm-to-pdf-to-text-and-image.md": "sensitive",
    "person-keys.md": "sensitive",
    # Junk — empty or content-less stubs
    "Untitled.md": "junk",
    "test.md": "junk",
    # Cymkube operations
    "Cympack-思考流程.md": "cymkube-ops",
    "cympack-prompt.md": "cymkube-ops",
    "法務拍攝內容.md": "cymkube-ops",
    "製作過商品內容.md": "cymkube-ops",
    "路跑需求.md": "cymkube-ops",
    # AI tooling / prompts
    "Data-Engineer.md": "prompts",
    "Frontend.md": "prompts",
    "game-developer.md": "prompts",
    "podcast-產生器.md": "prompts",
    "prompt-分析.md": "prompts",
    "prompt.md": "prompts",
    # Business ops
    "何大資訊.md": "business-ops",
    # Compile-worthy (keep in raw, don't archive)
    "Vue3-Build-Debug-錯誤排除-fontech-20241108.md": "compile-worthy",
    "軟體新玩法不談功能-不看工時-只看-創造多少價值.md": "junk",
}


def _strip_date_prefix(name: str) -> str:
    """Remove 2026-04-12_ prefix from filename."""
    if name.startswith("2026-04-12_"):
        return name[len("2026-04-12_"):]
    return name


@click.command()
@click.option("--vault", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--apply", is_flag=True, default=False)
@click.option("--dry-run", is_flag=True, default=False)
def main(vault: Path, apply: bool, dry_run: bool) -> None:
    """Archive orphan raw files into categorized _archive/ subdirectories."""
    if dry_run:
        apply = False

    raw_dir = vault / "raw"
    archive_dir = vault / "_archive"
    moved = 0
    skipped = 0

    # Also handle the empty root file
    root_empty = vault / "2026-04-12.md"
    if root_empty.exists():
        dest = archive_dir / "junk" / "2026-04-12.md"
        if apply:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(root_empty), str(dest))
        click.echo(f"{'MOVE' if apply else 'WOULD MOVE'}: 2026-04-12.md → _archive/junk/")
        moved += 1

    for raw_file in sorted(raw_dir.glob("*.md")):
        base = _strip_date_prefix(raw_file.name)
        category = ARCHIVE_MAP.get(base)

        if category is None:
            continue  # Not an orphan we're tracking
        if category == "compile-worthy":
            click.echo(f"SKIP (compile-worthy): {raw_file.name}")
            skipped += 1
            continue

        dest = archive_dir / category / raw_file.name
        if apply:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(raw_file), str(dest))
        click.echo(f"{'MOVE' if apply else 'WOULD MOVE'}: raw/{raw_file.name} → _archive/{category}/")
        moved += 1

    click.echo(f"\n{'Applied' if apply else 'Dry-run'}: {moved} files archived, {skipped} skipped (compile-worthy)")


if __name__ == "__main__":
    main()

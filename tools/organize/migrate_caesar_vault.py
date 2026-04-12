"""Migrate caesar_vault/ contents into notes/<category>/.

This is a one-shot script for issue #1. It walks caesar_vault/ and classifies
each .md file into the appropriate notes/ category, then removes the empty
caesar_vault/ directory.

Usage:
    uv run python -m organize.migrate_caesar_vault --vault ~/Dropbox/caesar_obsidian --dry-run
    uv run python -m organize.migrate_caesar_vault --vault ~/Dropbox/caesar_obsidian --apply
"""

from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

import click

# Mapping: caesar_vault subdirectory → notes category
DIR_MAP = {
    "blog": "blog-drafts",
    "blog/marketing": "blog-drafts",
    "person": "people-meetings",
    "thinking": "misc",
    "codingBear": "business",
    "cympotek": "cymkube",
    "cympotek/supplierchain": "cymkube",
    "cympotek/廠商提供資訊": "cymkube",
    "cympotek/廠商提供資訊/遠景": "cymkube",
    "cympotek/財報分析表": "cymkube",
}

# Keyword rules for root-level files in caesar_vault/
KEYWORD_RULES: list[tuple[str, list[str]]] = [
    ("cymkube", ["cymkube", "cympotek", "cympack", "壓克力", "3d客製化", "3d 客製化",
                 "crystal_sticker", "顏色", "追色", "色彩管理", "為什麼顏色"]),
    ("ai-tooling", ["claude", "ai如何", "ai agent", "prompt", "llm", "ai時代",
                    "vibe coding", "ai 程式碼", "wechaty", "上下文工程",
                    "人工智慧", "ai創業", "吳恩達", "ai影片", "podcast 產生",
                    "data engineer", "frontend", "game-developer", "nodejs",
                    "nvm", "node-installation", "vue3", "build_前端"]),
    ("blog-drafts", ["threads 成長", "oracle ai", "蘋果的越南", "拓竹",
                     "vibe marketing", "行銷的未來", "pj ace",
                     "全球主流 ai", "ray-ban", "真實智慧的崛起"]),
    ("business", ["跨境製造", "ap2", "牙驛通", "軟體新玩法", "coding bear",
                  "寶寶市場", "法務", "遠景公司", "company", "會眾"]),
    ("finance", ["台灣政府", "統計資料", "關稅", "八月新局"]),
]


def _read_head(p: Path, n: int = 512) -> str:
    try:
        return p.read_bytes()[:n].decode("utf-8", errors="replace")
    except Exception:
        return ""


def _sha1(p: Path) -> str:
    try:
        return hashlib.sha1(p.read_bytes()[:8192]).hexdigest()[:12]
    except Exception:
        return ""


def classify_file(p: Path, subdir: str) -> str:
    """Classify a file from caesar_vault/ into a notes/ category."""
    # If it's in a known subdir, use the dir map
    if subdir in DIR_MAP:
        return DIR_MAP[subdir]

    # Keyword matching: filename first, then content
    name = p.name.lower()
    for cat, keywords in KEYWORD_RULES:
        for kw in keywords:
            if kw.lower() in name:
                return cat

    head = _read_head(p).lower()
    for cat, keywords in KEYWORD_RULES:
        for kw in keywords:
            if kw.lower() in head:
                return cat

    return "misc"


def _sanitize(name: str) -> str:
    out = re.sub(r"[*<>|]", "", name).replace("**", "").strip()
    return out or "untitled"


def check_duplicate(src: Path, dst_dir: Path) -> Path | None:
    """Check if a file with the same name or hash already exists in dst_dir."""
    sanitized = _sanitize(src.name)
    candidate = dst_dir / sanitized
    if not candidate.exists():
        return None

    # Same name exists — check content
    src_hash = _sha1(src)
    dst_hash = _sha1(candidate)
    if src_hash == dst_hash:
        return candidate  # true duplicate
    return None  # different content, same name


@click.command()
@click.option("--vault", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--apply", is_flag=True, help="Actually perform the moves.")
def main(vault: Path, apply: bool) -> None:
    """Migrate caesar_vault/ into notes/<category>/."""
    cv = vault / "caesar_vault"
    if not cv.exists():
        click.echo("caesar_vault/ not found. Nothing to migrate.")
        return

    moves: list[tuple[Path, Path, str]] = []
    skipped_dupes: list[tuple[Path, Path]] = []
    skipped_junk: list[Path] = []
    image_moves: list[tuple[Path, Path]] = []

    image_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp"}

    for p in sorted(cv.rglob("*")):
        if p.is_dir():
            continue
        if any(part.startswith(".") for part in p.relative_to(cv).parts):
            continue  # skip .obsidian etc

        rel = p.relative_to(cv)
        subdir = str(rel.parent) if len(rel.parts) > 1 else ""

        # Images → notes/assets/
        if p.suffix.lower() in image_exts:
            dst = vault / "notes" / "assets" / p.name
            if not dst.exists():
                image_moves.append((p, dst))
            continue

        # Non-text files → skip
        if p.suffix.lower() not in {".md", ".markdown", ".txt"}:
            if p.suffix.lower() in {".canvas"}:
                skipped_junk.append(p)
            continue

        # Junk files
        if p.name in {"Untitled.md", "test.md"} and p.stat().st_size < 100:
            skipped_junk.append(p)
            continue

        # Empty files
        if p.stat().st_size == 0:
            skipped_junk.append(p)
            continue

        cat = classify_file(p, subdir)
        dst_dir = vault / "notes" / cat
        sanitized = _sanitize(p.name)
        dst = dst_dir / sanitized

        # Check for duplicates
        existing_dupe = check_duplicate(p, dst_dir)
        if existing_dupe:
            skipped_dupes.append((p, existing_dupe))
            continue

        # Avoid overwriting if different content but same name
        if dst.exists():
            stem, suf = dst.stem, dst.suffix
            dst = dst_dir / f"{stem}__from_caesar_vault{suf}"

        moves.append((p, dst, cat))

    # Report
    click.echo(f"\n=== caesar_vault/ migration plan ===")
    click.echo(f"  Moves:          {len(moves)}")
    click.echo(f"  Image moves:    {len(image_moves)}")
    click.echo(f"  Skipped dupes:  {len(skipped_dupes)}")
    click.echo(f"  Skipped junk:   {len(skipped_junk)}")
    click.echo()

    by_cat: dict[str, list[tuple[Path, Path]]] = {}
    for src, dst, cat in moves:
        by_cat.setdefault(cat, []).append((src, dst))
    for cat in sorted(by_cat):
        click.echo(f"  notes/{cat}/ ({len(by_cat[cat])})")
        for src, dst in by_cat[cat]:
            click.echo(f"    {src.relative_to(cv)} → {dst.relative_to(vault)}")

    if skipped_dupes:
        click.echo(f"\n  Duplicate files (skipped):")
        for src, existing in skipped_dupes:
            click.echo(f"    {src.relative_to(cv)} == {existing.relative_to(vault)}")

    if skipped_junk:
        click.echo(f"\n  Junk files (skipped):")
        for p in skipped_junk:
            click.echo(f"    {p.relative_to(cv)} ({p.stat().st_size} bytes)")

    if not apply:
        click.echo(f"\nDRY-RUN. Re-run with --apply to execute.")
        return

    # Execute moves
    n = 0
    for src, dst, _ in moves:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        n += 1
    for src, dst in image_moves:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        n += 1

    # Move junk to _archive/trash/
    trash = vault / "_archive" / "trash"
    trash.mkdir(parents=True, exist_ok=True)
    for p in skipped_junk:
        if p.exists():
            shutil.move(str(p), str(trash / p.name))
            n += 1

    # Move dupes to _archive/duplicates/
    dupes_dir = vault / "_archive" / "duplicates"
    dupes_dir.mkdir(parents=True, exist_ok=True)
    for src, _ in skipped_dupes:
        if src.exists():
            shutil.move(str(src), str(dupes_dir / src.name))
            n += 1

    # Try to remove empty caesar_vault
    try:
        # Remove empty subdirs first
        for d in sorted(cv.rglob("*"), reverse=True):
            if d.is_dir():
                try:
                    d.rmdir()
                except OSError:
                    pass
        # Remove .obsidian inside caesar_vault
        obsidian_dir = cv / ".obsidian"
        if obsidian_dir.exists():
            shutil.rmtree(obsidian_dir)
        # Try to remove caesar_vault itself
        try:
            cv.rmdir()
            click.echo(f"\nRemoved empty caesar_vault/")
        except OSError:
            remaining = list(cv.rglob("*"))
            click.echo(f"\ncaesar_vault/ still has {len(remaining)} files remaining")
    except Exception as e:
        click.echo(f"\nWarning: could not fully remove caesar_vault/: {e}")

    click.echo(f"\nApplied {n} operations.")


if __name__ == "__main__":
    main()

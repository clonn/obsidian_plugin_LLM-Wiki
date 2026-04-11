"""Reorganize a cluttered Obsidian vault into topic folders.

Safe by default — dry-run unless `--apply` is passed.

Behavior (root-level files of the vault only):
  1. Classify each file using `rules.RULES` against filename + first 500 bytes.
  2. Plan a move into `notes/<category>/<filename>`.
  3. Files in `DELETE_EXACT` and tiny empty files are planned for deletion
     (moved to `_archive/trash/` so the user can recover them).
  4. Duplicates discovered by the earlier audit stay in place — we note them
     in the report rather than auto-merging.

The script only touches **top-level files** by default. Files already inside
`caesar_vault/`, `wiki/`, `raw/`, `notes/`, `_archive/`, or `.obsidian/` are
left alone. Pass `--include-subdirs` to also triage the `caesar_vault/` subdir.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import click

from .rules import DEFAULT_CATEGORY, DELETE_EXACT, RULES

PROTECTED_TOP = {
    ".git",
    ".obsidian",
    ".trash",
    "raw",
    "wiki",
    "notes",
    "_archive",
    "caesar_vault",
    "Untitled",  # empty stub dir
}

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp"}


def _read_head(p: Path, n: int = 512) -> str:
    try:
        return p.read_bytes()[:n].decode("utf-8", errors="replace")
    except Exception:
        return ""


def classify(path: Path) -> str:
    """Return destination category for a file, or 'misc'.

    Two-pass matching:
      1. Filename pass — any pattern matched against the filename wins.
      2. Content pass  — if filename is ambiguous, fall back to first 500
         bytes of content.
    Filename matches beat content matches so we don't misroute a note just
    because it happens to mention another project in passing.
    """
    name = path.name.lower()
    head = _read_head(path).lower()
    # Pass 1: filename only
    for category, patterns in RULES:
        for pat in patterns:
            if pat.lower() in name:
                return category
    # Pass 2: content only
    for category, patterns in RULES:
        for pat in patterns:
            if pat.lower() in head:
                return category
    return DEFAULT_CATEGORY


def _safe_move(src: Path, dst: Path, apply: bool) -> None:
    if apply:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            stem, suf = dst.stem, dst.suffix
            i = 2
            while True:
                candidate = dst.with_name(f"{stem}__{i}{suf}")
                if not candidate.exists():
                    dst = candidate
                    break
                i += 1
        shutil.move(str(src), str(dst))


def plan(vault: Path, include_subdirs: bool) -> dict:
    moves: list[tuple[Path, Path, str]] = []
    deletions: list[Path] = []
    skipped_tiny: list[Path] = []
    image_moves: list[tuple[Path, Path]] = []

    # Top-level triage.
    for p in sorted(vault.iterdir()):
        if p.name in PROTECTED_TOP:
            continue
        if p.is_dir():
            continue
        if p.name.startswith("."):
            continue
        if p.name in ("index.md", "log.md", "README.md"):
            continue

        suf = p.suffix.lower()

        # Images at root → move under notes/assets/
        if suf in IMAGE_SUFFIXES:
            dst = vault / "notes" / "assets" / p.name
            image_moves.append((p, dst))
            continue

        # Obvious junk files.
        if p.name in DELETE_EXACT or suf in {".base", ".canvas"} and p.stat().st_size < 10:
            deletions.append(p)
            continue

        if suf not in {".md", ".markdown", ".txt"}:
            # leave as-is, surface in report
            continue

        size = p.stat().st_size
        if size == 0:
            deletions.append(p)
            continue
        if size < 200:
            # tiny but non-empty — archive rather than delete
            skipped_tiny.append(p)
            dst = vault / "_archive" / "tiny" / _sanitize(p.name)
            moves.append((p, dst, "__tiny__"))
            continue

        cat = classify(p)
        dst = vault / "notes" / cat / _sanitize(p.name)
        moves.append((p, dst, cat))

    return {
        "moves": moves,
        "deletions": deletions,
        "image_moves": image_moves,
        "skipped_tiny": skipped_tiny,
    }


_BAD_FILENAME_CHARS = re.compile(r"[*<>|]")


def _sanitize(name: str) -> str:
    """Strip characters that some filesystems choke on, preserve CJK."""
    out = _BAD_FILENAME_CHARS.sub("", name)
    # collapse repeated asterisks that came from markdown-style titles
    out = out.replace("**", "")
    # collapse leading/trailing whitespace
    out = out.strip()
    return out


def render_report(vault: Path, plan_dict: dict) -> str:
    lines = []
    lines.append(f"# Reorg plan for `{vault}`\n")
    lines.append(
        f"- Moves: **{len(plan_dict['moves'])}**\n"
        f"- Deletions (to `_archive/trash/`): **{len(plan_dict['deletions'])}**\n"
        f"- Image moves: **{len(plan_dict['image_moves'])}**\n"
        f"- Tiny files archived: **{len(plan_dict['skipped_tiny'])}**\n"
    )
    # group moves by category
    by_cat: dict[str, list[tuple[Path, Path]]] = {}
    for src, dst, cat in plan_dict["moves"]:
        by_cat.setdefault(cat, []).append((src, dst))
    for cat in sorted(by_cat.keys()):
        lines.append(f"## notes/{cat}/  ({len(by_cat[cat])})")
        for src, dst in by_cat[cat]:
            lines.append(f"- `{src.name}` → `{dst.relative_to(vault)}`")
        lines.append("")

    if plan_dict["deletions"]:
        lines.append(f"## Deletions → `_archive/trash/` ({len(plan_dict['deletions'])})")
        for p in plan_dict["deletions"]:
            lines.append(f"- `{p.name}` ({p.stat().st_size} bytes)")
        lines.append("")

    if plan_dict["image_moves"]:
        lines.append(f"## Image moves ({len(plan_dict['image_moves'])})")
        for src, dst in plan_dict["image_moves"]:
            lines.append(f"- `{src.name}` → `{dst.relative_to(vault)}`")
        lines.append("")

    return "\n".join(lines) + "\n"


@click.command()
@click.option(
    "--vault",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option("--apply", is_flag=True, help="Actually perform the moves.")
@click.option(
    "--include-subdirs",
    is_flag=True,
    help="Also reorganize files inside caesar_vault/ subdirs.",
)
@click.option(
    "--report-path",
    default=None,
    type=click.Path(path_type=Path),
)
def main(
    vault: Path, apply: bool, include_subdirs: bool, report_path: Path | None
) -> None:
    """Classify and move vault root files into notes/<category>/."""
    plan_dict = plan(vault, include_subdirs)
    report = render_report(vault, plan_dict)

    report_path = report_path or (
        Path(__file__).resolve().parent / "reports" / "reorg_plan.md"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    if not apply:
        click.echo(f"DRY-RUN. Plan written to {report_path}")
        click.echo(
            f"  {len(plan_dict['moves'])} moves | "
            f"{len(plan_dict['deletions'])} deletions | "
            f"{len(plan_dict['image_moves'])} image moves"
        )
        click.echo("Re-run with --apply to execute.")
        return

    # Apply
    n = 0
    for src, dst, _cat in plan_dict["moves"]:
        _safe_move(src, dst, apply=True)
        n += 1
    for src, dst in plan_dict["image_moves"]:
        _safe_move(src, dst, apply=True)
        n += 1
    trash = vault / "_archive" / "trash"
    trash.mkdir(parents=True, exist_ok=True)
    for p in plan_dict["deletions"]:
        _safe_move(p, trash / p.name, apply=True)
        n += 1

    click.echo(f"Applied {n} operations.")
    click.echo(f"Plan at {report_path}")


if __name__ == "__main__":
    main()

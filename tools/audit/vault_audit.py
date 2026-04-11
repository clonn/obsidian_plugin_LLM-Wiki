"""Read-only audit of an Obsidian vault.

Produces two reports:
  - reports/vault_inventory.json   (machine readable)
  - reports/vault_inventory.md     (human readable)

Answers: how many files, where, how big, empty files, suspicious duplicates,
top-level directory breakdown, language hint.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path

import click

IGNORED_DIRS = {".git", ".obsidian", ".trash", "node_modules", ".venv"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp"}
TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".canvas", ".base"}

CJK_RE = re.compile(r"[\u4e00-\u9fff]")


@dataclass
class FileRec:
    path: str
    size: int
    ext: str
    top_dir: str
    title: str
    cjk_ratio: float = 0.0
    first_line: str = ""
    sha1_8: str = ""


@dataclass
class Audit:
    vault: str
    total_files: int = 0
    total_bytes: int = 0
    by_ext: dict[str, int] = field(default_factory=dict)
    by_top_dir: dict[str, int] = field(default_factory=dict)
    md_count: int = 0
    image_count: int = 0
    empty_md: list[str] = field(default_factory=list)
    tiny_md: list[str] = field(default_factory=list)  # <200 bytes
    largest_files: list[tuple[str, int]] = field(default_factory=list)
    suspected_duplicates_by_title: dict[str, list[str]] = field(default_factory=dict)
    suspected_duplicates_by_hash: dict[str, list[str]] = field(default_factory=dict)
    cjk_md_count: int = 0
    top_level_md_at_root: int = 0


def _should_skip(rel: Path) -> bool:
    for part in rel.parts:
        if part in IGNORED_DIRS:
            return True
    return False


def _read_head(p: Path, n: int = 4096) -> str:
    try:
        with p.open("rb") as fh:
            data = fh.read(n)
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _sha1_head(p: Path, n: int = 8192) -> str:
    try:
        with p.open("rb") as fh:
            return hashlib.sha1(fh.read(n)).hexdigest()[:12]
    except Exception:
        return ""


def scan(vault: Path) -> tuple[Audit, list[FileRec]]:
    audit = Audit(vault=str(vault))
    records: list[FileRec] = []

    for p in vault.rglob("*"):
        rel = p.relative_to(vault)
        if _should_skip(rel):
            continue
        if p.is_dir():
            continue

        ext = p.suffix.lower()
        size = p.stat().st_size
        top = rel.parts[0] if len(rel.parts) > 1 else "<root>"

        audit.total_files += 1
        audit.total_bytes += size
        audit.by_ext[ext] = audit.by_ext.get(ext, 0) + 1
        audit.by_top_dir[top] = audit.by_top_dir.get(top, 0) + 1

        if ext in IMAGE_SUFFIXES:
            audit.image_count += 1
        elif ext == ".md":
            audit.md_count += 1
            if top == "<root>":
                audit.top_level_md_at_root += 1
            if size == 0:
                audit.empty_md.append(str(rel))
            elif size < 200:
                audit.tiny_md.append(str(rel))

        rec = FileRec(
            path=str(rel),
            size=size,
            ext=ext,
            top_dir=top,
            title=p.stem,
        )

        if ext in TEXT_SUFFIXES and size > 0:
            head = _read_head(p)
            rec.first_line = head.splitlines()[0][:200] if head else ""
            cjk = CJK_RE.findall(head)
            if head:
                rec.cjk_ratio = round(len(cjk) / max(len(head), 1), 3)
                if rec.cjk_ratio > 0.15 and ext == ".md":
                    audit.cjk_md_count += 1
            rec.sha1_8 = _sha1_head(p)

        records.append(rec)

    # duplicates by title (normalized)
    by_title: dict[str, list[str]] = defaultdict(list)
    for r in records:
        if r.ext != ".md":
            continue
        key = re.sub(r"\s+", " ", r.title.strip().lower())
        by_title[key].append(r.path)
    audit.suspected_duplicates_by_title = {
        k: v for k, v in by_title.items() if len(v) > 1
    }

    # duplicates by hash prefix
    by_hash: dict[str, list[str]] = defaultdict(list)
    for r in records:
        if r.sha1_8 and r.ext == ".md":
            by_hash[r.sha1_8].append(r.path)
    audit.suspected_duplicates_by_hash = {
        k: v for k, v in by_hash.items() if len(v) > 1
    }

    # top 20 largest files
    records_by_size = sorted(records, key=lambda r: r.size, reverse=True)
    audit.largest_files = [(r.path, r.size) for r in records_by_size[:20]]

    return audit, records


def render_md(audit: Audit, records: list[FileRec]) -> str:
    lines: list[str] = []
    lines.append(f"# Vault inventory — `{audit.vault}`\n")
    lines.append(
        f"- Total files: **{audit.total_files}** "
        f"({audit.total_bytes / 1_048_576:.1f} MiB)"
    )
    lines.append(f"- Markdown files: **{audit.md_count}**")
    lines.append(f"- Images: **{audit.image_count}**")
    lines.append(
        f"- Markdown files at vault root (unorganized): "
        f"**{audit.top_level_md_at_root}**"
    )
    lines.append(f"- CJK-heavy markdown files: **{audit.cjk_md_count}**")
    lines.append("")
    lines.append("## By top-level directory")
    for top, n in sorted(audit.by_top_dir.items(), key=lambda kv: -kv[1]):
        lines.append(f"- `{top}` — {n}")
    lines.append("")
    lines.append("## By extension")
    for ext, n in sorted(audit.by_ext.items(), key=lambda kv: -kv[1]):
        lines.append(f"- `{ext or '<none>'}` — {n}")
    lines.append("")
    lines.append("## Largest files")
    for path, size in audit.largest_files:
        lines.append(f"- {size / 1024:.0f} KiB — `{path}`")
    lines.append("")
    lines.append(f"## Empty markdown files ({len(audit.empty_md)})")
    for p in audit.empty_md:
        lines.append(f"- `{p}`")
    lines.append("")
    lines.append(f"## Tiny markdown files (<200 bytes) ({len(audit.tiny_md)})")
    for p in audit.tiny_md:
        lines.append(f"- `{p}`")
    lines.append("")
    lines.append(
        f"## Suspected duplicates by title "
        f"({len(audit.suspected_duplicates_by_title)})"
    )
    for title, paths in audit.suspected_duplicates_by_title.items():
        lines.append(f"- **{title}**")
        for p in paths:
            lines.append(f"  - `{p}`")
    lines.append("")
    lines.append(
        f"## Suspected duplicates by content hash "
        f"({len(audit.suspected_duplicates_by_hash)})"
    )
    for h, paths in audit.suspected_duplicates_by_hash.items():
        lines.append(f"- `{h}`")
        for p in paths:
            lines.append(f"  - `{p}`")
    return "\n".join(lines) + "\n"


@click.command()
@click.option(
    "--vault",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Obsidian vault directory",
)
@click.option(
    "--out",
    default=None,
    type=click.Path(path_type=Path),
    help="Output directory for reports (default: tools/audit/reports)",
)
def main(vault: Path, out: Path | None) -> None:
    """Read-only audit of an Obsidian vault."""
    audit, records = scan(vault)

    out_dir = out or (Path(__file__).resolve().parent / "reports")
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "vault_inventory.json"
    md_path = out_dir / "vault_inventory.md"

    payload = {
        "audit": asdict(audit),
        "records": [asdict(r) for r in records],
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md_path.write_text(render_md(audit, records), encoding="utf-8")

    click.echo(f"wrote {json_path}")
    click.echo(f"wrote {md_path}")
    click.echo(
        f"summary: {audit.md_count} md / "
        f"{audit.top_level_md_at_root} at root / "
        f"{len(audit.empty_md)} empty / "
        f"{len(audit.suspected_duplicates_by_title)} title-dupes"
    )


if __name__ == "__main__":
    main()

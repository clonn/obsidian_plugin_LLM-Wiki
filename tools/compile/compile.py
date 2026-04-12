"""Emit a compile prompt for Claude Code to run against the vault.

This is the 'LLM compiler' from Karpathy's architecture. We don't call the
model ourselves — we generate a prompt bundle and a manifest of
(raw file → existing wiki articles) that the user / plugin hands to Claude
Code.

Usage:
    uv run compile/compile.py --vault ~/Dropbox/caesar_obsidian

Output:
    <vault>/.llm-kb/queue/compile_YYYY-MM-DDTHH-MM-SS.md

The prompt is deterministic and always references the current index.md so
Claude Code can update it in-place. The plugin then streams the result back.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import click


PROMPT_TEMPLATE = """\
# Task: compile raw/ into wiki/

You are the LLM compiler for a Karpathy-style knowledge base at:

    {vault}

## Your job

1. Read every markdown file in `raw/` (there are {n_raw} right now).
2. For each one, decide whether it belongs in an existing
   `wiki/concepts/*.md`, `wiki/projects/*.md`, or `wiki/people/*.md`
   article, or whether it needs a brand-new article.
3. For new articles, create them in the appropriate wiki subfolder with
   this frontmatter:

   ```yaml
   ---
   title: <concept>
   aliases: []
   tags: []
   created: {today}
   updated: {today}
   sources:
     - raw/<source file>
   backlinks: []
   ---
   ```

4. Add `[[wiki/...]]` backlinks between related articles wherever you spot
   a connection.
5. Update `{vault}/index.md`:
   - Keep the `## 🗺️ 快速導覽` section as-is.
   - Between `<!-- BEGIN:auto-summary -->` and `<!-- END:auto-summary -->`
     rewrite a fresh summary: bulleted list of every wiki article with a
     1-line description.
6. Append a dated entry to `{vault}/log.md` at the top describing what
   you compiled this run.

## Conventions

- All content in Traditional Chinese (zh-TW).
- Be terse. Concept articles should be < 400 Chinese characters unless the
  source material genuinely needs more.
- Don't duplicate raw content into wiki articles — summarize and link.
- Don't touch anything under `notes/`, `_archive/`, or `.obsidian/`.

## Current raw/ manifest

{manifest}

## Current wiki/ manifest

{wiki_manifest}

When you're done, reply with a one-paragraph summary of what you compiled
and what you left untouched.
"""


def _list_md(d: Path) -> list[Path]:
    if not d.exists():
        return []
    return sorted(p for p in d.rglob("*.md") if p.name != "README.md")


def _load_last_compile(vault: Path) -> dict:
    """Load last_compile.json manifest (file→mtime map)."""
    p = vault / ".llm-kb" / "last_compile.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def _save_last_compile(vault: Path, raw_files: list[Path]) -> None:
    """Save current raw file→mtime map for incremental builds."""
    manifest = {}
    for f in raw_files:
        rel = str(f.relative_to(vault))
        manifest[rel] = f.stat().st_mtime
    p = vault / ".llm-kb" / "last_compile.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _count_orphan_raw(vault: Path) -> tuple[int, int, list[str]]:
    """Count how many raw files are NOT referenced in any wiki article's sources."""
    raw = vault / "raw"
    wiki = vault / "wiki"
    raw_files = [str(p.relative_to(vault)) for p in _list_md(raw)]

    referenced: set[str] = set()
    for p in _list_md(wiki):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            for line in text.splitlines()[:20]:
                if line.strip().startswith("- raw/"):
                    referenced.add(line.strip().lstrip("- ").strip())
        except Exception:
            pass

    orphans = [r for r in raw_files if r not in referenced]
    return len(raw_files), len(orphans), orphans


@click.command()
@click.option(
    "--vault",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--out",
    default=None,
    type=click.Path(path_type=Path),
)
@click.option(
    "--incremental",
    is_flag=True,
    default=False,
    help="Only compile raw files added/modified since last compile.",
)
@click.option(
    "--status",
    "show_status",
    is_flag=True,
    default=False,
    help="Show compile status without generating a prompt.",
)
def main(vault: Path, out: Path | None, incremental: bool, show_status: bool) -> None:
    """Emit a compile prompt bundle for Claude Code."""
    raw = vault / "raw"
    wiki = vault / "wiki"
    raw_files = _list_md(raw)
    wiki_files = _list_md(wiki)

    if show_status:
        total_raw, n_orphan, orphans = _count_orphan_raw(vault)
        compiled = total_raw - n_orphan
        pct = (compiled / total_raw * 100) if total_raw else 0
        click.echo(f"\n  Compile status:")
        click.echo(f"  raw: {total_raw} files | wiki: {len(wiki_files)} articles")
        click.echo(f"  compiled: {compiled} ({pct:.0f}%) | orphan: {n_orphan}")
        if n_orphan > 0:
            click.echo(f"\n  Orphan raw files (need compile):")
            for o in orphans[:5]:
                click.echo(f"    - {o}")
            if n_orphan > 5:
                click.echo(f"    ... and {n_orphan - 5} more")
        else:
            click.echo(f"\n  All raw files are compiled!")
        click.echo()
        return

    if incremental:
        prev = _load_last_compile(vault)
        new_files = []
        for f in raw_files:
            rel = str(f.relative_to(vault))
            prev_mtime = prev.get(rel)
            if prev_mtime is None or f.stat().st_mtime > prev_mtime:
                new_files.append(f)
        if not new_files:
            click.echo("incremental: nothing new since last compile.")
            return
        click.echo(f"incremental: {len(new_files)} new/modified files (of {len(raw_files)} total)")
        raw_files = new_files

    manifest = "\n".join(f"- `raw/{p.relative_to(raw)}`" for p in raw_files) or "- (empty)"
    wiki_manifest = (
        "\n".join(f"- `wiki/{p.relative_to(wiki)}`" for p in wiki_files) or "- (empty)"
    )

    prompt = PROMPT_TEMPLATE.format(
        vault=vault,
        n_raw=len(raw_files),
        today=datetime.now().strftime("%Y-%m-%d"),
        manifest=manifest,
        wiki_manifest=wiki_manifest,
    )

    queue = out or (vault / ".llm-kb" / "queue")
    queue.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    path = queue / f"compile_{ts}.md"
    path.write_text(prompt, encoding="utf-8")

    # Save manifest for next incremental run
    _save_last_compile(vault, _list_md(vault / "raw"))

    click.echo(f"compile prompt → {path}")
    click.echo(f"  raw: {len(raw_files)} files")
    click.echo(f"  wiki: {len(wiki_files)} files")
    click.echo("hand this file to Claude Code to run the compile step.")


if __name__ == "__main__":
    main()

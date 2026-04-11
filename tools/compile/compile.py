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
def main(vault: Path, out: Path | None) -> None:
    """Emit a compile prompt bundle for Claude Code."""
    raw = vault / "raw"
    wiki = vault / "wiki"
    raw_files = _list_md(raw)
    wiki_files = _list_md(wiki)

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

    click.echo(f"compile prompt → {path}")
    click.echo(f"  raw: {len(raw_files)} files")
    click.echo(f"  wiki: {len(wiki_files)} files")
    click.echo("hand this file to Claude Code to run the compile step.")


if __name__ == "__main__":
    main()

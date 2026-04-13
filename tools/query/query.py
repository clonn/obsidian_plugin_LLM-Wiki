"""Emit a query prompt and stub answer file under wiki/derived/.

Usage:
    uv run query/query.py --vault ~/Dropbox/caesar_obsidian "<question>"
    uv run query/query.py --vault ~/Dropbox/caesar_obsidian --mode deep "<question>"

Modes:
  quick    — uses hot.md + index.md only (fast, recent context)
  standard — picks 3-5 most relevant wiki articles via keyword matching
  deep     — includes ALL wiki articles for comprehensive synthesis

The question goes into `wiki/derived/YYYY-MM-DD_<slug>.md` with empty
`## 答案` section and a `## 來源` section that the LLM should populate with
backlinks to wiki articles it consulted. A companion prompt is written to
`.llm-kb/queue/` for Claude Code.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date
from pathlib import Path

import click
import frontmatter

# ---------------------------------------------------------------------------
# Prompt templates per mode
# ---------------------------------------------------------------------------

PROMPT_QUICK = """\
# Task: answer a question from the wiki (quick mode)

Vault: {vault}

## Question

{question}

## Context scope — QUICK

You have access to recent context only. Read these two files:
- `{vault}/wiki/hot.md` — recent activity / hot cache
- `{vault}/index.md` — the wiki section for article listing

Synthesize an answer from this limited context. If you cannot answer
confidently, say so and recommend switching to standard or deep mode.

## Output

1. Write the answer into `{stub_rel}`:
   - under `## 答案` write the synthesized answer in Traditional Chinese
   - under `## 來源` list every wiki article you consulted as `[[...]]`
2. Append a dated bullet to `{vault}/log.md` noting the question.

Be terse. If info is insufficient, say so explicitly.
"""

PROMPT_STANDARD = """\
# Task: answer a question from the wiki (standard mode)

Vault: {vault}

## Question

{question}

## Context scope — STANDARD

Read `{vault}/index.md` to orient yourself, then read these relevant articles:
{article_list}

Synthesize an answer from these articles. If they are insufficient, read
additional articles from index.md as needed.

## Output

1. Write the answer into `{stub_rel}`:
   - under `## 答案` write the synthesized answer in Traditional Chinese
   - under `## 來源` list every wiki article you consulted as `[[...]]`
     backlinks.
2. Update each consulted wiki article's `backlinks:` frontmatter to include
   `{stub_rel}` so the cross-link is bidirectional.
3. Append a dated bullet to `{vault}/log.md` noting the question.

Be terse. If you don't have enough info in wiki/, say so explicitly and
suggest which raw/ files would need to be compiled first.
"""

PROMPT_DEEP = """\
# Task: answer a question from the wiki (deep mode)

Vault: {vault}

## Question

{question}

## Context scope — DEEP

Read the entire wiki. All article paths:
{article_list}

Also read `{vault}/index.md` for the full map.

You may also search the web if the wiki alone is insufficient to answer the
question comprehensively. Synthesize from all available sources.

## Output

1. Write the answer into `{stub_rel}`:
   - under `## 答案` write the synthesized answer in Traditional Chinese
   - under `## 來源` list every wiki article you consulted as `[[...]]`
     backlinks.
2. Update each consulted wiki article's `backlinks:` frontmatter to include
   `{stub_rel}` so the cross-link is bidirectional.
3. Append a dated bullet to `{vault}/log.md` noting the question.

Be thorough. Cross-reference multiple articles. If you don't have enough
info in wiki/, say so explicitly and suggest which raw/ files would need to
be compiled first.
"""


def _slug(s: str) -> str:
    out = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "-", s).strip("-")
    return out[:60] or "question"


def _walk_wiki(vault: Path) -> list[Path]:
    """Return all .md files under wiki/, excluding README and gitkeep."""
    wiki = vault / "wiki"
    if not wiki.exists():
        return []
    return sorted(
        p for p in wiki.rglob("*.md")
        if p.name not in {"README.md", ".gitkeep"}
    )


def _parse_index_entries(vault: Path) -> list[tuple[str, str, str]]:
    """Parse index.md and extract (title, description, rel_path) tuples.

    Looks for lines like:
      - [[wiki/concepts/Foo]] — some description
      - [[wiki/concepts/Foo.md]] — some description
      - [[wiki/concepts/Foo|Foo Title]] — description
    """
    index_path = vault / "index.md"
    if not index_path.exists():
        return []

    entries = []
    text = index_path.read_text(encoding="utf-8", errors="replace")

    link_re = re.compile(
        r"\[\[([^\]\|#]+?)(?:\|([^\]]+))?\]\]"
        r"(?:\s*[—–\-:]\s*(.+))?"
    )
    for m in link_re.finditer(text):
        path_part = m.group(1).strip()
        display = m.group(2) or ""
        desc = m.group(3) or ""
        title = display.strip() if display.strip() else Path(path_part).stem
        entries.append((title, desc.strip(), path_part))

    return entries


def _tokenize(s: str) -> list[str]:
    """Split string into lowercase tokens for keyword matching."""
    return [t.lower() for t in re.findall(r"[\w\u4e00-\u9fff]+", s) if len(t) >= 2]


def _rank_articles(question: str, vault: Path, top_n: int = 5) -> list[str]:
    """Return up to top_n most relevant article relative paths by keyword score."""
    entries = _parse_index_entries(vault)
    if not entries:
        # Fallback: just return first N wiki files.
        wiki_files = _walk_wiki(vault)
        return [str(p.relative_to(vault)) for p in wiki_files[:top_n]]

    q_tokens = _tokenize(question)
    if not q_tokens:
        return [e[2] for e in entries[:top_n]]

    q_counts = Counter(q_tokens)
    scored: list[tuple[float, str]] = []

    for title, desc, rel_path in entries:
        entry_text = f"{title} {desc} {rel_path}"
        entry_tokens = _tokenize(entry_text)
        if not entry_tokens:
            continue
        # Score: sum of overlapping token counts.
        score = sum(q_counts[t] for t in entry_tokens if t in q_counts)
        scored.append((score, rel_path))

    # Sort by score descending, take top_n.
    scored.sort(key=lambda x: -x[0])
    # Always include at least a few even if score is 0.
    results = [rel for _score, rel in scored[:top_n]]

    # If we have fewer than 3 results, pad with top entries.
    if len(results) < 3:
        for title, desc, rel_path in entries:
            if rel_path not in results:
                results.append(rel_path)
            if len(results) >= 3:
                break

    return results[:top_n]


def _format_article_list(paths: list[str], vault: Path) -> str:
    """Format article paths as a bullet list for the prompt."""
    lines = []
    for p in paths:
        lines.append(f"- `{vault}/{p}`")
    return "\n".join(lines)


@click.command()
@click.option(
    "--vault",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--mode",
    type=click.Choice(["quick", "standard", "deep"], case_sensitive=False),
    default="standard",
    help="Query mode: quick (hot cache only), standard (top articles), deep (full vault).",
)
@click.argument("question", type=str)
def main(vault: Path, mode: str, question: str) -> None:
    """Create a stub answer and emit a query prompt."""
    today = date.today().isoformat()
    slug = _slug(question)

    # Create stub file.
    derived = vault / "wiki" / "derived"
    derived.mkdir(parents=True, exist_ok=True)
    stub = derived / f"{today}_{slug}.md"

    post = frontmatter.Post(
        f"## 問題\n\n{question}\n\n## 答案\n\n_待 Claude Code 填寫。_\n\n## 來源\n",
        title=question[:80],
        kind="query-answer",
        asked_at=today,
        mode=mode,
    )
    stub.write_text(frontmatter.dumps(post), encoding="utf-8")

    stub_rel = str(stub.relative_to(vault))

    # Build prompt based on mode.
    if mode == "quick":
        prompt = PROMPT_QUICK.format(
            vault=vault,
            question=question,
            stub_rel=stub_rel,
        )
    elif mode == "standard":
        article_paths = _rank_articles(question, vault, top_n=5)
        article_list = _format_article_list(article_paths, vault)
        prompt = PROMPT_STANDARD.format(
            vault=vault,
            question=question,
            stub_rel=stub_rel,
            article_list=article_list,
        )
    elif mode == "deep":
        wiki_files = _walk_wiki(vault)
        all_paths = [str(p.relative_to(vault)) for p in wiki_files]
        article_list = _format_article_list(all_paths, vault)
        prompt = PROMPT_DEEP.format(
            vault=vault,
            question=question,
            stub_rel=stub_rel,
            article_list=article_list,
        )
    else:
        raise click.UsageError(f"Unknown mode: {mode}")

    # Write prompt to queue.
    queue = vault / ".llm-kb" / "queue"
    queue.mkdir(parents=True, exist_ok=True)
    prompt_path = queue / f"query_{mode}_{today}_{slug}.md"
    prompt_path.write_text(prompt, encoding="utf-8")

    click.echo(f"mode   → {mode}")
    click.echo(f"stub   → {stub}")
    click.echo(f"prompt → {prompt_path}")


if __name__ == "__main__":
    main()

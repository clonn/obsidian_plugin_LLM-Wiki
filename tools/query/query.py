"""Emit a query prompt and stub answer file under wiki/derived/.

Usage:
    uv run query/query.py --vault ~/Dropbox/caesar_obsidian "<question>"

The question goes into `wiki/derived/YYYY-MM-DD_<slug>.md` with empty
`## 答案` section and a `## 來源` section that the LLM should populate with
backlinks to wiki articles it consulted. A companion prompt is written to
`.llm-kb/queue/` for Claude Code.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import click
import frontmatter


QUERY_PROMPT = """\
# Task: answer a question from the wiki

Vault: {vault}

## Question

{question}

## Your job

1. Read `{vault}/index.md` to get the wiki map.
2. Walk through relevant `wiki/` articles and synthesize an answer.
3. Write the answer into `{stub_rel}`:
   - under `## 答案` write the synthesized answer in Traditional Chinese
   - under `## 來源` list every wiki article you consulted as `[[...]]`
     backlinks.
4. Update each consulted wiki article's `backlinks:` frontmatter to include
   `{stub_rel}` so the cross-link is bidirectional.
5. Append a dated bullet to `{vault}/log.md` noting the question.

Be terse. If you don't have enough info in wiki/, say so explicitly and
suggest which raw/ files would need to be compiled first.
"""


def _slug(s: str) -> str:
    out = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "-", s).strip("-")
    return out[:60] or "question"


@click.command()
@click.option(
    "--vault",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.argument("question", type=str)
def main(vault: Path, question: str) -> None:
    """Create a stub answer and emit a query prompt."""
    today = date.today().isoformat()
    slug = _slug(question)

    derived = vault / "wiki" / "derived"
    derived.mkdir(parents=True, exist_ok=True)
    stub = derived / f"{today}_{slug}.md"

    post = frontmatter.Post(
        f"## 問題\n\n{question}\n\n## 答案\n\n_待 Claude Code 填寫。_\n\n## 來源\n",
        title=question[:80],
        kind="query-answer",
        asked_at=today,
    )
    stub.write_text(frontmatter.dumps(post), encoding="utf-8")

    prompt = QUERY_PROMPT.format(
        vault=vault,
        question=question,
        stub_rel=str(stub.relative_to(vault)),
    )

    queue = vault / ".llm-kb" / "queue"
    queue.mkdir(parents=True, exist_ok=True)
    prompt_path = queue / f"query_{today}_{slug}.md"
    prompt_path.write_text(prompt, encoding="utf-8")

    click.echo(f"stub  → {stub}")
    click.echo(f"prompt → {prompt_path}")


if __name__ == "__main__":
    main()

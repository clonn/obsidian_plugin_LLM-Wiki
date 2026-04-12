"""Naive full-text search over the wiki.

Uses TF-IDF-style scoring: term frequency in the document weighted by inverse
document frequency across the wiki. CJK characters are treated as individual
tokens (unigram) for simplicity — good enough for a personal KB.

Usage:
    uv run python -m search.search --vault ~/Dropbox/caesar_obsidian "query"
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import click

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
WORD_RE = re.compile(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    """Split text into lowered tokens. CJK chars become unigrams."""
    return [m.group().lower() for m in WORD_RE.finditer(text)]


def load_docs(vault: Path) -> list[tuple[Path, str, list[str]]]:
    """Load all wiki + notes .md files. Returns (path, raw_text, tokens)."""
    docs = []
    for d in [vault / "wiki", vault / "notes"]:
        if not d.exists():
            continue
        for p in sorted(d.rglob("*.md")):
            if p.name in {"README.md", ".gitkeep"}:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            tokens = tokenize(text)
            if tokens:
                docs.append((p, text, tokens))
    return docs


def search(query: str, docs: list[tuple[Path, str, list[str]]], top_k: int = 10):
    """Return top_k (path, score, context_lines) matches."""
    q_tokens = tokenize(query)
    if not q_tokens:
        return []

    n = len(docs)
    # Document frequency for each token
    df: Counter[str] = Counter()
    for _, _, tokens in docs:
        seen = set(tokens)
        for t in seen:
            df[t] += 1

    results = []
    for path, text, tokens in docs:
        tf = Counter(tokens)
        doc_len = len(tokens)
        score = 0.0
        for qt in q_tokens:
            if qt not in tf:
                continue
            # TF-IDF: (tf / doc_len) * log(N / df)
            idf = math.log((n + 1) / (df.get(qt, 0) + 1))
            score += (tf[qt] / max(doc_len, 1)) * idf

        if score > 0:
            # Extract context: first line containing any query token
            lines = text.splitlines()
            ctx = ""
            ql = set(q_tokens)
            for line in lines:
                ltokens = set(tokenize(line))
                if ltokens & ql:
                    ctx = line.strip()[:200]
                    break
            if not ctx and lines:
                ctx = lines[0].strip()[:200]
            results.append((path, score, ctx))

    results.sort(key=lambda r: -r[1])
    return results[:top_k]


def _extract_title(text: str) -> str:
    """Extract title from frontmatter or first heading."""
    for line in text.splitlines()[:15]:
        if line.startswith("title:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
        if line.startswith("# "):
            return line[2:].strip()
    return ""


@click.command()
@click.option(
    "--vault",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option("--top", default=10, help="Number of results to show.")
@click.option("--json-out", "use_json", is_flag=True, default=False, help="Output as JSON.")
@click.argument("query", type=str)
def main(vault: Path, top: int, use_json: bool, query: str) -> None:
    """Search the wiki and notes for a query."""
    docs = load_docs(vault)
    if not docs:
        if use_json:
            click.echo("[]")
        else:
            click.echo("No documents found in wiki/ or notes/.")
        sys.exit(1)

    results = search(query, docs, top_k=top)

    if use_json:
        out = []
        for path, score, ctx in results:
            rel = str(path.relative_to(vault))
            text = path.read_text(encoding="utf-8", errors="replace")
            out.append({
                "path": rel,
                "score": round(score, 4),
                "title": _extract_title(text),
                "context": ctx,
            })
        click.echo(json.dumps(out, ensure_ascii=False))
        return

    if not results:
        click.echo(f"No results for: {query}")
        sys.exit(0)

    click.echo(f"\n  Search results for: {query}\n")
    for i, (path, score, ctx) in enumerate(results, 1):
        rel = path.relative_to(vault)
        click.echo(f"  {i}. [{score:.4f}] {rel}")
        if ctx:
            click.echo(f"     {ctx}")
        click.echo()


if __name__ == "__main__":
    main()

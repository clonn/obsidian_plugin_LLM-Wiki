"""Export the wiki's link graph as JSON for visualization.

Produces a graph with:
  - nodes: every .md file in wiki/ and notes/
  - edges: every [[...]] link between files

Output: <vault>/.llm-kb/graph.json (consumable by graphify, D3, Obsidian graph API)

Usage:
    uv run python -m graph.export_graph --vault ~/Dropbox/caesar_obsidian
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import click

LINK_RE = re.compile(r"\[\[([^\]\|#]+)(?:\|[^\]]+)?\]\]")


def _resolve_link(target: str, vault: Path) -> str | None:
    """Try to resolve a [[...]] target to a real file path."""
    # Direct path
    norm = target if target.endswith(".md") else target + ".md"
    if (vault / norm).exists():
        return norm
    # Search by basename
    basename = Path(target).stem
    for d in [vault / "wiki", vault / "notes"]:
        if not d.exists():
            continue
        for p in d.rglob("*.md"):
            if p.stem == basename:
                return str(p.relative_to(vault))
    return None


def build_graph(vault: Path) -> dict:
    nodes = []
    edges = []
    node_ids = set()

    for d in [vault / "wiki", vault / "notes"]:
        if not d.exists():
            continue
        for p in sorted(d.rglob("*.md")):
            if p.name in {"README.md", ".gitkeep"}:
                continue
            rel = str(p.relative_to(vault))
            node_ids.add(rel)

            # Determine group from path
            parts = p.relative_to(vault).parts
            group = parts[1] if len(parts) > 2 else parts[0]

            size = p.stat().st_size
            nodes.append({
                "id": rel,
                "label": p.stem,
                "group": group,
                "size": size,
            })

            # Extract links
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            for m in LINK_RE.finditer(text):
                target = m.group(1).strip()
                resolved = _resolve_link(target, vault)
                if resolved and resolved != rel:
                    edges.append({
                        "source": rel,
                        "target": resolved,
                    })

    # Filter edges to only include known nodes
    edges = [e for e in edges if e["source"] in node_ids and e["target"] in node_ids]

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "groups": list(set(n["group"] for n in nodes)),
        },
    }


@click.command()
@click.option("--vault", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--out", default=None, type=click.Path(path_type=Path))
def main(vault: Path, out: Path | None) -> None:
    """Export the wiki's link graph as JSON."""
    graph = build_graph(vault)

    out_path = out or (vault / ".llm-kb" / "graph.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    click.echo(f"graph → {out_path}")
    click.echo(f"  {graph['stats']['total_nodes']} nodes, {graph['stats']['total_edges']} edges")
    click.echo(f"  groups: {', '.join(graph['stats']['groups'])}")


if __name__ == "__main__":
    main()

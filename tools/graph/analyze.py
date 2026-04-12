"""Deep graph analysis for the knowledge base.

Computes: cluster detection, hub/bridge nodes, isolated nodes,
weak connections, and structural improvement suggestions.

Also generates an Obsidian .canvas file for visual knowledge mapping.

Usage:
    uv run python -m graph.analyze --vault ~/Dropbox/caesar_obsidian
    uv run python -m graph.analyze --vault ~/Dropbox/caesar_obsidian --canvas
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

import click

from graph.export_graph import build_graph


def _build_adjacency(graph: dict) -> dict[str, set[str]]:
    """Build undirected adjacency list from graph edges."""
    adj: dict[str, set[str]] = defaultdict(set)
    for e in graph["edges"]:
        adj[e["source"]].add(e["target"])
        adj[e["target"]].add(e["source"])
    return adj


def _degree_stats(adj: dict[str, set[str]], nodes: list[dict]) -> list[dict]:
    """Compute degree for each node, sorted descending."""
    result = []
    for n in nodes:
        nid = n["id"]
        deg = len(adj.get(nid, set()))
        result.append({"id": nid, "label": n["label"], "group": n["group"], "degree": deg})
    result.sort(key=lambda x: x["degree"], reverse=True)
    return result


def _find_components(adj: dict[str, set[str]], all_ids: set[str]) -> list[set[str]]:
    """Find connected components via BFS."""
    visited: set[str] = set()
    components: list[set[str]] = []
    for nid in all_ids:
        if nid in visited:
            continue
        comp: set[str] = set()
        queue = [nid]
        while queue:
            cur = queue.pop()
            if cur in visited:
                continue
            visited.add(cur)
            comp.add(cur)
            for nb in adj.get(cur, set()):
                if nb not in visited and nb in all_ids:
                    queue.append(nb)
        components.append(comp)
    components.sort(key=len, reverse=True)
    return components


def _find_bridges(adj: dict[str, set[str]], all_ids: set[str]) -> list[dict]:
    """Find bridge nodes — removing them disconnects the graph.
    Uses simplified betweenness: nodes with high degree connecting different groups."""
    node_groups: dict[str, set[str]] = {}
    for nid in all_ids:
        groups = set()
        for nb in adj.get(nid, set()):
            # Extract group from path
            parts = Path(nb).parts
            g = parts[1] if len(parts) > 2 else parts[0]
            groups.add(g)
        node_groups[nid] = groups

    bridges = []
    for nid in all_ids:
        groups = node_groups[nid]
        if len(groups) >= 3:  # Connects 3+ different groups
            parts = Path(nid).parts
            own_group = parts[1] if len(parts) > 2 else parts[0]
            bridges.append({
                "id": nid,
                "label": Path(nid).stem,
                "group": own_group,
                "connects_groups": sorted(groups),
                "degree": len(adj.get(nid, set())),
            })
    bridges.sort(key=lambda x: len(x["connects_groups"]), reverse=True)
    return bridges


def _group_density(adj: dict[str, set[str]], nodes: list[dict]) -> list[dict]:
    """Compute intra-group and inter-group edge density for each group."""
    groups: dict[str, list[str]] = defaultdict(list)
    node_group: dict[str, str] = {}
    for n in nodes:
        groups[n["group"]].append(n["id"])
        node_group[n["id"]] = n["group"]

    result = []
    for g, members in sorted(groups.items()):
        member_set = set(members)
        intra = 0
        inter = 0
        for m in members:
            for nb in adj.get(m, set()):
                if nb in member_set:
                    intra += 1
                else:
                    inter += 1
        intra //= 2  # undirected
        n = len(members)
        max_intra = n * (n - 1) // 2 if n > 1 else 1
        density = intra / max_intra if max_intra > 0 else 0
        result.append({
            "group": g,
            "nodes": n,
            "intra_edges": intra,
            "inter_edges": inter,
            "density": round(density, 3),
        })
    result.sort(key=lambda x: x["nodes"], reverse=True)
    return result


def _suggest_links(adj: dict[str, set[str]], nodes: list[dict]) -> list[dict]:
    """Suggest new links between nodes that share neighbors but aren't connected."""
    node_map = {n["id"]: n for n in nodes}
    suggestions = []
    seen = set()

    # Focus on wiki articles — they're the structured knowledge
    wiki_nodes = [n for n in nodes if n["id"].startswith("wiki/")]

    for n in wiki_nodes:
        nid = n["id"]
        neighbors = adj.get(nid, set())
        # Find friends-of-friends not yet connected
        for nb in neighbors:
            for fof in adj.get(nb, set()):
                if fof == nid or fof in neighbors:
                    continue
                if not fof.startswith("wiki/"):
                    continue
                pair = tuple(sorted([nid, fof]))
                if pair in seen:
                    continue
                seen.add(pair)
                # Count shared neighbors
                shared = neighbors & adj.get(fof, set())
                if len(shared) >= 2:
                    suggestions.append({
                        "source": nid,
                        "target": fof,
                        "source_label": Path(nid).stem,
                        "target_label": Path(fof).stem,
                        "shared_neighbors": len(shared),
                        "shared_via": [Path(s).stem for s in sorted(shared)][:5],
                    })

    suggestions.sort(key=lambda x: x["shared_neighbors"], reverse=True)
    return suggestions[:30]


def _generate_canvas(graph: dict, adj: dict[str, set[str]], vault: Path) -> Path:
    """Generate an Obsidian .canvas file with the knowledge map.

    Canvas JSON format:
    {
      "nodes": [{"id", "type", "file"/"text", "x", "y", "width", "height", "color"}],
      "edges": [{"id", "fromNode", "toNode", "color"}]
    }
    """
    canvas_nodes = []
    canvas_edges = []

    # Group nodes by category for layout
    groups: dict[str, list[dict]] = defaultdict(list)
    for n in graph["nodes"]:
        groups[n["group"]].append(n)

    # Color palette for groups
    colors = {
        "concepts": "4",    # green
        "projects": "6",    # purple
        "people": "3",      # yellow
        "ai-tooling": "1",  # red
        "cymkube": "5",     # pink
        "blog-drafts": "0", # no color (gray)
        "openclaw": "2",    # orange
        "business": "3",    # yellow
        "sowork": "6",      # purple
        "infra": "1",       # red
        "finance": "3",     # yellow
        "people-meetings": "3",
        "misc": "0",
    }

    # Layout: arrange groups in a circular pattern
    group_list = sorted(groups.keys(), key=lambda g: len(groups[g]), reverse=True)
    n_groups = len(group_list)

    # Group label nodes (section headers)
    group_centers: dict[str, tuple[float, float]] = {}
    radius = 2000  # Spread groups in a circle
    for i, g in enumerate(group_list):
        angle = 2 * math.pi * i / n_groups
        cx = radius * math.cos(angle)
        cy = radius * math.sin(angle)
        group_centers[g] = (cx, cy)

        # Add group label as a text card
        canvas_nodes.append({
            "id": f"group-{g}",
            "type": "text",
            "text": f"# {g.upper()}\n{len(groups[g])} nodes",
            "x": int(cx - 150),
            "y": int(cy - 300),
            "width": 300,
            "height": 80,
            "color": colors.get(g, "0"),
        })

    # Place nodes within each group in a grid pattern
    node_positions: dict[str, tuple[int, int]] = {}
    for g, members in groups.items():
        cx, cy = group_centers[g]
        cols = max(1, int(math.ceil(math.sqrt(len(members)))))
        card_w = 260
        card_h = 80
        gap_x = card_w + 20
        gap_y = card_h + 20

        for idx, n in enumerate(sorted(members, key=lambda m: len(adj.get(m["id"], set())), reverse=True)):
            row = idx // cols
            col = idx % cols
            x = int(cx + (col - cols / 2) * gap_x)
            y = int(cy + row * gap_y)

            # Wiki articles link to the file; notes link to file
            node_id = n["id"].replace("/", "_").replace(".", "_")
            canvas_nodes.append({
                "id": node_id,
                "type": "file",
                "file": n["id"],
                "x": x,
                "y": y,
                "width": card_w,
                "height": card_h,
                "color": colors.get(g, "0"),
            })
            node_positions[n["id"]] = (x, y)

    # Add edges — only between wiki articles to keep it clean
    edge_id = 0
    added_edges: set[tuple[str, str]] = set()
    for e in graph["edges"]:
        src = e["source"]
        tgt = e["target"]
        # Only show wiki↔wiki and wiki↔notes edges
        if not (src.startswith("wiki/") or tgt.startswith("wiki/")):
            continue
        pair = tuple(sorted([src, tgt]))
        if pair in added_edges:
            continue
        added_edges.add(pair)

        src_id = src.replace("/", "_").replace(".", "_")
        tgt_id = tgt.replace("/", "_").replace(".", "_")

        # Check both nodes exist in the canvas
        if src not in node_positions or tgt not in node_positions:
            continue

        canvas_edges.append({
            "id": f"edge-{edge_id}",
            "fromNode": src_id,
            "toNode": tgt_id,
        })
        edge_id += 1

    canvas = {"nodes": canvas_nodes, "edges": canvas_edges}
    out_path = vault / "知識圖譜.canvas"
    out_path.write_text(json.dumps(canvas, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def analyze(vault: Path, generate_canvas: bool = False) -> dict:
    """Run full graph analysis."""
    graph = build_graph(vault)
    adj = _build_adjacency(graph)
    all_ids = {n["id"] for n in graph["nodes"]}

    degrees = _degree_stats(adj, graph["nodes"])
    components = _find_components(adj, all_ids)
    bridges = _find_bridges(adj, all_ids)
    density = _group_density(adj, graph["nodes"])
    suggestions = _suggest_links(adj, graph["nodes"])

    # Isolated nodes (degree 0 or 1)
    isolated = [d for d in degrees if d["degree"] <= 1]

    # Hub nodes (top 10 by degree)
    hubs = degrees[:10]

    canvas_path = None
    if generate_canvas:
        canvas_path = _generate_canvas(graph, adj, vault)

    return {
        "stats": graph["stats"],
        "components": [{"size": len(c), "sample": sorted(list(c))[:3]} for c in components[:5]],
        "hubs": hubs,
        "bridges": bridges[:10],
        "isolated": isolated,
        "group_density": density,
        "suggested_links": suggestions,
        "canvas_path": str(canvas_path) if canvas_path else None,
    }


@click.command()
@click.option("--vault", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--canvas", is_flag=True, default=False, help="Generate Obsidian .canvas file.")
@click.option("--json-out", is_flag=True, default=False, help="Output as JSON.")
def main(vault: Path, canvas: bool, json_out: bool) -> None:
    """Deep analysis of knowledge base graph structure."""
    result = analyze(vault, generate_canvas=canvas)

    if json_out:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return

    click.echo("\n  ╔══════════════════════════════════════╗")
    click.echo("  ║     Knowledge Graph Deep Analysis     ║")
    click.echo("  ╚══════════════════════════════════════╝")

    s = result["stats"]
    click.echo(f"\n  📊 Overview: {s['total_nodes']} nodes, {s['total_edges']} edges, {len(s['groups'])} groups")

    # Components
    click.echo(f"\n  🔗 Connected components: {len(result['components'])}")
    for i, c in enumerate(result["components"][:3]):
        click.echo(f"     #{i+1}: {c['size']} nodes — e.g. {', '.join(Path(s).stem for s in c['sample'])}")

    # Hubs
    click.echo("\n  🌟 Hub nodes (most connected):")
    for h in result["hubs"]:
        click.echo(f"     {h['degree']:3d} links — {h['label']} ({h['group']})")

    # Bridges
    click.echo("\n  🌉 Bridge nodes (connecting clusters):")
    for b in result["bridges"][:7]:
        groups_str = ", ".join(b["connects_groups"])
        click.echo(f"     {b['label']} — connects: {groups_str}")

    # Isolated
    click.echo(f"\n  🏝️  Isolated nodes (≤1 link): {len(result['isolated'])}")
    for iso in result["isolated"][:10]:
        click.echo(f"     {iso['degree']} links — {iso['label']} ({iso['group']})")

    # Group density
    click.echo("\n  📂 Group density:")
    click.echo(f"     {'Group':<20s} {'Nodes':>5s} {'Intra':>6s} {'Inter':>6s} {'Density':>8s}")
    for d in result["group_density"]:
        click.echo(f"     {d['group']:<20s} {d['nodes']:>5d} {d['intra_edges']:>6d} {d['inter_edges']:>6d} {d['density']:>8.3f}")

    # Suggestions
    click.echo(f"\n  💡 Suggested new links ({len(result['suggested_links'])} candidates):")
    for sg in result["suggested_links"][:10]:
        via = ", ".join(sg["shared_via"][:3])
        click.echo(f"     {sg['source_label']} ↔ {sg['target_label']} (via: {via})")

    if result["canvas_path"]:
        click.echo(f"\n  🗺️  Canvas → {result['canvas_path']}")

    click.echo()


if __name__ == "__main__":
    main()

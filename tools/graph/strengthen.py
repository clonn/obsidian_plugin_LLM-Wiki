"""Strengthen weak graph connections by adding cross-links between related articles.

Two strategies:
1. Wiki↔Wiki: Add [[backlinks]] in ## 相關 sections between wiki articles
   that share ≥2 neighbors but aren't directly linked.
2. Isolated→Hub: Connect isolated notes (≤1 link) to relevant wiki hubs
   by scanning their content for topic keywords.

Usage:
    uv run python -m graph.strengthen --vault ~/Dropbox/caesar_obsidian --dry-run
    uv run python -m graph.strengthen --vault ~/Dropbox/caesar_obsidian --apply
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import click

from graph.export_graph import build_graph, LINK_RE


def _build_adjacency(graph: dict) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = defaultdict(set)
    for e in graph["edges"]:
        adj[e["source"]].add(e["target"])
        adj[e["target"]].add(e["source"])
    return adj


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from text for topic matching."""
    # Remove frontmatter
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            text = text[end + 3:]
    # Remove links
    text = re.sub(r"\[\[.*?\]\]", "", text)
    # Lowercase for matching
    text_lower = text.lower()
    return set(text_lower.split())


# Topic → relevant wiki concepts mapping (keywords that indicate relation)
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "wiki/concepts/AI-Agents.md": ["agent", "agents", "ai agent", "代理", "agentic", "autonomous"],
    "wiki/concepts/Prompt-Engineering.md": ["prompt", "prompting", "提示", "prompt engineering"],
    "wiki/concepts/Vibe-Coding.md": ["vibe coding", "vibe", "氛圍", "cursor", "copilot"],
    "wiki/concepts/AI-Code-Generation.md": ["code generation", "程式碼生成", "coding", "生成"],
    "wiki/concepts/Claude-Code.md": ["claude", "claude code", "hooks", "sandbox"],
    "wiki/concepts/Cymkube-3D-SDK.md": ["cymkube", "3d", "sdk", "客製化", "列印", "公仔"],
    "wiki/concepts/Context-Engineering.md": ["context", "上下文", "context engineering"],
    "wiki/concepts/AI-創業策略.md": ["創業", "startup", "速度", "吳恩達"],
    "wiki/concepts/AI-Work-Revolution.md": ["工作革命", "超級個體", "一人公司", "假工作"],
    "wiki/concepts/AI-行銷.md": ["marketing", "行銷", "vibe marketing", "增長"],
    "wiki/concepts/LLM-Knowledge-Base.md": ["知識庫", "knowledge base", "karpathy", "compile"],
    "wiki/concepts/NotebookLM.md": ["notebooklm", "notebook", "pdf"],
    "wiki/concepts/OCR-Technology.md": ["ocr", "chandra", "文字辨識"],
    "wiki/concepts/Bloom-AI-Evaluation.md": ["bloom", "評估", "evaluation"],
    "wiki/concepts/社群媒體成長.md": ["threads", "社群", "成長"],
    "wiki/concepts/數位支付.md": ["支付", "payment", "金流", "藍新", "ecpay"],
    "wiki/concepts/全球貿易與地緣政治.md": ["關稅", "貿易", "tariff", "地緣"],
    "wiki/concepts/印刷色彩管理.md": ["色彩", "印刷", "delta e", "色彩管理"],
    "wiki/concepts/雲端伺服器部署.md": ["azure", "vm", "伺服器", "deploy"],
    "wiki/concepts/雲端AI基礎設施市場.md": ["oracle", "雲端", "基礎設施"],
    "wiki/concepts/台灣市場分析.md": ["台灣", "市場", "統計"],
    "wiki/concepts/一人公司模式.md": ["一人公司", "超級個體", "獨立", "solopreneur"],
    "wiki/concepts/水晶貼紙品質管理.md": ["水晶貼紙", "品質", "iqc", "qc"],
    "wiki/concepts/智慧眼鏡與製造業數位化.md": ["ray-ban", "眼鏡", "製造業", "驗收"],
    "wiki/concepts/Generative-Engine-Optimization.md": ["geo", "seo", "生成式引擎"],
    "wiki/concepts/Image-Generation-Nanobanana.md": ["nanobanana", "圖片生成", "image"],
    "wiki/concepts/Chatbot-SDK-Wechaty.md": ["wechaty", "chatbot", "聊天機器人"],
    "wiki/concepts/AI-Presentation-Tools.md": ["簡報", "presentation", "slides"],
    "wiki/concepts/AI-Driven-HR.md": ["hr", "招募", "人力資源"],
    "wiki/concepts/MBTI-AI-Templates.md": ["mbti", "personality", "人格"],
    "wiki/concepts/AI-神經網路基礎.md": ["神經網路", "cnn", "深度學習", "neural"],
    "wiki/concepts/Node.js環境配置.md": ["node", "nvm", "npm", "前端"],
    "wiki/concepts/全球AI工具生態系.md": ["ai工具", "ai 工具", "全球"],
    "wiki/concepts/3D列印市場.md": ["3d列印", "拓竹", "bambu", "3d打印"],
    "wiki/projects/Cymkube.md": ["cymkube", "cympotek", "正美"],
    "wiki/projects/OpenClaw.md": ["openclaw", "龍蝦", "蝦"],
    "wiki/projects/sowork.md": ["sowork", "共生", "企業作業系統"],
    "wiki/projects/CodingBear.md": ["coding bear", "台中場"],
    "wiki/projects/AP2.md": ["ap2", "跨境支付", "agent payments"],
    "wiki/projects/牙驛通.md": ["牙驛通", "牙醫", "遠距"],
    "wiki/projects/遠景公司合作.md": ["遠景", "海洋", "智慧包裝"],
}


def _match_score(text_lower: str, keywords: list[str]) -> int:
    """Count how many keywords appear in the text."""
    score = 0
    for kw in keywords:
        if kw in text_lower:
            score += 1
    return score


def _has_related_section(text: str) -> bool:
    """Check if file already has a 相關 section."""
    return bool(re.search(r"^##\s*相關", text, re.MULTILINE))


def _get_existing_links(text: str) -> set[str]:
    """Get all [[link]] targets already in the file."""
    return {m.group(1).strip() for m in LINK_RE.finditer(text)}


def strengthen(vault: Path, apply: bool) -> list[dict]:
    """Find and add strengthening links."""
    graph = build_graph(vault)
    adj = _build_adjacency(graph)
    all_nodes = {n["id"]: n for n in graph["nodes"]}
    changes: list[dict] = []

    # Strategy 1: Wiki↔Wiki cross-links via shared neighbors
    wiki_nodes = [n for n in graph["nodes"] if n["id"].startswith("wiki/")]
    wiki_ids = {n["id"] for n in wiki_nodes}

    for n in wiki_nodes:
        nid = n["id"]
        neighbors = adj.get(nid, set())
        path = vault / nid
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        existing = _get_existing_links(text)

        new_links: list[str] = []
        for other in wiki_nodes:
            oid = other["id"]
            if oid == nid or oid in neighbors:
                continue
            # Check if already linked
            ostem = Path(oid).stem
            opath_no_ext = oid.replace(".md", "")
            if opath_no_ext in existing or ostem in existing:
                continue
            # Count shared neighbors
            shared = neighbors & adj.get(oid, set())
            if len(shared) >= 3:
                new_links.append(oid)

        if new_links and not _has_related_section(text):
            links_md = "\n".join(f"- [[{lnk.replace('.md', '')}|{Path(lnk).stem}]]" for lnk in sorted(new_links))
            addition = f"\n\n## 相關\n\n{links_md}\n"
            if apply:
                path.write_text(text.rstrip() + addition, encoding="utf-8")
            changes.append({
                "file": nid,
                "type": "wiki-crosslink",
                "links_added": len(new_links),
                "targets": [Path(l).stem for l in new_links],
            })

    # Strategy 2: Connect isolated notes to wiki hubs via keyword matching
    isolated = [n for n in graph["nodes"]
                if len(adj.get(n["id"], set())) <= 1 and not n["id"].startswith("wiki/")]

    for n in isolated:
        nid = n["id"]
        path = vault / nid
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        existing = _get_existing_links(text)
        text_lower = text.lower()

        # Score against each wiki topic
        matches: list[tuple[str, int]] = []
        for wiki_id, keywords in TOPIC_KEYWORDS.items():
            if wiki_id.replace(".md", "") in existing or Path(wiki_id).stem in existing:
                continue
            score = _match_score(text_lower, keywords)
            if score >= 2:
                matches.append((wiki_id, score))

        matches.sort(key=lambda x: x[1], reverse=True)
        top_matches = matches[:3]  # Max 3 new links per isolated node

        if top_matches:
            # Add links at the end of the file
            links_md = "\n".join(
                f"- [[{wid.replace('.md', '')}|{Path(wid).stem}]]"
                for wid, _ in top_matches
            )
            if _has_related_section(text):
                # Append to existing section
                addition = "\n" + links_md + "\n"
            else:
                addition = f"\n\n## 相關\n\n{links_md}\n"

            if apply:
                path.write_text(text.rstrip() + addition, encoding="utf-8")
            changes.append({
                "file": nid,
                "type": "isolated-connect",
                "links_added": len(top_matches),
                "targets": [Path(wid).stem for wid, _ in top_matches],
            })

    return changes


@click.command()
@click.option("--vault", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--apply", is_flag=True, default=False)
@click.option("--dry-run", is_flag=True, default=False)
def main(vault: Path, apply: bool, dry_run: bool) -> None:
    """Strengthen weak graph connections."""
    if dry_run:
        apply = False

    changes = strengthen(vault, apply=apply)

    wiki_cross = [c for c in changes if c["type"] == "wiki-crosslink"]
    iso_connect = [c for c in changes if c["type"] == "isolated-connect"]

    click.echo(f"\n  {'Applied' if apply else 'Dry-run'} graph strengthening:")
    click.echo(f"  Wiki cross-links: {len(wiki_cross)} files, {sum(c['links_added'] for c in wiki_cross)} links")
    click.echo(f"  Isolated→Hub: {len(iso_connect)} files, {sum(c['links_added'] for c in iso_connect)} links")

    if wiki_cross:
        click.echo("\n  Wiki cross-links:")
        for c in wiki_cross:
            targets = ", ".join(c["targets"][:5])
            click.echo(f"    {Path(c['file']).stem} → {targets}")

    if iso_connect:
        click.echo("\n  Isolated node connections:")
        for c in iso_connect:
            targets = ", ".join(c["targets"][:3])
            click.echo(f"    {Path(c['file']).stem} → {targets}")

    total = sum(c["links_added"] for c in changes)
    click.echo(f"\n  Total: {total} new links in {len(changes)} files")


if __name__ == "__main__":
    main()

---
name: autoresearch
description: Autonomous web research on a topic. Decomposes into angles, searches, synthesizes, and creates wiki pages. Use when deep research is needed on a new topic.
user_invocable: true
---

# /autoresearch — Autonomous Research Loop

Research a topic thoroughly and create structured wiki pages.

## Process

1. **Decompose** the topic into 3-5 research angles
   - Show the angles to the user before proceeding
   - Each angle should cover a distinct facet

2. **For each angle** (can run in parallel):
   a. Web search for the angle
   b. Read top 3-5 results
   c. Extract key facts, data points, and sources
   d. Identify gaps or contradictions

3. **Gap-filling round** (up to 2 additional rounds):
   - Identify what's missing or contradictory
   - Targeted searches to fill gaps
   - Stop when coverage is sufficient

4. **Create wiki pages**:
   - One `wiki/concepts/<topic>.md` main article
   - Additional pages for sub-concepts if needed
   - Entity pages in `wiki/people/` or `wiki/projects/` if relevant
   - All in Traditional Chinese (zh-TW)

5. **Structure each page** with:
   ```yaml
   ---
   title: <topic>
   type: concept
   created: <today>
   updated: <today>
   tags: []
   sources:
     - <url1>
     - <url2>
   backlinks: []
   reviewed: false
   ---
   ```
   - `## 概要` — 2-3 sentence summary
   - `## 核心內容` — main content
   - `## 來源` — source URLs with brief description
   - `## 相關` — cross-links to existing wiki articles

6. **Update** index.md, log.md, and hot.md

7. **Run autolink** after creating pages to connect them to existing graph

## Rules

- Vault: /Users/caesarchi/Library/CloudStorage/Dropbox/caesar_obsidian
- All content in Traditional Chinese (zh-TW)
- Be terse — concept articles < 400 Chinese characters unless genuinely needed
- Always cite sources with URLs
- Flag contradictions between sources explicitly
- Maximum 300 lines per page

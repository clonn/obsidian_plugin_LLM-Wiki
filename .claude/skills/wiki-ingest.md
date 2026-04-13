---
name: wiki-ingest
description: Enhanced ingestion of source materials into the knowledge base. Extracts entities and concepts, creates/updates wiki pages, and cross-references. Use when adding new knowledge sources.
user_invocable: true
---

# /wiki-ingest — Enhanced Source Ingestion

Ingest source material and automatically extract structured knowledge.

## Input Types

- **File path**: Read a local file (markdown, PDF, text)
- **URL**: Fetch and clean web content, then ingest
- **Pasted text**: Process inline text from conversation

## Process

1. **Ingest to raw/**
   - Create `raw/YYYY-MM-DD_<slug>.md` with frontmatter:
     ```yaml
     ---
     title: <source title>
     ingested_at: <today>
     source: <file path or URL>
     ---
     ```
   - Preserve original content below frontmatter

2. **Entity Extraction**
   - Scan for people names → check wiki/people/, create if new
   - Scan for organizations → check wiki/projects/, create if new
   - Scan for products/tools → check wiki/concepts/, create if new
   - Each new entity gets a minimal wiki page with:
     ```yaml
     ---
     title: <entity name>
     type: <person|project|concept>
     created: <today>
     updated: <today>
     sources:
       - raw/<source file>
     backlinks: []
     reviewed: false
     ---
     ```

3. **Concept Extraction**
   - Identify key ideas, frameworks, patterns, technologies
   - For each concept:
     a. Check if wiki/concepts/ already has a page (by title or alias)
     b. If exists: append new information under `## 更新` section, add source to frontmatter
     c. If new: create wiki/concepts/<slug>.md

4. **Cross-Referencing**
   - Add [[wikilinks]] between new pages and existing related articles
   - Update backlinks in frontmatter of linked articles
   - Run autolink scan on new files

5. **Update Indexes**
   - Add new articles to index.md auto-summary section
   - Append log entry to log.md
   - Update hot.md with ingestion summary

## Conventions

- All content in Traditional Chinese (zh-TW)
- Be terse: concept articles < 400 Chinese characters
- One concept per page (atomic notes)
- Maximum 300 lines per page
- Don't duplicate — summarize and link
- Vault: /Users/caesarchi/Library/CloudStorage/Dropbox/caesar_obsidian

## Example Usage

```
/wiki-ingest https://example.com/article-about-ai-agents
/wiki-ingest ~/Downloads/meeting-notes.md
/wiki-ingest (then paste text)
```

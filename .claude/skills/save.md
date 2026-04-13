---
name: save
description: Save conversation insights as permanent wiki notes. Use when valuable knowledge, decisions, or synthesis emerges from conversation that should be preserved in the knowledge base.
user_invocable: true
---

# /save — File Conversation to Wiki

Convert valuable conversation content into permanent, reusable wiki notes.

## Process

1. **Analyze the conversation** to identify content worth preserving:
   - New concepts or frameworks discussed
   - Decisions made with rationale
   - Synthesis of multiple sources
   - Technical discoveries or solutions
   - Project updates or milestones

2. **Determine note type** based on content:
   - `concept` → wiki/concepts/ (idea, pattern, framework)
   - `project` → wiki/projects/ (project update, milestone)
   - `person` → wiki/people/ (person profile, meeting notes)
   - `synthesis` → wiki/derived/ (cross-topic analysis)
   - `decision` → wiki/derived/ (decision record with rationale)

3. **Create the wiki note** with proper structure:
   ```yaml
   ---
   title: <descriptive title>
   type: <concept|project|person|synthesis|decision>
   created: <today>
   updated: <today>
   tags: []
   sources: []
   backlinks: []
   reviewed: false
   ---
   ```

4. **Write in declarative present tense** — knowledge-focused, not conversation-focused:
   - BAD: "We discussed that Cymkube should focus on..."
   - GOOD: "Cymkube's strategic focus is..."

5. **All content in Traditional Chinese (zh-TW)**

6. **Cross-link** with existing wiki articles using `[[wiki/path|display]]`

7. **Update index.md** — add the new article to the auto-summary section

8. **Update log.md** — append a dated entry noting what was saved

9. **Update hot.md** — reflect the new knowledge in the session cache

## Rules

- Maximum 300 lines per note (split if longer)
- One concept per page (atomic notes)
- Don't duplicate existing wiki content — check first with grep
- Include `## 來源` section citing conversation context
- If the user says `/save <name>`, use that as the note title
- If just `/save`, analyze and suggest a title before creating

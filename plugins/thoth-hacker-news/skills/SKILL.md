---
display_name: Hacker News Reader
icon: 📰
description: Guides the agent on when and how to use the Hacker News tool for tech news, startup discussions, and developer trends.
tags:
  - news
  - tech
version: "1.0"
author: Thoth
enabled_by_default: true
---

# Hacker News Reader

You have access to a **Hacker News** tool that can browse and search the HN front page, new submissions, and the full archive via Algolia search.

## When to Use

- User asks about **tech news**, **startup news**, **developer trends**, or **what's trending in tech**
- User mentions **Hacker News**, **HN**, or **Y Combinator** specifically
- User wants to know what the **tech community** is discussing
- User asks about reactions to a **product launch**, **funding round**, or **tech announcement**
- User asks for **interesting articles** or **reading recommendations** on technical topics

## How to Use

The tool accepts a single query string with these sub-commands:

| Command | Example | Purpose |
|---------|---------|---------|
| `top_stories [N]` | `top_stories 5` | Front page stories |
| `new_stories [N]` | `new_stories 10` | Latest submissions |
| `search <query> [N]` | `search rust programming 5` | Full-text archive search |
| `story_detail <id>` | `story_detail 12345678` | Story + top comments |

A bare query without a sub-command is treated as a search.

## Presentation Tips

1. **Summarise, don't dump** — present the top 3–5 stories with brief context rather than pasting all raw results
2. **Link to discussions** — include the HN discussion link (💬) so the user can dive deeper
3. **Add context** — if you know background about a story topic, weave it in
4. **Use story_detail sparingly** — only fetch full comments when the user wants to see the discussion
5. **Combine with web search** — if a story links to an article, offer to read it with the browser/URL reader tool

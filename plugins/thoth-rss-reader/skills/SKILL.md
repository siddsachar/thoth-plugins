---
name: rss_reader
display_name: RSS Feed Reader
icon: "📡"
description: Guides the agent on when and how to use the RSS Reader tool for feed subscriptions and reading.
tags:
  - rss
  - feeds
  - news
  - reading
---

# RSS Feed Reader

You have access to the `rss_reader` tool for managing RSS and Atom feed subscriptions.

## When to Use

- User asks to subscribe to, follow, or track a blog, news source, or podcast
- User wants to read or check their feeds
- User asks "what's new" across their subscriptions
- User mentions an RSS or Atom feed URL

## Sub-commands

| Command | Purpose |
|---------|---------|
| `add_feed <url> [name]` | Subscribe to a feed; optionally give it a friendly name |
| `remove_feed <url\|name>` | Unsubscribe by URL or display name |
| `list_feeds` | Show all subscribed feeds |
| `fetch <url\|name> [count]` | Get latest entries from a specific feed |
| `fetch_all [count]` | Get latest entries across ALL feeds, merged by date |

## Presentation Tips

- After `add_feed`, confirm the subscription and mention how many entries are available
- For `fetch` / `fetch_all`, summarise the top 3-5 entries with titles and one-line descriptions rather than dumping raw output
- Group entries by topic or source when showing results from `fetch_all`
- Include links so the user can read the full article
- When fetching fails for some feeds, still show what succeeded and mention the failures briefly
- If the user has no feeds yet, suggest popular feeds relevant to their interests

## Example Interactions

User: "Subscribe me to the Hacker News RSS feed"
→ `add_feed https://hnrss.org/frontpage Hacker News`

User: "What's new in my feeds?"
→ `fetch_all 10`

User: "Check the Verge for new articles"
→ `fetch The Verge 5`

User: "Remove the TechCrunch feed"
→ `remove_feed TechCrunch`

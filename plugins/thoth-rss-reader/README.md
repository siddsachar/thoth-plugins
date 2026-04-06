# 📡 RSS Reader

Subscribe to and read RSS/Atom feeds directly from Thoth.

## Features

- **Subscribe to feeds** — add any RSS or Atom feed by URL
- **Fetch latest entries** — read recent entries from a single feed or all at once
- **Manage subscriptions** — list and remove feeds
- **Smart formatting** — entries include title, summary, link, and relative time

## Installation

Install from the Thoth plugin marketplace (Settings → Plugins → Marketplace) or manually:

1. Copy the `thoth-rss-reader` folder to `~/.thoth/installed_plugins/`
2. Restart Thoth

Requires `feedparser` (installed automatically by the marketplace).

## Usage

The agent uses this tool automatically when you mention RSS, feeds, or news sources. You can also be explicit:

- *"Subscribe to https://blog.example.com/feed.xml"*
- *"What's new on my RSS feeds?"*
- *"Show me the latest entries from TechCrunch"*
- *"Unsubscribe from that feed"*
- *"List my feeds"*

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `default_count` | 10 | Number of entries returned per request (1–30) |

Configurable in Settings → Plugins → RSS Reader.

## Sub-commands

The tool accepts these sub-commands (the agent selects the right one automatically):

| Command | Example | Description |
|---------|---------|-------------|
| `add_feed <url> [name]` | `add_feed https://blog.example.com/rss My Blog` | Subscribe to a feed |
| `remove_feed <name\|url>` | `remove_feed My Blog` | Unsubscribe from a feed |
| `list_feeds` | `list_feeds` | Show all subscriptions |
| `fetch <name\|url> [N]` | `fetch TechCrunch 5` | Fetch entries from one feed |
| `fetch_all [N]` | `fetch_all 10` | Fetch entries from all feeds, merged by date |

A bare URL (without a command) is treated as `fetch <url>`.

## Dependencies

- [feedparser](https://feedparser.readthedocs.io/) — universal RSS/Atom parser (no API key needed)

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.

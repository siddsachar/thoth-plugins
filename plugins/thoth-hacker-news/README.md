# 📰 Hacker News Reader

Browse and search [Hacker News](https://news.ycombinator.com) directly from Thoth.

## Features

- **Front page** — see what's trending on HN right now
- **New stories** — discover the latest submissions
- **Full-text search** — search the entire HN archive via Algolia
- **Story details** — read top comments on any story

## Installation

Install from the Thoth plugin marketplace (Settings → Plugins → Marketplace) or manually:

1. Copy the `thoth-hacker-news` folder to `~/.thoth/installed_plugins/`
2. Restart Thoth

No API key or configuration needed — works out of the box.

## Usage

The agent uses this tool automatically when you ask about tech news, HN discussions, or trending topics. You can also be explicit:

- *"What's on Hacker News right now?"*
- *"Search HN for articles about Rust"*
- *"Show me the latest HN posts"*
- *"What are people saying about the new GPT-5 release on HN?"*

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `default_count` | 10 | Number of stories returned per request (1–30) |

Configurable in Settings → Plugins → Hacker News Reader.

## Sub-commands

The tool accepts these sub-commands (the agent selects the right one automatically):

| Command | Example | Description |
|---------|---------|-------------|
| `top_stories [N]` | `top_stories 5` | HN front page stories |
| `new_stories [N]` | `new_stories 10` | Latest submissions |
| `search <query> [N]` | `search rust 5` | Full-text archive search |
| `story_detail <id>` | `story_detail 12345` | Story + top comments |

## APIs Used

- [HN Firebase API](https://github.com/HackerNewsAPI/HackerNewsAPI) — stories, items, users (no auth)
- [Algolia HN Search](https://hn.algolia.com/api) — full-text search (no auth)

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.

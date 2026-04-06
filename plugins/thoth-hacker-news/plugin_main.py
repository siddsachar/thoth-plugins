"""Hacker News Reader — browse and search HN from Thoth.

Sub-commands:
  top_stories  — front-page stories (ranked by HN algorithm)
  new_stories  — newest submissions
  search       — full-text search via Algolia
  story_detail — full story with top comments
"""

from __future__ import annotations

import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from typing import Any

from plugins.api import PluginAPI, PluginTool

# ── HN Firebase API ─────────────────────────────────────────────────────────
_HN_BASE = "https://hacker-news.firebaseio.com/v0"
_ALGOLIA_BASE = "https://hn.algolia.com/api/v1"
_REQUEST_TIMEOUT = 10  # seconds


def _fetch_json(url: str) -> Any:
    """GET a URL and parse the JSON response."""
    req = urllib.request.Request(url, headers={"User-Agent": "Thoth-HN-Plugin/1.0"})
    with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _relative_time(unix_ts: int | None) -> str:
    """Convert a Unix timestamp to a human-readable relative string."""
    if not unix_ts:
        return ""
    now = datetime.now(timezone.utc)
    dt = datetime.fromtimestamp(unix_ts, tz=timezone.utc)
    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 30:
        return f"{days}d ago"
    months = days // 30
    return f"{months}mo ago"


def _fetch_item(item_id: int) -> dict | None:
    """Fetch a single HN item by ID."""
    try:
        return _fetch_json(f"{_HN_BASE}/item/{item_id}.json")
    except Exception:
        return None


def _format_story(item: dict, index: int | None = None) -> str:
    """Format a story item into a readable block."""
    title = item.get("title", "Untitled")
    url = item.get("url", "")
    score = item.get("score", 0)
    by = item.get("by", "unknown")
    time_str = _relative_time(item.get("time"))
    descendants = item.get("descendants", 0)
    item_id = item.get("id", "")
    hn_link = f"https://news.ycombinator.com/item?id={item_id}"

    prefix = f"[{index}] " if index is not None else ""
    lines = [f"{prefix}**{title}**"]
    if url:
        lines.append(f"   🔗 {url}")
    lines.append(f"   ▲ {score} points · {by} · {time_str} · {descendants} comments")
    lines.append(f"   💬 {hn_link}")
    return "\n".join(lines)


def _fetch_stories(endpoint: str, count: int) -> str:
    """Fetch story IDs from an endpoint and return formatted results."""
    story_ids = _fetch_json(f"{_HN_BASE}/{endpoint}.json")
    story_ids = story_ids[:count]

    stories = []
    for sid in story_ids:
        item = _fetch_item(sid)
        if item and item.get("type") == "story":
            stories.append(item)

    if not stories:
        return "No stories found."

    parts = []
    for i, story in enumerate(stories, 1):
        parts.append(_format_story(story, index=i))
    return "\n\n".join(parts)


# ── Algolia Search ──────────────────────────────────────────────────────────
def _search_hn(query: str, count: int) -> str:
    """Search HN via Algolia and return formatted results."""
    params = urllib.parse.urlencode({
        "query": query,
        "tags": "story",
        "hitsPerPage": count,
    })
    url = f"{_ALGOLIA_BASE}/search?{params}"
    data = _fetch_json(url)
    hits = data.get("hits", [])

    if not hits:
        return f"No Hacker News results found for: {query}"

    parts = []
    for i, hit in enumerate(hits, 1):
        title = hit.get("title", "Untitled")
        link = hit.get("url", "")
        points = hit.get("points", 0)
        author = hit.get("author", "unknown")
        num_comments = hit.get("num_comments", 0)
        created_at = hit.get("created_at_i")
        time_str = _relative_time(created_at)
        object_id = hit.get("objectID", "")
        hn_link = f"https://news.ycombinator.com/item?id={object_id}"

        lines = [f"[{i}] **{title}**"]
        if link:
            lines.append(f"   🔗 {link}")
        lines.append(f"   ▲ {points} points · {author} · {time_str} · {num_comments} comments")
        lines.append(f"   💬 {hn_link}")
        parts.append("\n".join(lines))

    return "\n\n".join(parts)


# ── Story Detail ────────────────────────────────────────────────────────────
def _story_detail(story_id: int, comment_count: int = 5) -> str:
    """Fetch a story and its top comments."""
    item = _fetch_item(story_id)
    if not item:
        return f"Could not find story with ID {story_id}."

    if item.get("type") != "story":
        return f"Item {story_id} is a {item.get('type', 'unknown')}, not a story."

    result = _format_story(item)

    # Fetch text content if it's an Ask HN / Show HN
    text = item.get("text", "")
    if text:
        # Strip HTML tags (basic)
        import re
        clean = re.sub(r"<[^>]+>", "", text)
        clean = clean.replace("&#x27;", "'").replace("&quot;", '"').replace("&amp;", "&")
        result += f"\n\n📝 **Post text:**\n{clean}"

    # Fetch top comments
    comment_ids = item.get("kids", [])[:comment_count]
    if comment_ids:
        result += f"\n\n💬 **Top {len(comment_ids)} comments:**\n"
        for idx, cid in enumerate(comment_ids, 1):
            comment = _fetch_item(cid)
            if comment and comment.get("text"):
                import re
                clean = re.sub(r"<[^>]+>", "", comment["text"])
                clean = clean.replace("&#x27;", "'").replace("&quot;", '"').replace("&amp;", "&")
                by = comment.get("by", "unknown")
                time_str = _relative_time(comment.get("time"))
                # Truncate long comments
                if len(clean) > 500:
                    clean = clean[:497] + "..."
                result += f"\n---\n**{by}** · {time_str}\n{clean}\n"

    return result


# ── Query Parser ────────────────────────────────────────────────────────────
def _parse_query(query: str, default_count: int) -> tuple[str, dict]:
    """Parse a natural-language query into (action, params).

    Supported formats:
      top_stories [count]
      new_stories [count]
      search <query> [count]
      story_detail <id> [comments:N]
      <bare text> → treated as search
    """
    query = query.strip()
    if not query:
        return "top_stories", {"count": default_count}

    parts = query.split(None, 1)
    action = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""

    if action == "top_stories":
        count = _parse_int(rest, default_count)
        return "top_stories", {"count": count}

    elif action == "new_stories":
        count = _parse_int(rest, default_count)
        return "new_stories", {"count": count}

    elif action == "search":
        if not rest:
            return "error", {"message": "Please provide a search query. Usage: search <query>"}
        # Check for trailing count like "search rust lang 5"
        tokens = rest.rsplit(None, 1)
        if len(tokens) == 2 and tokens[1].isdigit():
            return "search", {"query": tokens[0], "count": int(tokens[1])}
        return "search", {"query": rest, "count": default_count}

    elif action == "story_detail":
        if not rest:
            return "error", {"message": "Please provide a story ID. Usage: story_detail <id>"}
        tokens = rest.split()
        try:
            story_id = int(tokens[0])
        except (ValueError, TypeError):
            return "error", {"message": f"Invalid story ID: {tokens[0]}"}
        if story_id <= 0:
            return "error", {"message": f"Invalid story ID: {tokens[0]}"}
        comment_count = 5
        for t in tokens[1:]:
            if t.startswith("comments:"):
                comment_count = _parse_int(t.split(":", 1)[1], 5)
        return "story_detail", {"story_id": story_id, "comment_count": comment_count}

    else:
        # Bare text → treat as search
        return "search", {"query": query, "count": default_count}


def _parse_int(s: str, default: int) -> int:
    """Parse an integer string with a fallback default."""
    s = s.strip()
    if s.isdigit():
        return max(1, min(int(s), 30))
    return default


# ═════════════════════════════════════════════════════════════════════════════
# HackerNewsTool
# ═════════════════════════════════════════════════════════════════════════════
class HackerNewsTool(PluginTool):
    """Browse and search Hacker News."""

    @property
    def name(self) -> str:
        return "hacker_news"

    @property
    def display_name(self) -> str:
        return "📰 Hacker News"

    @property
    def description(self) -> str:
        return (
            "Browse and search Hacker News. "
            "Sub-commands: "
            "top_stories [count] — front page stories; "
            "new_stories [count] — newest submissions; "
            "search <query> [count] — full-text search; "
            "story_detail <id> [comments:N] — story with top comments. "
            "Default count is 10. A bare query (no sub-command) is treated as search."
        )

    def execute(self, query: str) -> str:
        default_count = self.plugin_api.get_config("default_count", 10)
        try:
            default_count = int(default_count)
        except (TypeError, ValueError):
            default_count = 10
        default_count = max(1, min(default_count, 30))

        try:
            action, params = _parse_query(query, default_count)
        except Exception as exc:
            return f"Error parsing query: {exc}"

        try:
            if action == "top_stories":
                return _fetch_stories("topstories", params["count"])
            elif action == "new_stories":
                return _fetch_stories("newstories", params["count"])
            elif action == "search":
                return _search_hn(params["query"], params["count"])
            elif action == "story_detail":
                return _story_detail(params["story_id"], params.get("comment_count", 5))
            elif action == "error":
                return params["message"]
            else:
                return f"Unknown action: {action}"
        except urllib.error.URLError as exc:
            return f"Network error accessing Hacker News: {exc}"
        except Exception as exc:
            return f"Error fetching from Hacker News: {exc}"


# ═════════════════════════════════════════════════════════════════════════════
# Plugin Registration
# ═════════════════════════════════════════════════════════════════════════════
def register(api: PluginAPI):
    """Called by Thoth when the plugin loads."""
    api.register_tool(HackerNewsTool(api))

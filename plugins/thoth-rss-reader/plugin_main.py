"""RSS Reader — subscribe to and read RSS/Atom feeds from Thoth.

Sub-commands:
  add_feed    — subscribe to a feed
  remove_feed — unsubscribe from a feed
  list_feeds  — show all subscribed feeds
  fetch       — get latest entries from a specific feed
  fetch_all   — get latest entries across all feeds
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from time import mktime
from typing import Any

from plugins.api import PluginAPI, PluginTool

_REQUEST_TIMEOUT = 10  # seconds


# ── Feed Storage ─────────────────────────────────────────────────────────────
def _get_feeds(api: PluginAPI) -> list[dict]:
    """Load the list of subscribed feeds from plugin config.

    Each feed is ``{"url": "...", "name": "..."}``.
    """
    raw = api.get_config("feeds", "[]")
    if isinstance(raw, list):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []


def _save_feeds(api: PluginAPI, feeds: list[dict]) -> None:
    """Persist the feeds list."""
    api.set_config("feeds", json.dumps(feeds))


def _find_feed(feeds: list[dict], identifier: str) -> dict | None:
    """Look up a feed by URL or display name (case-insensitive)."""
    identifier_lower = identifier.strip().lower()
    for f in feeds:
        if f["url"].lower() == identifier_lower or f["name"].lower() == identifier_lower:
            return f
    return None


# ── Feed Parsing ─────────────────────────────────────────────────────────────
def _parse_feed(url: str) -> Any:
    """Fetch and parse a feed URL. Returns a feedparser result."""
    import feedparser

    result = feedparser.parse(
        url,
        request_headers={"User-Agent": "Thoth-RSS-Plugin/1.0"},
    )
    return result


def _entry_date(entry: Any) -> datetime:
    """Extract a datetime from a feed entry, falling back to now."""
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None) or entry.get(attr)
        if val:
            try:
                return datetime.fromtimestamp(mktime(val), tz=timezone.utc)
            except (TypeError, OverflowError, ValueError):
                pass
    return datetime.now(timezone.utc)


def _relative_time(dt: datetime) -> str:
    """Convert a datetime to a human-readable relative string."""
    now = datetime.now(timezone.utc)
    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < 0:
        return "just now"
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


def _truncate(text: str, length: int = 200) -> str:
    """Truncate text to *length* characters, adding an ellipsis."""
    text = re.sub(r"<[^>]+>", "", text)  # strip HTML
    text = text.replace("\n", " ").strip()
    if len(text) <= length:
        return text
    return text[: length - 3].rstrip() + "..."


def _format_entry(entry: Any, index: int, feed_name: str = "") -> str:
    """Format a single feed entry into a readable block."""
    title = entry.get("title", "Untitled")
    link = entry.get("link", "")
    summary = _truncate(entry.get("summary", entry.get("description", "")))
    dt = _entry_date(entry)
    time_str = _relative_time(dt)

    prefix = f"[{index}]"
    source = f" · 📡 {feed_name}" if feed_name else ""
    lines = [f"{prefix} **{title}**"]
    if link:
        lines.append(f"   🔗 {link}")
    if summary:
        lines.append(f"   {summary}")
    lines.append(f"   🕐 {time_str}{source}")
    return "\n".join(lines)


# ── Sub-command Handlers ─────────────────────────────────────────────────────
def _add_feed(api: PluginAPI, url: str, name: str) -> str:
    """Subscribe to a new feed."""
    url = url.strip()
    if not url:
        return "Error: Please provide a feed URL. Usage: add_feed <url> [name]"

    if not re.match(r"https?://", url, re.IGNORECASE):
        return f"Error: Invalid URL — must start with http:// or https://. Got: {url}"

    feeds = _get_feeds(api)

    # Check for duplicate
    if _find_feed(feeds, url):
        return f"Already subscribed to: {url}"

    # Validate by fetching the feed
    try:
        result = _parse_feed(url)
    except Exception as exc:
        return f"Error fetching feed: {exc}"

    if result.bozo and not result.entries:
        err = getattr(result, "bozo_exception", "unknown error")
        return f"Error: Could not parse feed at {url} — {err}"

    feed_title = result.feed.get("title", "")
    if not name:
        name = feed_title or url.split("/")[-1] or url

    feeds.append({"url": url, "name": name})
    _save_feeds(api, feeds)

    entry_count = len(result.entries)
    return (
        f"✅ Subscribed to **{name}**\n"
        f"   🔗 {url}\n"
        f"   📄 {entry_count} entries available"
    )


def _remove_feed(api: PluginAPI, identifier: str) -> str:
    """Unsubscribe from a feed by URL or name."""
    identifier = identifier.strip()
    if not identifier:
        return "Error: Please specify a feed URL or name. Usage: remove_feed <url|name>"

    feeds = _get_feeds(api)
    match = _find_feed(feeds, identifier)
    if not match:
        return f"No feed found matching: {identifier}"

    feeds = [f for f in feeds if f["url"] != match["url"]]
    _save_feeds(api, feeds)
    return f"✅ Unsubscribed from **{match['name']}** ({match['url']})"


def _list_feeds(api: PluginAPI) -> str:
    """List all subscribed feeds."""
    feeds = _get_feeds(api)
    if not feeds:
        return (
            "No feeds subscribed yet.\n"
            "Use `add_feed <url> [name]` to subscribe to a feed."
        )

    parts = [f"**📡 {len(feeds)} subscribed feed{'s' if len(feeds) != 1 else ''}:**\n"]
    for i, f in enumerate(feeds, 1):
        parts.append(f"[{i}] **{f['name']}**\n   🔗 {f['url']}")
    return "\n\n".join(parts)


def _fetch_feed(api: PluginAPI, identifier: str, count: int) -> str:
    """Fetch latest entries from a specific feed."""
    identifier = identifier.strip()
    if not identifier:
        return "Error: Please specify a feed URL or name. Usage: fetch <url|name> [count]"

    feeds = _get_feeds(api)
    match = _find_feed(feeds, identifier)

    # Allow fetching a URL that isn't subscribed
    url = match["url"] if match else identifier
    feed_name = match["name"] if match else ""

    if not re.match(r"https?://", url, re.IGNORECASE):
        return f"No feed found matching: {identifier}"

    try:
        result = _parse_feed(url)
    except Exception as exc:
        return f"Error fetching feed: {exc}"

    if not result.entries:
        return f"No entries found in feed: {url}"

    if not feed_name:
        feed_name = result.feed.get("title", url)

    entries = sorted(result.entries, key=_entry_date, reverse=True)[:count]

    parts = [f"**📡 {feed_name}** — {len(entries)} latest entries:\n"]
    for i, entry in enumerate(entries, 1):
        parts.append(_format_entry(entry, i))
    return "\n\n".join(parts)


def _fetch_all(api: PluginAPI, count: int) -> str:
    """Fetch latest entries across all subscribed feeds, merged by date."""
    feeds = _get_feeds(api)
    if not feeds:
        return (
            "No feeds subscribed yet.\n"
            "Use `add_feed <url> [name]` to subscribe to a feed."
        )

    all_entries: list[tuple[Any, str]] = []  # (entry, feed_name)
    errors: list[str] = []

    for f in feeds:
        try:
            result = _parse_feed(f["url"])
            for entry in result.entries:
                all_entries.append((entry, f["name"]))
        except Exception as exc:
            errors.append(f"⚠️ {f['name']}: {exc}")

    if not all_entries and errors:
        return "Could not fetch any feeds:\n" + "\n".join(errors)

    if not all_entries:
        return "No entries found across any subscribed feed."

    # Sort by date descending and take top N
    all_entries.sort(key=lambda pair: _entry_date(pair[0]), reverse=True)
    top = all_entries[:count]

    parts = [f"**📡 Latest across {len(feeds)} feeds** — {len(top)} entries:\n"]
    for i, (entry, feed_name) in enumerate(top, 1):
        parts.append(_format_entry(entry, i, feed_name=feed_name))

    if errors:
        parts.append("\n---\n" + "\n".join(errors))

    return "\n\n".join(parts)


# ── Query Parser ─────────────────────────────────────────────────────────────
def _parse_int(s: str, default: int) -> int:
    """Parse an integer string with fallback, clamped to 1-30."""
    s = s.strip()
    if s.isdigit():
        return max(1, min(int(s), 30))
    return default


def _parse_query(query: str, default_count: int) -> tuple[str, dict]:
    """Parse a natural-language query into (action, params).

    Supported formats:
      add_feed <url> [name]
      remove_feed <url|name>
      list_feeds
      fetch <url|name> [count]
      fetch_all [count]
    """
    query = query.strip()
    if not query:
        return "list_feeds", {}

    parts = query.split(None, 1)
    action = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""

    if action == "add_feed":
        tokens = rest.split(None, 1)
        url = tokens[0] if tokens else ""
        name = tokens[1] if len(tokens) > 1 else ""
        return "add_feed", {"url": url, "name": name}

    elif action == "remove_feed":
        return "remove_feed", {"identifier": rest}

    elif action in ("list_feeds", "list"):
        return "list_feeds", {}

    elif action == "fetch":
        if not rest:
            return "error", {"message": "Please specify a feed. Usage: fetch <url|name> [count]"}
        # Check if last token is a count
        tokens = rest.rsplit(None, 1)
        if len(tokens) == 2 and tokens[1].isdigit():
            return "fetch", {"identifier": tokens[0], "count": int(tokens[1])}
        return "fetch", {"identifier": rest, "count": default_count}

    elif action == "fetch_all":
        count = _parse_int(rest, default_count)
        return "fetch_all", {"count": count}

    else:
        # Bare text — could be a feed name for fetch, or default to list
        # If it looks like a URL, treat as fetch
        if re.match(r"https?://", query, re.IGNORECASE):
            return "fetch", {"identifier": query, "count": default_count}
        return "error", {
            "message": (
                f"Unknown command: {action}\n"
                "Available commands: add_feed, remove_feed, list_feeds, fetch, fetch_all"
            ),
        }


# ═════════════════════════════════════════════════════════════════════════════
# RSSReaderTool
# ═════════════════════════════════════════════════════════════════════════════
class RSSReaderTool(PluginTool):
    """Read and manage RSS/Atom feed subscriptions."""

    @property
    def name(self) -> str:
        return "rss_reader"

    @property
    def display_name(self) -> str:
        return "📡 RSS Reader"

    @property
    def description(self) -> str:
        return (
            "Manage RSS/Atom feed subscriptions and fetch latest entries. "
            "Pass a plain-text command string as the query argument. "
            "Examples: "
            "query='add_feed https://example.com/rss Ars Technica' | "
            "query='remove_feed Ars Technica' | "
            "query='list_feeds' | "
            "query='fetch Ars Technica 5' | "
            "query='fetch_all 10'"
        )

    def execute(self, query: str) -> str:
        default_count = self.plugin_api.get_config("default_count", 10)
        if isinstance(default_count, str):
            default_count = _parse_int(default_count, 10)

        action, params = _parse_query(query, default_count)

        try:
            if action == "add_feed":
                return _add_feed(self.plugin_api, params["url"], params["name"])
            elif action == "remove_feed":
                return _remove_feed(self.plugin_api, params["identifier"])
            elif action == "list_feeds":
                return _list_feeds(self.plugin_api)
            elif action == "fetch":
                return _fetch_feed(
                    self.plugin_api, params["identifier"],
                    min(params.get("count", default_count), 30),
                )
            elif action == "fetch_all":
                return _fetch_all(self.plugin_api, min(params["count"], 30))
            elif action == "error":
                return params["message"]
            else:
                return f"Unknown action: {action}"
        except Exception as exc:
            return f"Error: {exc}"


# ── Registration ─────────────────────────────────────────────────────────────
def register(api: PluginAPI):
    """Called by Thoth on startup."""
    api.register_tool(RSSReaderTool(api))

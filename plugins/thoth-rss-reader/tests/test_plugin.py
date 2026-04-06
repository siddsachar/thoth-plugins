"""Tests for thoth-rss-reader plugin."""

import json
import os
import pathlib
import sys
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from time import struct_time

# Ensure Thoth root is on path so `from plugins.api import ...` resolves.
PLUGIN_DIR = pathlib.Path(__file__).parent.parent
_thoth_root = os.environ.get("THOTH_ROOT")
if _thoth_root:
    THOTH_ROOT = pathlib.Path(_thoth_root)
else:
    candidate = PLUGIN_DIR.parent.parent.parent / "Thoth"
    if (candidate / "plugins" / "api.py").exists():
        THOTH_ROOT = candidate
    else:
        THOTH_ROOT = PLUGIN_DIR.parent.parent.parent

if str(THOTH_ROOT) not in sys.path:
    sys.path.insert(0, str(THOTH_ROOT))


def _load_module():
    """Dynamically load plugin_main.py."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "plugin_main", PLUGIN_DIR / "plugin_main.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_api(**config_overrides) -> MagicMock:
    """Create a mock PluginAPI with a dict-backed config store."""
    api = MagicMock()
    store = {}
    store.update(config_overrides)
    api.get_config = MagicMock(side_effect=lambda k, default=None: store.get(k, default))
    api.set_config = MagicMock(side_effect=lambda k, v: store.__setitem__(k, v))
    return api


def _make_entry(title="Test", link="https://example.com", summary="A test entry",
                minutes_ago=10):
    """Create a mock feedparser entry."""
    dt = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    tt = dt.timetuple()
    return {
        "title": title,
        "link": link,
        "summary": summary,
        "published_parsed": struct_time(tt),
    }


def _make_feed_result(entries=None, title="Test Feed", bozo=False, bozo_exception=None):
    """Create a mock feedparser result."""
    result = MagicMock()
    result.entries = entries or []
    result.feed = {"title": title}
    result.bozo = bozo
    result.bozo_exception = bozo_exception
    return result


# ── Manifest Tests ──────────────────────────────────────────────────────────
class TestManifest(unittest.TestCase):

    def setUp(self):
        with open(PLUGIN_DIR / "plugin.json", "r", encoding="utf-8") as f:
            self.manifest = json.load(f)

    def test_required_fields(self):
        for field in ("id", "name", "version", "min_thoth_version",
                      "author", "description"):
            self.assertIn(field, self.manifest, f"Missing '{field}'")

    def test_id_format(self):
        self.assertEqual(self.manifest["id"], "thoth-rss-reader")

    def test_author(self):
        self.assertEqual(self.manifest["author"]["name"], "Thoth")
        self.assertEqual(self.manifest["author"]["github"], "siddsachar")

    def test_provides_one_tool(self):
        tools = self.manifest["provides"]["tools"]
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "rss_reader")

    def test_provides_one_skill(self):
        skills = self.manifest["provides"]["skills"]
        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0]["name"], "rss_reader")

    def test_has_feedparser_dependency(self):
        deps = self.manifest["python_dependencies"]
        self.assertTrue(any("feedparser" in d for d in deps))

    def test_license_is_apache(self):
        self.assertEqual(self.manifest["license"], "Apache-2.0")


# ── Register Function Tests ─────────────────────────────────────────────────
class TestRegister(unittest.TestCase):

    def test_register_exists_and_callable(self):
        module = _load_module()
        self.assertTrue(hasattr(module, "register"))
        self.assertTrue(callable(module.register))

    def test_register_registers_tool(self):
        module = _load_module()
        mock_api = MagicMock()
        module.register(mock_api)
        mock_api.register_tool.assert_called_once()
        tool = mock_api.register_tool.call_args[0][0]
        self.assertEqual(tool.name, "rss_reader")
        self.assertEqual(tool.display_name, "📡 RSS Reader")


# ── Query Parser Tests ──────────────────────────────────────────────────────
class TestQueryParser(unittest.TestCase):

    def setUp(self):
        self.mod = _load_module()

    def test_empty_query_defaults_to_list_feeds(self):
        action, params = self.mod._parse_query("", 10)
        self.assertEqual(action, "list_feeds")

    def test_add_feed_url_only(self):
        action, params = self.mod._parse_query("add_feed https://example.com/feed.xml", 10)
        self.assertEqual(action, "add_feed")
        self.assertEqual(params["url"], "https://example.com/feed.xml")
        self.assertEqual(params["name"], "")

    def test_add_feed_url_with_name(self):
        action, params = self.mod._parse_query(
            "add_feed https://example.com/feed.xml My Blog", 10
        )
        self.assertEqual(action, "add_feed")
        self.assertEqual(params["url"], "https://example.com/feed.xml")
        self.assertEqual(params["name"], "My Blog")

    def test_remove_feed(self):
        action, params = self.mod._parse_query("remove_feed TechCrunch", 10)
        self.assertEqual(action, "remove_feed")
        self.assertEqual(params["identifier"], "TechCrunch")

    def test_list_feeds(self):
        action, _ = self.mod._parse_query("list_feeds", 10)
        self.assertEqual(action, "list_feeds")

    def test_list_alias(self):
        action, _ = self.mod._parse_query("list", 10)
        self.assertEqual(action, "list_feeds")

    def test_fetch_by_name(self):
        action, params = self.mod._parse_query("fetch TechCrunch", 10)
        self.assertEqual(action, "fetch")
        self.assertEqual(params["identifier"], "TechCrunch")
        self.assertEqual(params["count"], 10)

    def test_fetch_with_count(self):
        action, params = self.mod._parse_query("fetch TechCrunch 5", 10)
        self.assertEqual(action, "fetch")
        self.assertEqual(params["identifier"], "TechCrunch")
        self.assertEqual(params["count"], 5)

    def test_fetch_all(self):
        action, params = self.mod._parse_query("fetch_all", 10)
        self.assertEqual(action, "fetch_all")
        self.assertEqual(params["count"], 10)

    def test_fetch_all_with_count(self):
        action, params = self.mod._parse_query("fetch_all 5", 10)
        self.assertEqual(action, "fetch_all")
        self.assertEqual(params["count"], 5)

    def test_bare_url_treated_as_fetch(self):
        action, params = self.mod._parse_query("https://example.com/feed.xml", 10)
        self.assertEqual(action, "fetch")
        self.assertEqual(params["identifier"], "https://example.com/feed.xml")

    def test_unknown_command_returns_error(self):
        action, params = self.mod._parse_query("explode everything", 10)
        self.assertEqual(action, "error")
        self.assertIn("Unknown command", params["message"])


# ── Feed Storage Tests ──────────────────────────────────────────────────────
class TestFeedStorage(unittest.TestCase):

    def setUp(self):
        self.mod = _load_module()

    def test_get_feeds_empty(self):
        api = _make_api()
        feeds = self.mod._get_feeds(api)
        self.assertEqual(feeds, [])

    def test_get_feeds_json_string(self):
        api = _make_api(feeds='[{"url":"https://a.com","name":"A"}]')
        feeds = self.mod._get_feeds(api)
        self.assertEqual(len(feeds), 1)
        self.assertEqual(feeds[0]["url"], "https://a.com")

    def test_get_feeds_list_passthrough(self):
        data = [{"url": "https://b.com", "name": "B"}]
        api = _make_api(feeds=data)
        feeds = self.mod._get_feeds(api)
        self.assertEqual(feeds, data)

    def test_save_and_get_roundtrip(self):
        api = _make_api()
        feeds = [{"url": "https://c.com", "name": "C"}]
        self.mod._save_feeds(api, feeds)
        api.set_config.assert_called_once()
        # Verify it called with valid JSON
        saved = api.set_config.call_args[0][1]
        parsed = json.loads(saved)
        self.assertEqual(parsed, feeds)

    def test_find_feed_by_url(self):
        feeds = [{"url": "https://a.com/feed", "name": "Blog A"}]
        match = self.mod._find_feed(feeds, "https://a.com/feed")
        self.assertIsNotNone(match)
        self.assertEqual(match["name"], "Blog A")

    def test_find_feed_by_name_case_insensitive(self):
        feeds = [{"url": "https://a.com/feed", "name": "Blog A"}]
        match = self.mod._find_feed(feeds, "blog a")
        self.assertIsNotNone(match)

    def test_find_feed_no_match(self):
        feeds = [{"url": "https://a.com/feed", "name": "Blog A"}]
        match = self.mod._find_feed(feeds, "Blog B")
        self.assertIsNone(match)


# ── Formatting Tests ────────────────────────────────────────────────────────
class TestFormatting(unittest.TestCase):

    def setUp(self):
        self.mod = _load_module()

    def test_truncate_short_text(self):
        self.assertEqual(self.mod._truncate("hello", 200), "hello")

    def test_truncate_long_text(self):
        text = "a" * 300
        result = self.mod._truncate(text, 200)
        self.assertEqual(len(result), 200)
        self.assertTrue(result.endswith("..."))

    def test_truncate_strips_html(self):
        result = self.mod._truncate("<p>Hello <b>world</b></p>")
        self.assertEqual(result, "Hello world")

    def test_relative_time_just_now(self):
        dt = datetime.now(timezone.utc)
        result = self.mod._relative_time(dt)
        self.assertEqual(result, "just now")

    def test_relative_time_hours(self):
        dt = datetime.now(timezone.utc) - timedelta(hours=3)
        result = self.mod._relative_time(dt)
        self.assertEqual(result, "3h ago")

    def test_format_entry_includes_title(self):
        entry = _make_entry(title="Big News")
        result = self.mod._format_entry(entry, 1)
        self.assertIn("Big News", result)
        self.assertIn("[1]", result)

    def test_format_entry_with_feed_name(self):
        entry = _make_entry(title="Article")
        result = self.mod._format_entry(entry, 1, feed_name="My Blog")
        self.assertIn("My Blog", result)


# ── Mocked Network Tests (add/fetch/fetch_all) ─────────────────────────────
class TestAddFeed(unittest.TestCase):

    def setUp(self):
        self.mod = _load_module()

    def test_add_feed_success(self):
        api = _make_api()
        feed_result = _make_feed_result(
            entries=[_make_entry()], title="My Blog"
        )
        with patch.object(self.mod, "_parse_feed", return_value=feed_result):
            result = self.mod._add_feed(api, "https://example.com/feed.xml", "")
        self.assertIn("Subscribed", result)
        self.assertIn("My Blog", result)
        api.set_config.assert_called_once()

    def test_add_feed_empty_url(self):
        api = _make_api()
        result = self.mod._add_feed(api, "", "")
        self.assertIn("Error", result)

    def test_add_feed_invalid_url(self):
        api = _make_api()
        result = self.mod._add_feed(api, "not-a-url", "")
        self.assertIn("Error", result)

    def test_add_feed_duplicate(self):
        api = _make_api(feeds='[{"url":"https://example.com/feed.xml","name":"X"}]')
        result = self.mod._add_feed(api, "https://example.com/feed.xml", "")
        self.assertIn("Already subscribed", result)

    def test_add_feed_bozo_no_entries(self):
        api = _make_api()
        feed_result = _make_feed_result(bozo=True, bozo_exception="parse error")
        with patch.object(self.mod, "_parse_feed", return_value=feed_result):
            result = self.mod._add_feed(api, "https://example.com/bad", "")
        self.assertIn("Error", result)

    def test_add_feed_with_custom_name(self):
        api = _make_api()
        feed_result = _make_feed_result(
            entries=[_make_entry()], title="Auto Name"
        )
        with patch.object(self.mod, "_parse_feed", return_value=feed_result):
            result = self.mod._add_feed(api, "https://example.com/feed.xml", "Custom Name")
        self.assertIn("Custom Name", result)


class TestRemoveFeed(unittest.TestCase):

    def setUp(self):
        self.mod = _load_module()

    def test_remove_existing(self):
        api = _make_api(feeds='[{"url":"https://a.com","name":"A"}]')
        result = self.mod._remove_feed(api, "A")
        self.assertIn("Unsubscribed", result)

    def test_remove_nonexistent(self):
        api = _make_api()
        result = self.mod._remove_feed(api, "Nope")
        self.assertIn("No feed found", result)

    def test_remove_empty_identifier(self):
        api = _make_api()
        result = self.mod._remove_feed(api, "")
        self.assertIn("Error", result)


class TestListFeeds(unittest.TestCase):

    def setUp(self):
        self.mod = _load_module()

    def test_list_empty(self):
        api = _make_api()
        result = self.mod._list_feeds(api)
        self.assertIn("No feeds subscribed", result)

    def test_list_with_feeds(self):
        api = _make_api(feeds='[{"url":"https://a.com","name":"Blog A"},{"url":"https://b.com","name":"Blog B"}]')
        result = self.mod._list_feeds(api)
        self.assertIn("Blog A", result)
        self.assertIn("Blog B", result)
        self.assertIn("2 subscribed", result)


class TestFetchFeed(unittest.TestCase):

    def setUp(self):
        self.mod = _load_module()

    def test_fetch_success(self):
        api = _make_api(feeds='[{"url":"https://a.com/feed","name":"Blog A"}]')
        entries = [_make_entry(title=f"Post {i}", minutes_ago=i * 10) for i in range(3)]
        feed_result = _make_feed_result(entries=entries, title="Blog A")
        with patch.object(self.mod, "_parse_feed", return_value=feed_result):
            result = self.mod._fetch_feed(api, "Blog A", 10)
        self.assertIn("Blog A", result)
        self.assertIn("Post 0", result)

    def test_fetch_empty_identifier(self):
        api = _make_api()
        result = self.mod._fetch_feed(api, "", 10)
        self.assertIn("Error", result)

    def test_fetch_not_found(self):
        api = _make_api()
        result = self.mod._fetch_feed(api, "NoSuchFeed", 10)
        self.assertIn("No feed found", result)

    def test_fetch_no_entries(self):
        api = _make_api(feeds='[{"url":"https://a.com/feed","name":"Blog A"}]')
        feed_result = _make_feed_result(entries=[], title="Blog A")
        with patch.object(self.mod, "_parse_feed", return_value=feed_result):
            result = self.mod._fetch_feed(api, "Blog A", 10)
        self.assertIn("No entries found", result)


class TestFetchAll(unittest.TestCase):

    def setUp(self):
        self.mod = _load_module()

    def test_fetch_all_no_feeds(self):
        api = _make_api()
        result = self.mod._fetch_all(api, 10)
        self.assertIn("No feeds subscribed", result)

    def test_fetch_all_success(self):
        api = _make_api(feeds=json.dumps([
            {"url": "https://a.com/feed", "name": "Blog A"},
            {"url": "https://b.com/feed", "name": "Blog B"},
        ]))
        entries_a = [_make_entry(title="A Post", minutes_ago=5)]
        entries_b = [_make_entry(title="B Post", minutes_ago=2)]

        def mock_parse(url):
            if "a.com" in url:
                return _make_feed_result(entries=entries_a, title="Blog A")
            return _make_feed_result(entries=entries_b, title="Blog B")

        with patch.object(self.mod, "_parse_feed", side_effect=mock_parse):
            result = self.mod._fetch_all(api, 10)
        self.assertIn("A Post", result)
        self.assertIn("B Post", result)
        self.assertIn("2 feeds", result)

    def test_fetch_all_partial_failure(self):
        api = _make_api(feeds=json.dumps([
            {"url": "https://a.com/feed", "name": "Blog A"},
            {"url": "https://bad.com/feed", "name": "Bad"},
        ]))
        entries_a = [_make_entry(title="Good Post")]

        def mock_parse(url):
            if "bad.com" in url:
                raise Exception("timeout")
            return _make_feed_result(entries=entries_a, title="Blog A")

        with patch.object(self.mod, "_parse_feed", side_effect=mock_parse):
            result = self.mod._fetch_all(api, 10)
        self.assertIn("Good Post", result)
        self.assertIn("Bad", result)


# ── Execute Integration Tests ───────────────────────────────────────────────
class TestExecute(unittest.TestCase):

    def setUp(self):
        self.mod = _load_module()

    def test_execute_list_empty(self):
        api = _make_api(default_count=10)
        tool = self.mod.RSSReaderTool(api)
        result = tool.execute("list_feeds")
        self.assertIn("No feeds subscribed", result)

    def test_execute_add_feed(self):
        api = _make_api(default_count=10)
        tool = self.mod.RSSReaderTool(api)
        feed_result = _make_feed_result(entries=[_make_entry()], title="Test")
        with patch.object(self.mod, "_parse_feed", return_value=feed_result):
            result = tool.execute("add_feed https://example.com/feed.xml")
        self.assertIn("Subscribed", result)

    def test_execute_unknown_action(self):
        api = _make_api(default_count=10)
        tool = self.mod.RSSReaderTool(api)
        result = tool.execute("explode 123")
        self.assertIn("Unknown command", result)

    def test_execute_fetch_all_empty(self):
        api = _make_api(default_count=10)
        tool = self.mod.RSSReaderTool(api)
        result = tool.execute("fetch_all")
        self.assertIn("No feeds subscribed", result)


# ── Skill Tests ─────────────────────────────────────────────────────────────
class TestSkill(unittest.TestCase):

    def test_skill_file_exists(self):
        skill_path = PLUGIN_DIR / "skills" / "SKILL.md"
        self.assertTrue(skill_path.exists(), "skills/SKILL.md missing")

    def test_skill_has_frontmatter(self):
        skill_path = PLUGIN_DIR / "skills" / "SKILL.md"
        text = skill_path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---"), "SKILL.md should start with YAML frontmatter")
        # Check for required frontmatter fields
        self.assertIn("name:", text)
        self.assertIn("description:", text)


if __name__ == "__main__":
    unittest.main()

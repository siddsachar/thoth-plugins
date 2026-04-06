"""Tests for thoth-hacker-news plugin."""

import json
import os
import pathlib
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure Thoth root is on path so `from plugins.api import ...` resolves.
# THOTH_ROOT env var can override; otherwise assume sibling directory layout.
PLUGIN_DIR = pathlib.Path(__file__).parent.parent
_thoth_root = os.environ.get("THOTH_ROOT")
if _thoth_root:
    THOTH_ROOT = pathlib.Path(_thoth_root)
else:
    # Try sibling: D:\Code\Thoth alongside D:\Code\thoth-plugins
    candidate = PLUGIN_DIR.parent.parent.parent / "Thoth"
    if (candidate / "plugins" / "api.py").exists():
        THOTH_ROOT = candidate
    else:
        # Fallback: assume thoth-plugins is inside Thoth
        THOTH_ROOT = PLUGIN_DIR.parent.parent.parent

if str(THOTH_ROOT) not in sys.path:
    sys.path.insert(0, str(THOTH_ROOT))


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
        self.assertEqual(self.manifest["id"], "thoth-hacker-news")

    def test_author(self):
        self.assertEqual(self.manifest["author"]["name"], "Thoth")
        self.assertEqual(self.manifest["author"]["github"], "siddsachar")

    def test_no_python_dependencies(self):
        self.assertEqual(self.manifest["python_dependencies"], [])

    def test_provides_one_tool(self):
        tools = self.manifest["provides"]["tools"]
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "hacker_news")

    def test_provides_one_skill(self):
        skills = self.manifest["provides"]["skills"]
        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0]["name"], "hacker_news_reader")


# ── Register Function Tests ─────────────────────────────────────────────────
class TestRegister(unittest.TestCase):

    def test_register_exists_and_callable(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "plugin_main", PLUGIN_DIR / "plugin_main.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(hasattr(module, "register"))
        self.assertTrue(callable(module.register))

    def test_register_registers_tool(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "plugin_main", PLUGIN_DIR / "plugin_main.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        mock_api = MagicMock()
        module.register(mock_api)
        mock_api.register_tool.assert_called_once()
        tool = mock_api.register_tool.call_args[0][0]
        self.assertEqual(tool.name, "hacker_news")
        self.assertEqual(tool.display_name, "📰 Hacker News")


# ── Query Parser Tests ──────────────────────────────────────────────────────
class TestQueryParser(unittest.TestCase):

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "plugin_main", PLUGIN_DIR / "plugin_main.py"
        )
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_empty_query_defaults_to_top_stories(self):
        action, params = self.module._parse_query("", 10)
        self.assertEqual(action, "top_stories")
        self.assertEqual(params["count"], 10)

    def test_top_stories_with_count(self):
        action, params = self.module._parse_query("top_stories 5", 10)
        self.assertEqual(action, "top_stories")
        self.assertEqual(params["count"], 5)

    def test_new_stories(self):
        action, params = self.module._parse_query("new_stories", 10)
        self.assertEqual(action, "new_stories")

    def test_search_query(self):
        action, params = self.module._parse_query("search rust programming", 10)
        self.assertEqual(action, "search")
        self.assertEqual(params["query"], "rust programming")
        self.assertEqual(params["count"], 10)

    def test_search_with_count(self):
        action, params = self.module._parse_query("search rust programming 5", 10)
        self.assertEqual(action, "search")
        self.assertEqual(params["query"], "rust programming")
        self.assertEqual(params["count"], 5)

    def test_story_detail(self):
        action, params = self.module._parse_query("story_detail 12345678", 10)
        self.assertEqual(action, "story_detail")
        self.assertEqual(params["story_id"], 12345678)

    def test_story_detail_with_comments(self):
        action, params = self.module._parse_query("story_detail 123 comments:3", 10)
        self.assertEqual(action, "story_detail")
        self.assertEqual(params["story_id"], 123)
        self.assertEqual(params["comment_count"], 3)

    def test_bare_text_treated_as_search(self):
        action, params = self.module._parse_query("what is new in AI", 10)
        self.assertEqual(action, "search")
        self.assertEqual(params["query"], "what is new in AI")

    def test_search_empty_returns_error(self):
        action, params = self.module._parse_query("search", 10)
        self.assertEqual(action, "error")

    def test_story_detail_no_id_returns_error(self):
        action, params = self.module._parse_query("story_detail", 10)
        self.assertEqual(action, "error")

    def test_count_clamped_to_max_30(self):
        action, params = self.module._parse_query("top_stories 100", 10)
        self.assertEqual(params["count"], 30)

    def test_count_clamped_to_min_1(self):
        action, params = self.module._parse_query("top_stories 0", 10)
        self.assertEqual(params["count"], 1)


# ── Formatting Tests ────────────────────────────────────────────────────────
class TestFormatting(unittest.TestCase):

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "plugin_main", PLUGIN_DIR / "plugin_main.py"
        )
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_format_story_with_url(self):
        item = {
            "title": "Test Story",
            "url": "https://example.com",
            "score": 42,
            "by": "testuser",
            "time": 1712345678,
            "descendants": 10,
            "id": 99999,
        }
        result = self.module._format_story(item, index=1)
        self.assertIn("[1] **Test Story**", result)
        self.assertIn("https://example.com", result)
        self.assertIn("42 points", result)
        self.assertIn("testuser", result)
        self.assertIn("https://news.ycombinator.com/item?id=99999", result)

    def test_format_story_without_url(self):
        item = {
            "title": "Ask HN: Something",
            "score": 10,
            "by": "author",
            "time": 1712345678,
            "descendants": 5,
            "id": 88888,
        }
        result = self.module._format_story(item, index=None)
        self.assertIn("**Ask HN: Something**", result)
        self.assertNotIn("[None]", result)

    def test_relative_time(self):
        import time
        now = int(time.time())
        self.assertEqual(self.module._relative_time(now - 30), "just now")
        self.assertEqual(self.module._relative_time(now - 120), "2m ago")
        self.assertEqual(self.module._relative_time(now - 7200), "2h ago")
        self.assertEqual(self.module._relative_time(now - 172800), "2d ago")
        self.assertEqual(self.module._relative_time(None), "")


# ── Network Tests (mocked) ──────────────────────────────────────────────────
class TestNetworkMocked(unittest.TestCase):

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "plugin_main", PLUGIN_DIR / "plugin_main.py"
        )
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_fetch_stories_formats_correctly(self):
        """Test story fetching with mocked HTTP."""
        mock_items = {
            1001: {"id": 1001, "type": "story", "title": "Test A",
                   "score": 100, "by": "alice", "time": 1712345678,
                   "descendants": 20, "url": "https://a.com"},
            1002: {"id": 1002, "type": "story", "title": "Test B",
                   "score": 50, "by": "bob", "time": 1712345600,
                   "descendants": 5},
        }

        def mock_fetch(url):
            if "topstories" in url:
                return [1001, 1002]
            for item_id, item in mock_items.items():
                if str(item_id) in url:
                    return item
            return None

        with patch.object(self.module, "_fetch_json", side_effect=mock_fetch):
            result = self.module._fetch_stories("topstories", 2)
            self.assertIn("Test A", result)
            self.assertIn("Test B", result)
            self.assertIn("100 points", result)

    def test_search_no_results(self):
        """Algolia returning empty hits."""
        with patch.object(self.module, "_fetch_json",
                          return_value={"hits": []}):
            result = self.module._search_hn("nonexistent_query_xyz", 10)
            self.assertIn("No Hacker News results", result)

    def test_story_detail_not_found(self):
        """Non-existent story ID."""
        with patch.object(self.module, "_fetch_item", return_value=None):
            result = self.module._story_detail(99999999)
            self.assertIn("Could not find", result)

    def test_story_detail_wrong_type(self):
        """Item exists but is a comment, not a story."""
        with patch.object(self.module, "_fetch_item",
                          return_value={"type": "comment", "id": 123}):
            result = self.module._story_detail(123)
            self.assertIn("comment", result)
            self.assertIn("not a story", result)


# ── Execute Integration Tests (mocked) ──────────────────────────────────────
class TestExecute(unittest.TestCase):

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "plugin_main", PLUGIN_DIR / "plugin_main.py"
        )
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

        self.mock_api = MagicMock()
        self.mock_api.get_config.return_value = 10
        self.tool = self.module.HackerNewsTool(self.mock_api)

    def test_execute_network_error(self):
        """Network failure returns friendly error."""
        import urllib.error
        with patch.object(self.module, "_fetch_json",
                          side_effect=urllib.error.URLError("timeout")):
            result = self.tool.execute("top_stories 3")
            self.assertIn("Network error", result)

    def test_execute_unknown_exception(self):
        """Unexpected error is caught gracefully."""
        with patch.object(self.module, "_fetch_json",
                          side_effect=RuntimeError("bad")):
            result = self.tool.execute("top_stories")
            self.assertIn("Error fetching", result)

    def test_execute_empty_query(self):
        """Empty query defaults to top_stories."""
        with patch.object(self.module, "_fetch_stories",
                          return_value="mocked") as mock:
            result = self.tool.execute("")
            mock.assert_called_once_with("topstories", 10)

    def test_execute_respects_config(self):
        """Default count comes from plugin config."""
        self.mock_api.get_config.return_value = 5
        tool = self.module.HackerNewsTool(self.mock_api)
        with patch.object(self.module, "_fetch_stories",
                          return_value="mocked") as mock:
            tool.execute("top_stories")
            mock.assert_called_once_with("topstories", 5)


# ── Skill File Tests ────────────────────────────────────────────────────────
class TestSkill(unittest.TestCase):

    def test_skill_file_exists(self):
        skill_path = PLUGIN_DIR / "skills" / "SKILL.md"
        self.assertTrue(skill_path.exists(), "skills/SKILL.md missing")

    def test_skill_has_frontmatter(self):
        skill_path = PLUGIN_DIR / "skills" / "SKILL.md"
        content = skill_path.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---"), "SKILL.md missing YAML frontmatter")
        parts = content.split("---", 2)
        self.assertGreaterEqual(len(parts), 3, "Invalid frontmatter structure")
        self.assertIn("display_name:", parts[1])


if __name__ == "__main__":
    unittest.main(verbosity=2)

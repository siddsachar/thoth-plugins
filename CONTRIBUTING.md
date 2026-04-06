# Contributing to Thoth Plugins

Thank you for your interest in building a plugin for Thoth! This guide walks you through the entire process — from setting up your environment to getting your plugin merged and available in the marketplace.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Environment Setup](#environment-setup)
3. [Plugin Structure](#plugin-structure)
4. [Step-by-Step: Creating a Plugin](#step-by-step-creating-a-plugin)
5. [Plugin Manifest Reference](#plugin-manifest-reference)
6. [PluginTool API Reference](#plugintool-api-reference)
7. [PluginAPI Methods Reference](#pluginapi-methods-reference)
8. [Adding Skills](#adding-skills)
9. [Testing Your Plugin Locally](#testing-your-plugin-locally)
10. [Submitting Your Plugin](#submitting-your-plugin)
11. [What CI Checks](#what-ci-checks)
12. [What Reviewers Look For](#what-reviewers-look-for)
13. [Common Mistakes](#common-mistakes)
14. [FAQ](#faq)

---

## Quick Start

```bash
# 1. Fork this repo on GitHub, then clone your fork
git clone https://github.com/YOUR-USERNAME/thoth-plugins.git
cd thoth-plugins

# 2. Copy the template
cp -r template/ plugins/my-plugin/

# 3. Edit your plugin files
#    - plugins/my-plugin/plugin.json    (metadata)
#    - plugins/my-plugin/plugin_main.py (tools + register function)
#    - plugins/my-plugin/README.md      (documentation)

# 4. Test locally (see "Testing Your Plugin Locally" section)

# 5. Commit and push
git checkout -b add-my-plugin
git add plugins/my-plugin/
git commit -m "Add my-plugin v1.0.0"
git push origin add-my-plugin

# 6. Open a PR to main
```

---

## Environment Setup

### Prerequisites

- Python 3.11 or higher (Thoth bundles Python 3.13)
- Git
- A running instance of Thoth (for local testing)

### Development Setup

```bash
# Clone the plugins repo
git clone https://github.com/YOUR-USERNAME/thoth-plugins.git
cd thoth-plugins

# (Optional) Create a virtual environment for testing
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
```

---

## Plugin Structure

Every plugin lives in its own directory under `plugins/`:

```
plugins/my-plugin/
├── plugin.json        # Required — plugin manifest
├── plugin_main.py     # Required — entry point with register()
├── README.md          # Required — documentation
├── LICENSE            # Required — OSI-approved license
├── requirements.txt   # Optional — Python dependencies
├── skills/            # Optional — SKILL.md files
│   └── SKILL.md
├── tests/             # Optional — test suite
│   └── test_plugin.py
└── CHANGELOG.md       # Optional — version history
```

---

## Step-by-Step: Creating a Plugin

### Step 1: Plan Your Plugin

Before writing code, decide:
- **Plugin ID**: lowercase with hyphens (e.g., `weather-alerts`, `crm-tools`)
- **Tools**: What operations will the agent be able to perform?
- **Skills**: Any step-by-step workflows?
- **API keys**: Does the plugin need external API credentials?
- **Dependencies**: Any Python packages required?

### Step 2: Copy the Template

```bash
cp -r template/ plugins/your-plugin-id/
```

### Step 3: Edit plugin.json

Open `plugins/your-plugin-id/plugin.json` and fill in your metadata:

```json
{
  "id": "weather-alerts",
  "name": "Weather Alerts",
  "version": "1.0.0",
  "min_thoth_version": "3.12.0",
  "author": {
    "name": "Jane Smith",
    "github": "janesmith"
  },
  "description": "Real-time weather alerts and forecasts.",
  "icon": "🌦️",
  "license": "Apache-2.0",
  "tags": ["weather", "alerts", "utility"],

  "provides": {
    "tools": [
      {
        "name": "get_weather",
        "display_name": "Get Weather",
        "description": "Get current weather for a location"
      }
    ],
    "skills": []
  },

  "settings": {
    "api_keys": {
      "WEATHER_API_KEY": {
        "label": "Weather API Key",
        "required": true,
        "placeholder": "your-api-key-here"
      }
    },
    "config": {
      "units": {
        "label": "Temperature Units",
        "type": "select",
        "options": ["celsius", "fahrenheit"],
        "default": "celsius"
      }
    }
  },

  "python_dependencies": [
    "requests>=2.28"
  ]
}
```

### Step 4: Implement Your Tools

Edit `plugin_main.py`:

```python
"""Weather Alerts plugin for Thoth."""

from plugins.api import PluginAPI, PluginTool


class GetWeather(PluginTool):
    """Get current weather for a location."""

    @property
    def name(self) -> str:
        return "get_weather"

    @property
    def display_name(self) -> str:
        return "🌦️ Get Weather"

    @property
    def description(self) -> str:
        return (
            "Get the current weather for a given location. "
            "Provide a city name or coordinates."
        )

    def execute(self, query: str) -> str:
        api_key = self.plugin_api.get_secret("WEATHER_API_KEY")
        if not api_key:
            return (
                "Error: Weather API key not configured. "
                "Go to Settings → Plugins → Weather Alerts to add it."
            )

        units = self.plugin_api.get_config("units", "celsius")

        try:
            import requests
            resp = requests.get(
                "https://api.weatherapi.com/v1/current.json",
                params={"key": api_key, "q": query},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            location = data["location"]["name"]
            temp = data["current"]["temp_c" if units == "celsius" else "temp_f"]
            unit_symbol = "°C" if units == "celsius" else "°F"
            condition = data["current"]["condition"]["text"]

            return f"Weather in {location}: {temp}{unit_symbol}, {condition}"

        except requests.RequestException as exc:
            return f"Error fetching weather: {exc}"
        except (KeyError, ValueError) as exc:
            return f"Error parsing weather data: {exc}"


def register(api: PluginAPI):
    """Called by Thoth on startup."""
    api.register_tool(GetWeather(api))
```

### Step 5: Write Tests

Create `tests/test_plugin.py`:

```python
"""Tests for weather-alerts plugin."""

import json
import pathlib


def test_manifest():
    manifest_path = pathlib.Path(__file__).parent.parent / "plugin.json"
    with open(manifest_path) as f:
        data = json.load(f)
    assert data["id"] == "weather-alerts"
    assert data["version"] == "1.0.0"


def test_register():
    import importlib.util
    main_path = pathlib.Path(__file__).parent.parent / "plugin_main.py"
    spec = importlib.util.spec_from_file_location("plugin_main", main_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "register")


if __name__ == "__main__":
    test_manifest()
    test_register()
    print("All tests passed!")
```

### Step 6: Update README.md

Document your plugin with usage examples and setup instructions.

### Step 7: Test Locally

See the [Testing Your Plugin Locally](#testing-your-plugin-locally) section below.

---

## Plugin Manifest Reference

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique lowercase ID with hyphens, 2-64 chars (e.g., `crm-tools`) |
| `name` | string | Human-readable name (e.g., "CRM Tools") |
| `version` | string | Semantic version: `MAJOR.MINOR.PATCH` (e.g., `1.2.0`) |
| `min_thoth_version` | string | Minimum Thoth version required (e.g., `3.12.0`) |
| `author` | object | `{"name": "...", "github": "..."}` |
| `description` | string | One-line description |

### Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `long_description` | string | `""` | Longer markdown description for marketplace |
| `icon` | string | `"🔌"` | Emoji icon |
| `license` | string | `"Apache-2.0"` | License identifier |
| `tags` | string[] | `[]` | Search tags |
| `homepage` | string | `""` | Project homepage URL |
| `repository` | string | `""` | Source code URL |
| `provides` | object | `{}` | Tools and skills listing |
| `settings` | object | `{}` | API keys and config schema |
| `python_dependencies` | string[] | `[]` | pip requirements |

### Settings Schema

```json
{
  "settings": {
    "api_keys": {
      "KEY_NAME": {
        "label": "Human-readable label",
        "required": true,
        "placeholder": "Hint text"
      }
    },
    "config": {
      "setting_name": {
        "label": "Human-readable label",
        "type": "text|number|select|boolean",
        "options": ["a", "b"],
        "default": "a",
        "min": 1,
        "max": 100
      }
    }
  }
}
```

---

## PluginTool API Reference

Subclass `PluginTool` for each tool your plugin provides:

```python
from plugins.api import PluginAPI, PluginTool

class MyTool(PluginTool):
    def __init__(self, plugin_api: PluginAPI):
        super().__init__(plugin_api)
        # self.plugin_api is available for config/secrets

    @property
    def name(self) -> str:
        """Internal unique identifier. Lowercase with underscores."""
        return "my_tool"

    @property
    def display_name(self) -> str:
        """Human-readable label. Include an emoji."""
        return "🔧 My Tool"

    @property
    def description(self) -> str:
        """One-line description for the AI agent.
        Be specific about what input the tool expects."""
        return "Do X with Y. Provide a query string."

    def execute(self, query: str) -> str:
        """Run the tool. Must return a string.
        Handle errors gracefully — return error messages, don't raise."""
        try:
            # Your logic here
            return "Result text"
        except Exception as exc:
            return f"Error: {exc}"
```

### Writing Good Tool Descriptions

The AI agent uses the `description` to decide when to call your tool. Good descriptions:

- ✅ "Search HubSpot CRM for contacts, deals, and companies by name or email"
- ✅ "Get the current weather forecast for a given city or coordinates"
- ❌ "A weather tool" (too vague)
- ❌ "This tool interfaces with the OpenWeatherMap API" (sounds like documentation, not instructions)

---

## PluginAPI Methods Reference

The `PluginAPI` object is passed to your `register()` function and stored as `self.plugin_api` on every `PluginTool`:

| Method | Description |
|--------|-------------|
| `api.plugin_id` | Your plugin's ID string |
| `api.plugin_dir` | Path to your plugin's installed directory |
| `api.register_tool(tool)` | Register a `PluginTool` instance |
| `api.register_skill(info)` | Register a skill dict (usually auto-discovered) |
| `api.get_config(key, default)` | Read a config value |
| `api.set_config(key, value)` | Write a config value |
| `api.get_secret(key)` | Read an API key (returns `None` if not set) |
| `api.set_secret(key, value)` | Write an API key |

### Important Rules

- **Never** read API keys from `os.environ` — always use `api.get_secret()`
- **Never** read config from files directly — always use `api.get_config()`
- You **can** read/write files inside `api.plugin_dir` for plugin-local data

---

## Adding Skills

Skills are YAML-frontmatter markdown files in your `skills/` directory:

```markdown
---
name: weather_briefing
display_name: Weather Briefing
icon: "🌦️"
description: Generate a daily weather briefing for the user's location.
tags:
  - weather
  - daily
---

# Weather Briefing

You are using the Weather Briefing skill. Follow these steps:

1. Ask the user for their location if not already known
2. Use the `get_weather` tool to fetch current conditions
3. Use the `get_forecast` tool to fetch the 3-day forecast
4. Present a concise briefing with:
   - Current conditions
   - Today's high/low
   - 3-day outlook
   - Any weather alerts

## Style Guidelines
- Use weather emojis (☀️ 🌧️ ❄️ ⛈️)
- Be concise but informative
- Suggest relevant actions (e.g., "bring an umbrella")
```

Skills are auto-discovered from the `skills/` directory — no registration needed.

---

## Testing Your Plugin Locally

### Method 1: Symlink for Development (Recommended)

Create a symlink from Thoth's plugin directory to your working copy. This lets you edit code in place and reload without copying files each time.

```bash
# macOS/Linux:
ln -s "$(pwd)/plugins/your-plugin" ~/.thoth/installed_plugins/your-plugin

# Windows (run as Administrator):
mklink /D "%USERPROFILE%\.thoth\installed_plugins\your-plugin" "%CD%\plugins\your-plugin"
```

After making changes, go to **Settings → Plugins** and click **"Reload Plugins"** — no restart needed. The plugin loader follows symlinks automatically.

> **Tip:** Remove the symlink when you're done developing — don't leave symlinks in the installed directory for day-to-day use.

### Method 2: Copy for Final Testing

If you want to test exactly what users will get (a standalone copy), copy the files instead:

```bash
# macOS/Linux:
cp -r plugins/your-plugin/ ~/.thoth/installed_plugins/your-plugin/

# Windows:
xcopy /E /I plugins\your-plugin\ %USERPROFILE%\.thoth\installed_plugins\your-plugin\
```

Then go to **Settings → Plugins** and click **"Reload Plugins"** (or restart Thoth).

Check the logs for:
```
✅ Plugin 'your-plugin' v1.0.0 loaded (1 tools, 0 skills)
```

### Method 3: Run Validation Script

```bash
python scripts/validate_plugin.py plugins/your-plugin/
```

### Method 4: Run Your Tests

```bash
cd plugins/your-plugin
python -m pytest tests/ -v
```

### Verifying in Thoth

1. Launch Thoth
2. Go to **Settings → Plugins**
3. Verify your plugin card appears with correct name, description, tool/skill counts
4. Click your plugin card and configure any API keys
5. In chat, ask the agent to use your tool
6. Toggle the plugin off/on and verify it stops/starts working
7. Check that Thoth still functions normally with your plugin enabled

---

## Submitting Your Plugin

### Step 1: Create a Branch

```bash
git checkout -b add-your-plugin
```

### Step 2: Add Your Plugin Files

```bash
git add plugins/your-plugin/
git commit -m "Add your-plugin v1.0.0"
git push origin add-your-plugin
```

### Step 3: Open a PR

Go to the thoth-plugins repo on GitHub and open a Pull Request to `main`.

**PR Title Format**: `Add <plugin-name> v<version>` (e.g., "Add weather-alerts v1.0.0")

**PR Description Template**:
```markdown
## New Plugin: <Plugin Name>

**Plugin ID**: `your-plugin-id`
**Version**: 1.0.0
**Description**: Brief description

### Tools
- `tool_name` — what it does

### Skills
- (none / list them)

### Dependencies
- (none / list them)

### Testing
- [ ] Validated with `scripts/validate_plugin.py`
- [ ] Tested locally in Thoth
- [ ] All tools work correctly
- [ ] Enable/disable toggle works
- [ ] No core functionality broken
```

### Step 4: Wait for CI + Review

- CI will automatically validate your plugin
- A maintainer will review the code
- You may be asked to make changes
- Once approved, it will be merged and appear in the marketplace

---

## What CI Checks

When you open a PR, the CI pipeline automatically:

1. **Manifest validation**: plugin.json has all required fields, valid ID, valid semver
2. **Entry point check**: plugin_main.py exists with a `register()` function
3. **Security scan**: No `eval()`, `exec()`, `os.system()`, `subprocess`, or `__import__()`
4. **Import guard**: No imports from Thoth core modules (`tools`, `agent`, `app`, `ui`, etc.)
5. **Dependency check**: Plugin deps don't conflict with Thoth core requirements
6. **Plugin tests**: Runs your `tests/` if present

---

## What Reviewers Look For

Beyond CI checks, human reviewers will evaluate:

- **Code quality**: Clean, readable, idiomatic Python
- **Error handling**: Tools return error messages instead of crashing
- **Description quality**: Tool descriptions are clear and useful for the AI agent
- **Documentation**: README has setup instructions and usage examples
- **No side effects**: Plugin doesn't modify files outside its own directory
- **Privacy**: Plugin doesn't send data to unexpected endpoints
- **License**: Valid OSI-approved license included

---

## Common Mistakes

### 1. Importing core modules
```python
# ❌ Wrong — this will be blocked
from tools.base import BaseTool

# ✅ Correct
from plugins.api import PluginTool
```

### 2. Reading environment variables directly
```python
# ❌ Wrong
api_key = os.environ.get("MY_API_KEY")

# ✅ Correct
api_key = self.plugin_api.get_secret("MY_API_KEY")
```

### 3. Raising exceptions in execute()
```python
# ❌ Wrong — will show as "Plugin tool error" to user
def execute(self, query: str) -> str:
    resp = requests.get(url)
    resp.raise_for_status()  # raises on HTTP error
    return resp.json()["data"]

# ✅ Correct
def execute(self, query: str) -> str:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()["data"]
    except requests.RequestException as exc:
        return f"Error: Could not reach API: {exc}"
    except (KeyError, ValueError):
        return "Error: Unexpected response format"
```

### 4. Vague tool descriptions
```python
# ❌ Too vague — agent won't know when to use it
@property
def description(self) -> str:
    return "A tool for weather"

# ✅ Specific — agent knows exactly what this does and what input to provide
@property
def description(self) -> str:
    return "Get the current weather and 3-day forecast for a city name or ZIP code"
```

### 5. Not specifying min_thoth_version
```json
// ❌ Missing
{}

// ✅ Always specify
{"min_thoth_version": "3.12.0"}
```

---

## FAQ

**Q: Can I use any Python package?**
A: Yes, as long as it doesn't conflict with Thoth's core dependencies. Declare all dependencies in both `plugin.json` and `requirements.txt`.

**Q: How do I store data locally?**
A: Use `self.plugin_api.plugin_dir` to get your plugin's directory path. You can read/write files there.

**Q: Can my plugin have multiple tools?**
A: Yes! Register as many tools as you want in your `register()` function.

**Q: How do I update my plugin?**
A: Bump the `version` in `plugin.json`, make your changes, and open a new PR.

**Q: Can I use async/await?**
A: Tool `execute()` methods are synchronous. For async operations, use `asyncio.run()` or blocking calls with timeouts.

**Q: What happens if my plugin crashes?**
A: Thoth catches all plugin errors. If `register()` crashes, the plugin is marked as failed. If a tool's `execute()` crashes, a friendly error message is shown to the user.

**Q: How are secrets stored?**
A: Secrets are stored in `~/.thoth/plugin_secrets.json` with restricted file permissions (0600 on Unix). They are never sent anywhere except when your tool explicitly uses them.

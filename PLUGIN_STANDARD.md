# Plugin Coding Standard

All plugins submitted to the Thoth marketplace must follow these rules.

## Required Files

| File | Purpose |
|------|---------|
| `plugin.json` | Plugin manifest (metadata, dependencies, settings) |
| `plugin_main.py` | Entry point with `register(api)` function |
| `README.md` | Description, setup instructions, usage examples |
| `LICENSE` | OSI-approved license (Apache-2.0 recommended) |

## Optional Files

| File / Directory | Purpose |
|------------------|---------|
| `requirements.txt` | Python dependencies |
| `skills/` | SKILL.md files for agent workflows |
| `tests/` | Plugin test suite |
| `CHANGELOG.md` | Version history |

## Code Rules

1. **Entry point**: `plugin_main.py` must contain a `register(api: PluginAPI)` function
2. **Tool base class**: All tools must subclass `PluginTool` from `plugins.api`
3. **Skill format**: Skills must use SKILL.md with YAML frontmatter
4. **No core imports**: Plugins must NOT import from `tools/`, `ui/`, `agent.py`, `app.py`, `models.py`, `prompts.py`, or any other core module
5. **Filesystem boundary**: Plugins must NOT access files outside `~/.thoth/installed_plugins/<id>/`
6. **No dangerous calls**: Plugins must NOT use `os.system()`, `eval()`, `exec()`, `subprocess`, or `__import__()`
7. **No global mutation**: Plugins must NOT modify global state or monkey-patch
8. **Secrets via API**: All API keys must be accessed via `api.get_secret()`, never `os.environ`
9. **Config via API**: All configuration must be accessed via `api.get_config()`, never direct file I/O
10. **Graceful errors**: Tools must handle errors and return error messages, never raise unhandled exceptions
11. **Clear descriptions**: Tool descriptions must be clear and agent-friendly
12. **Declare dependencies**: All Python dependencies must be listed in both `plugin.json` and `requirements.txt`
13. **Minimum version**: `min_thoth_version` must be specified in `plugin.json`

## Naming Conventions

| Entity | Format | Example |
|--------|--------|---------|
| Plugin ID | lowercase, hyphens | `crm-tools` |
| Tool name | lowercase, underscores | `hubspot_lookup` |
| Skill name | lowercase, underscores | `crm_outreach` |

Name collisions with built-in Thoth tools are detected at load time and cause the conflicting tool to be skipped.

## Security Enforcement

These rules are enforced by:
- **CI validation** on every PR (automated scan)
- **Runtime loader** security scan on plugin installation
- **Manual review** by plugin maintainers before merge

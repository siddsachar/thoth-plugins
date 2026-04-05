# Thoth Plugins

The official plugin marketplace for [Thoth](https://github.com/siddsachar/Thoth) — a local AI assistant.

## What Are Plugins?

Plugins extend Thoth with new **tools** and **skills** without modifying the core application:

- **Tools** give the agent new capabilities (search CRM records, control smart home devices, query APIs)
- **Skills** teach the agent step-by-step workflows using plugin tools

## For Users

### Installing Plugins

1. Open Thoth → **Settings → Plugins**
2. Click **Browse Marketplace**
3. Find a plugin and click **Install**
4. Configure any required API keys
5. The plugin is ready to use immediately

### Managing Plugins

- **Enable/Disable**: Toggle the switch on each plugin card in Settings → Plugins
- **Configure**: Click a plugin card to set API keys and options
- **Update**: Update notifications appear when newer versions are available
- **Uninstall**: Click Configure → Uninstall to remove a plugin completely

## For Plugin Authors

Want to create a plugin? See [CONTRIBUTING.md](CONTRIBUTING.md) for a complete guide.

Quick start:
1. Fork this repo
2. Copy `template/` to `plugins/your-plugin-id/`
3. Edit `plugin.json`, `plugin_main.py`, and add your tools
4. Test locally
5. Open a PR

## Repository Structure

```
thoth-plugins/
├── index.json           # Auto-generated plugin catalog
├── template/            # Starter template for new plugins
├── scripts/             # CI validation scripts
├── .github/workflows/   # CI automation
└── plugins/             # All plugins live here
    ├── crm-tools/
    ├── notion-sync/
    └── ...
```

## Standards

All plugins must follow the [Plugin Standard](PLUGIN_STANDARD.md):
- Use `PluginTool` base class from `plugins.api`
- Include a valid `plugin.json` manifest
- No `eval()`, `exec()`, `subprocess`, or `os.system()`
- No imports from Thoth core modules
- Handle errors gracefully
- Provide clear tool descriptions

## License

MIT — see [LICENSE](LICENSE) for details.

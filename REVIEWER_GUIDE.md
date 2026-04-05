# Plugin Reviewer Guide

This guide is for maintainers who review plugin Pull Requests. It provides a checklist-driven process for validating plugins before they are merged into the marketplace.

## Table of Contents

1. [Pre-Review Checklist (Automated)](#pre-review-checklist-automated)
2. [Code Review Checklist](#code-review-checklist)
3. [Manual Testing Steps](#manual-testing-steps)
4. [Approval Criteria](#approval-criteria)
5. [Merge Process](#merge-process)
6. [Handling Issues](#handling-issues)

---

## Pre-Review Checklist (Automated)

Before starting your review, verify that CI has passed:

- [ ] **CI status is green** — the `validate-pr` check passed
- [ ] **Manifest valid** — plugin.json has all required fields
- [ ] **Security scan passed** — no eval/exec/subprocess/os.system
- [ ] **Import guard passed** — no core module imports
- [ ] **Dependency check passed** — no conflicts with Thoth core
- [ ] **Plugin tests passed** (if present)

> If CI is red, ask the author to fix the issues before reviewing.

---

## Code Review Checklist

Review the plugin files with these criteria:

### plugin.json
- [ ] `id` matches the directory name (e.g., `plugins/weather-alerts/` has `"id": "weather-alerts"`)
- [ ] `version` is valid semver (x.y.z)
- [ ] `min_thoth_version` is set and reasonable (currently `3.12.0`)
- [ ] `description` is clear and concise (one sentence)
- [ ] `author` has a name
- [ ] `provides.tools` lists all tools with correct names
- [ ] `settings.api_keys` documents all required API keys
- [ ] `python_dependencies` matches `requirements.txt` (if present)

### plugin_main.py
- [ ] Has a `register(api: PluginAPI)` function
- [ ] All tools subclass `PluginTool` from `plugins.api`
- [ ] Tool `name` properties match those listed in `plugin.json`
- [ ] Tool `description` properties are agent-friendly (clear input expectations)
- [ ] `execute()` methods handle errors gracefully (return error strings, don't raise)
- [ ] API keys accessed only via `self.plugin_api.get_secret()`
- [ ] Config accessed only via `self.plugin_api.get_config()`
- [ ] No hardcoded credentials or tokens
- [ ] HTTP requests use timeouts
- [ ] No file access outside the plugin directory

### Security Red Flags
- [ ] No obfuscated code
- [ ] No network calls to unexpected endpoints
- [ ] No data exfiltration patterns (sending secrets or user data somewhere)
- [ ] No attempts to modify Thoth configuration
- [ ] No `open()` calls to files outside `api.plugin_dir`

### Documentation
- [ ] README.md exists with setup instructions
- [ ] README includes usage examples
- [ ] LICENSE file exists (OSI-approved)

---

## Manual Testing Steps

For every plugin PR, perform these steps in a live Thoth instance:

### Setup

```bash
# 1. Pull the PR branch
git fetch origin pull/NUMBER/head:pr-NUMBER
git checkout pr-NUMBER

# 2. Copy the plugin to Thoth's plugins directory
# macOS/Linux:
cp -r plugins/PLUGIN-ID/ ~/.thoth/installed_plugins/PLUGIN-ID/

# Windows:
xcopy /E /I plugins\PLUGIN-ID\ %USERPROFILE%\.thoth\installed_plugins\PLUGIN-ID\
```

### Test Sequence

Perform each step and check the box:

#### Step 1: Plugin Loading
- [ ] Launch Thoth
- [ ] Check the terminal/logs for: `✅ Plugin 'PLUGIN-ID' vX.Y.Z loaded`
- [ ] No error messages related to the plugin in the logs

#### Step 2: Settings UI
- [ ] Open **Settings → Plugins**
- [ ] Plugin card appears with correct:
  - [ ] Name and icon
  - [ ] Description
  - [ ] Version number
  - [ ] Tool count badge
  - [ ] Skill count badge (if applicable)
- [ ] Enable/disable toggle works
  - [ ] Toggle OFF → plugin tools stop appearing in agent responses
  - [ ] Toggle ON → plugin tools start working again

#### Step 3: Plugin Configuration
- [ ] Click the plugin card → **Configure** button
- [ ] Plugin dialog opens with correct:
  - [ ] Plugin name and version
  - [ ] Author info
  - [ ] Description
  - [ ] API key fields (if any)
  - [ ] Config settings (if any)
  - [ ] Tools list
  - [ ] Skills list (if any)
- [ ] Enter API key(s) and click **Save**
- [ ] Close and reopen Settings → Plugins → Configure — keys are persisted
- [ ] API key field shows masked value (password dots)

#### Step 4: Tool Testing
For each tool the plugin provides:
- [ ] Ask the agent to use the tool in chat
- [ ] Tool executes and returns a reasonable result
- [ ] If API key is missing, tool returns a helpful error (not a crash)
- [ ] If API returns an error, tool handles it gracefully

Example prompts to test:
```
Use the [tool_name] to [expected action]
Can you [natural language description of what the tool does]?
```

#### Step 5: Error Handling
- [ ] Remove the API key(s) from plugin settings
- [ ] Ask the agent to use the tool — should get a clear error message
- [ ] Re-add the API key — tool should work again

#### Step 6: Skills (if applicable)
- [ ] Verify plugin skills appear in the system
- [ ] Test a skill invocation via chat

#### Step 7: Core Functionality
- [ ] Regular chat (without plugin tools) still works
- [ ] Built-in tools (web search, file system, etc.) still work
- [ ] No error messages in logs unrelated to the plugin

#### Step 8: Cleanup
- [ ] Uninstall the plugin:
  - Settings → Plugins → Configure → **Uninstall**
  - OR manually delete `~/.thoth/installed_plugins/PLUGIN-ID/`
- [ ] Restart Thoth
- [ ] Verify the plugin is gone from Settings → Plugins
- [ ] Verify Thoth core works normally after uninstall

---

## Approval Criteria

A plugin should be **approved** when:

1. ✅ CI is green (all automated checks passed)
2. ✅ Code review checklist complete (no security concerns)
3. ✅ Manual testing steps all pass
4. ✅ Plugin does what its description claims
5. ✅ No negative impact on Thoth core functionality
6. ✅ Documentation is adequate

A plugin should be **requested changes** when:

- ⚠️ Tools have poor descriptions (agent can't figure out when to use them)
- ⚠️ Error handling is missing (tools crash instead of returning error messages)
- ⚠️ Missing README/LICENSE
- ⚠️ API keys are hardcoded
- ⚠️ Unnecessary dependencies

A plugin should be **rejected** when:

- ❌ Contains malicious code
- ❌ Attempts to access core Thoth internals
- ❌ Exfiltrates user data
- ❌ Contains obfuscated code
- ❌ Author refuses to address security concerns

---

## Merge Process

1. **Verify** all checks above are complete
2. **Approve** the PR on GitHub
3. **Merge** using "Squash and merge" with format: `Add PLUGIN-ID vX.Y.Z (#PR_NUMBER)`
4. **Verify** the `rebuild-index` workflow runs and updates `index.json`
5. **Spot-check** the updated `index.json` includes the new plugin

After merge, the plugin is immediately available in the Thoth marketplace.

---

## Handling Issues

### Author Needs Help
- Point them to [CONTRIBUTING.md](CONTRIBUTING.md)
- Suggest specific fixes rather than vague feedback
- If their `execute()` error handling is weak, provide a code example

### Plugin Conflicts
- If two plugins register the same tool name, the second one is automatically skipped
- Inform both authors and ask one to rename their tool

### Dependency Concerns
- If a plugin requires a package that's close to a core dependency version, test carefully
- When in doubt, ask the author to pin their dependency to a compatible version

### Post-Merge Issues
- If a merged plugin causes problems, create an issue
- For urgent issues, revert the merge commit and notify the author
- The `index.json` will auto-rebuild on revert, removing the plugin from the marketplace

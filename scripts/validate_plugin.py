#!/usr/bin/env python3
"""Validate a plugin directory.

Usage:
    python scripts/validate_plugin.py plugins/my-plugin/

Checks:
  1. plugin.json exists and has required fields
  2. plugin_main.py exists with register() function
  3. Security scan (no eval/exec/os.system/subprocess/__import__)
  4. No forbidden core imports
  5. README.md and LICENSE exist

Exit codes:
  0 = pass
  1 = validation errors found
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────────
_ID_RE = re.compile(r"^[a-z][a-z0-9\-]{1,63}$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

_DANGEROUS_PATTERNS = [
    re.compile(r"\beval\s*\("),
    re.compile(r"\bexec\s*\("),
    re.compile(r"\bos\.system\s*\("),
    re.compile(r"\bsubprocess\b"),
    re.compile(r"\b__import__\s*\("),
]

_FORBIDDEN_IMPORTS = {
    "tools", "tools.base", "tools.registry",
    "agent", "app", "models", "prompts",
    "knowledge_graph", "memory_extraction", "dream_cycle",
    "threads", "tasks", "documents",
    "ui", "ui.settings", "ui.streaming", "ui.chat",
    "ui.render", "ui.helpers", "ui.home",
}


def validate(plugin_dir: Path) -> list[str]:
    """Return a list of error strings. Empty = pass."""
    errors: list[str] = []

    # 1. plugin.json
    manifest_path = plugin_dir / "plugin.json"
    if not manifest_path.exists():
        errors.append("Missing plugin.json")
        return errors  # Can't continue without manifest

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid JSON in plugin.json: {exc}")
        return errors

    # Required fields
    for field in ("id", "name", "version", "min_thoth_version", "author", "description"):
        if field not in manifest:
            errors.append(f"Missing required field '{field}' in plugin.json")

    pid = manifest.get("id", "")
    if pid and not _ID_RE.match(pid):
        errors.append(f"Invalid plugin ID '{pid}': must be lowercase alphanumeric with hyphens, 2-64 chars")

    version = manifest.get("version", "")
    if version and not _SEMVER_RE.match(version):
        errors.append(f"Invalid version '{version}': must be semver (x.y.z)")

    min_ver = manifest.get("min_thoth_version", "")
    if min_ver and not _SEMVER_RE.match(min_ver):
        errors.append(f"Invalid min_thoth_version '{min_ver}': must be semver")

    author = manifest.get("author", {})
    if not isinstance(author, dict) or not author.get("name"):
        errors.append("'author' must be an object with at least 'name'")

    # 2. plugin_main.py
    main_path = plugin_dir / "plugin_main.py"
    if not main_path.exists():
        errors.append("Missing plugin_main.py")
    else:
        try:
            spec = importlib.util.spec_from_file_location("_validate_plugin", main_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if not hasattr(module, "register"):
                    errors.append("plugin_main.py has no register() function")
                elif not callable(module.register):
                    errors.append("register is not callable")
        except Exception as exc:
            errors.append(f"Error importing plugin_main.py: {exc}")

    # 3-4. Security scan
    for py_file in plugin_dir.rglob("*.py"):
        if "tests/" in str(py_file.relative_to(plugin_dir)):
            continue  # Skip test files
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        rel = py_file.relative_to(plugin_dir)
        for pattern in _DANGEROUS_PATTERNS:
            match = pattern.search(content)
            if match:
                errors.append(
                    f"Security violation in {rel}: forbidden pattern '{match.group()}'"
                )

        for line_no, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for forbidden in _FORBIDDEN_IMPORTS:
                if (re.search(rf"\bimport\s+{re.escape(forbidden)}\b", stripped)
                        or re.search(rf"\bfrom\s+{re.escape(forbidden)}\b", stripped)):
                    if forbidden.startswith("plugins"):
                        continue
                    errors.append(
                        f"Security violation in {rel}:{line_no}: "
                        f"imports core module '{forbidden}'"
                    )

    # 5. README and LICENSE
    if not (plugin_dir / "README.md").exists():
        errors.append("Missing README.md")
    if not (plugin_dir / "LICENSE").exists():
        errors.append("Missing LICENSE")

    return errors


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_plugin.py <plugin_dir>")
        sys.exit(1)

    plugin_dir = Path(sys.argv[1])
    if not plugin_dir.is_dir():
        print(f"ERROR: {plugin_dir} is not a directory")
        sys.exit(1)

    print(f"Validating plugin: {plugin_dir.name}")
    errors = validate(plugin_dir)

    if errors:
        print(f"\n❌ FAILED — {len(errors)} error(s):")
        for e in errors:
            print(f"  • {e}")
        sys.exit(1)
    else:
        print("✅ PASSED — plugin is valid")
        sys.exit(0)


if __name__ == "__main__":
    main()

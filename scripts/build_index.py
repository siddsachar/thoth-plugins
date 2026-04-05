#!/usr/bin/env python3
"""Rebuild index.json from all plugins in the plugins/ directory.

Usage:
    python scripts/build_index.py

Scans every plugins/<id>/plugin.json and builds a fresh index.json
at the repo root.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
PLUGINS_DIR = REPO_ROOT / "plugins"
INDEX_PATH = REPO_ROOT / "index.json"


def build_index() -> dict:
    """Build the index dict from all plugin manifests."""
    plugins = []

    if not PLUGINS_DIR.is_dir():
        PLUGINS_DIR.mkdir(parents=True, exist_ok=True)

    for plugin_dir in sorted(PLUGINS_DIR.iterdir()):
        if not plugin_dir.is_dir():
            continue
        manifest_path = plugin_dir / "plugin.json"
        if not manifest_path.exists():
            print(f"  ⚠️  Skipping {plugin_dir.name}: no plugin.json")
            continue

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception as exc:
            print(f"  ⚠️  Skipping {plugin_dir.name}: {exc}")
            continue

        provides = manifest.get("provides", {})
        author = manifest.get("author", {})
        tool_count = len(provides.get("tools", [])) if isinstance(provides, dict) else 0
        skill_count = len(provides.get("skills", [])) if isinstance(provides, dict) else 0

        plugins.append({
            "id": manifest.get("id", plugin_dir.name),
            "name": manifest.get("name", ""),
            "version": manifest.get("version", ""),
            "description": manifest.get("description", ""),
            "icon": manifest.get("icon", "🔌"),
            "author": {
                "name": author.get("name", "") if isinstance(author, dict) else "",
                "github": author.get("github", "") if isinstance(author, dict) else "",
            },
            "tags": manifest.get("tags", []),
            "min_thoth_version": manifest.get("min_thoth_version", ""),
            "provides": {
                "tools": tool_count,
                "skills": skill_count,
            },
            "verified": True,  # All merged plugins are verified
        })

    return {
        "schema_version": 1,
        "generated": datetime.now(timezone.utc).isoformat(),
        "source": "https://github.com/siddsachar/thoth-plugins",
        "plugins": plugins,
    }


def main():
    print("Building index.json...")
    index = build_index()
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    print(f"✅ index.json updated with {len(index['plugins'])} plugins")


if __name__ == "__main__":
    main()

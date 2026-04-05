#!/usr/bin/env python3
"""Check plugin dependencies against Thoth core requirements.

Usage:
    python scripts/check_core_deps.py plugins/my-plugin/

Reads the plugin's requirements.txt (or python_dependencies from
plugin.json) and verifies none of them conflict with Thoth's core
dependencies listed in a pinned requirements file.

Exit codes:
  0 = no conflicts
  1 = conflicts found
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Core requirements — maintained manually or copied from Thoth's requirements.txt
# This file should be kept in sync with Thoth's actual requirements.
CORE_REQUIREMENTS_PATH = Path(__file__).parent.parent / "core_requirements.txt"


def parse_requirement(line: str) -> tuple[str, str]:
    """Parse 'package>=1.0' into ('package', '>=1.0')."""
    line = line.strip()
    if not line or line.startswith("#"):
        return ("", "")
    match = re.match(r"([a-zA-Z0-9_\-\.]+)\s*(.*)", line)
    if match:
        return (match.group(1).lower().replace("-", "_"), match.group(2).strip())
    return ("", "")


def load_core_deps() -> dict[str, str]:
    """Load core requirements as {package_name: version_spec}."""
    deps = {}
    if not CORE_REQUIREMENTS_PATH.exists():
        print(f"⚠️  Core requirements file not found: {CORE_REQUIREMENTS_PATH}")
        return deps
    for line in CORE_REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines():
        name, spec = parse_requirement(line)
        if name:
            deps[name] = spec
    return deps


def get_plugin_deps(plugin_dir: Path) -> list[str]:
    """Get plugin dependencies from requirements.txt or plugin.json."""
    req_path = plugin_dir / "requirements.txt"
    if req_path.exists():
        return [
            line.strip()
            for line in req_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

    manifest_path = plugin_dir / "plugin.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            return manifest.get("python_dependencies", [])
        except Exception:
            pass

    return []


def check_conflicts(plugin_dir: Path) -> list[str]:
    """Check for dependency conflicts. Returns list of conflict descriptions."""
    core_deps = load_core_deps()
    plugin_deps = get_plugin_deps(plugin_dir)
    conflicts = []

    for dep_line in plugin_deps:
        name, spec = parse_requirement(dep_line)
        if not name:
            continue
        if name in core_deps:
            conflicts.append(
                f"'{name}' is a core dependency ({core_deps[name] or 'any'}). "
                f"Plugin wants: {spec or 'any'}. "
                f"This may cause conflicts."
            )

    return conflicts


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_core_deps.py <plugin_dir>")
        sys.exit(1)

    plugin_dir = Path(sys.argv[1])
    if not plugin_dir.is_dir():
        print(f"ERROR: {plugin_dir} is not a directory")
        sys.exit(1)

    print(f"Checking dependencies for: {plugin_dir.name}")
    conflicts = check_conflicts(plugin_dir)

    if conflicts:
        print(f"\n⚠️  {len(conflicts)} potential conflict(s):")
        for c in conflicts:
            print(f"  • {c}")
        sys.exit(1)
    else:
        print("✅ No dependency conflicts with Thoth core")
        sys.exit(0)


if __name__ == "__main__":
    main()

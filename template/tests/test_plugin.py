"""Basic tests for the plugin template."""

import json
import pathlib


def test_manifest_valid():
    """Verify plugin.json is valid JSON with required fields."""
    manifest_path = pathlib.Path(__file__).parent.parent / "plugin.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "id" in data, "Missing 'id'"
    assert "name" in data, "Missing 'name'"
    assert "version" in data, "Missing 'version'"
    assert "min_thoth_version" in data, "Missing 'min_thoth_version'"
    assert "author" in data, "Missing 'author'"
    assert "description" in data, "Missing 'description'"
    print("✅ Manifest is valid")


def test_register_exists():
    """Verify plugin_main.py has a register() function."""
    import importlib.util
    main_path = pathlib.Path(__file__).parent.parent / "plugin_main.py"
    spec = importlib.util.spec_from_file_location("plugin_main", main_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "register"), "Missing register() function"
    assert callable(module.register), "register is not callable"
    print("✅ register() function exists")


if __name__ == "__main__":
    test_manifest_valid()
    test_register_exists()
    print("\n🎉 All template tests passed!")

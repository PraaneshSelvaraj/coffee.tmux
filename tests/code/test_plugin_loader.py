from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from core import PluginLoader


def test_load_plugins_nonexistent_directory() -> None:
    loader = PluginLoader("/nonexistent/path")

    with pytest.raises(FileNotFoundError) as exc:
        loader.load_plugins()

    assert "doesn't exist" in str(exc.value)


def test_load_plugins_minimal_config_url_only(tmp_path: Path) -> None:
    yaml_content = """
url: https://github.com/owner/my-plugin.git
"""
    (tmp_path / "plugin.yml").write_text(yaml_content)

    loader = PluginLoader(str(tmp_path))
    plugins = loader.load_plugins()

    assert len(plugins) == 1
    plugin = plugins[0]

    assert plugin["url"] == "https://github.com/owner/my-plugin.git"
    assert plugin["name"] == "my-plugin"
    assert plugin["local"] is False
    assert plugin["source"] == []
    assert plugin["tag"] is None
    assert plugin["skip_auto_update"] is False


def test_load_plugins_with_explicit_name(tmp_path: Path) -> None:
    yaml_content = """
name: explicit-name
url: owner/repo
"""
    (tmp_path / "plugin.yml").write_text(yaml_content)

    loader = PluginLoader(str(tmp_path))
    plugins = loader.load_plugins()

    assert len(plugins) == 1
    assert plugins[0]["name"] == "explicit-name"
    assert plugins[0]["url"] == "owner/repo"


def test_load_plugins_multiple_files(tmp_path: Path) -> None:
    (tmp_path / "a.yml").write_text("url: owner/repo-a")
    (tmp_path / "b.yaml").write_text("url: owner/repo-b")

    loader = PluginLoader(str(tmp_path))
    plugins = loader.load_plugins()

    names = {p["name"] for p in plugins}

    assert names == {"repo-a", "repo-b"}


def test_load_plugins_ignores_non_yaml_files(tmp_path: Path) -> None:
    (tmp_path / "plugin.yml").write_text("url: owner/repo")
    (tmp_path / "README.txt").write_text("ignore me")
    (tmp_path / "config.json").write_text("{}")

    loader = PluginLoader(str(tmp_path))
    plugins = loader.load_plugins()

    assert len(plugins) == 1
    assert plugins[0]["name"] == "repo"


def test_load_plugins_missing_url_is_skipped(tmp_path: Path) -> None:
    (tmp_path / "plugin.yml").write_text("name: no-url")

    loader = PluginLoader(str(tmp_path))
    plugins = loader.load_plugins()

    assert plugins == []


def test_load_plugins_empty_yaml_file(tmp_path: Path) -> None:
    (tmp_path / "empty.yml").write_text("")

    loader = PluginLoader(str(tmp_path))
    plugins = loader.load_plugins()

    assert plugins == []


def test_load_plugins_invalid_yaml_syntax(tmp_path: Path, capsys: Any) -> None:
    (tmp_path / "broken.yml").write_text("""
name: bad
  invalid: ::::
url: owner/repo
""")

    loader = PluginLoader(str(tmp_path))
    plugins = loader.load_plugins()

    captured = capsys.readouterr()
    assert "[coffee] Failed to load" in captured.out
    assert plugins == []


def test_load_plugins_defaults_are_applied(tmp_path: Path) -> None:
    (tmp_path / "plugin.yml").write_text("url: owner/repo")

    loader = PluginLoader(str(tmp_path))
    plugin = loader.load_plugins()[0]

    assert plugin["local"] is False
    assert plugin["source"] == []
    assert plugin["tag"] is None
    assert plugin["skip_auto_update"] is False


def test_load_plugins_all_fields(tmp_path: Path) -> None:
    yaml_content = """
name: full-plugin
url: owner/full
local: true
source:
  - a.tmux
  - b.tmux
tag: v2.0.0
skip_auto_update: true
"""
    (tmp_path / "full.yml").write_text(yaml_content)

    loader = PluginLoader(str(tmp_path))
    plugin = loader.load_plugins()[0]

    assert plugin == {
        "name": "full-plugin",
        "url": "owner/full",
        "local": True,
        "source": ["a.tmux", "b.tmux"],
        "tag": "v2.0.0",
        "skip_auto_update": True,
    }


def test_load_plugins_empty_directory(tmp_path: Path) -> None:
    loader = PluginLoader(str(tmp_path))
    assert loader.load_plugins() == []


def test_load_plugins_file_read_error(tmp_path: Path, capsys: Any) -> None:
    (tmp_path / "plugin.yml").write_text("url: owner/repo")

    loader = PluginLoader(str(tmp_path))

    with patch("builtins.open", side_effect=PermissionError("denied")):
        plugins = loader.load_plugins()

    captured = capsys.readouterr()
    assert "[coffee] Failed to load" in captured.out
    assert plugins == []

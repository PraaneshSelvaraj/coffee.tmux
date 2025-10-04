import os
from typing import Any, Dict, List
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import pytest
import core.pluginLoader as pl


def test_load_plugins_nonexistent_directory() -> None:
    loader: pl.PluginLoader = pl.PluginLoader("/nonexistent/path")
    with pytest.raises(FileNotFoundError) as exc_info:
        loader.load_plugins()
    assert "doesn't exist" in str(exc_info.value)


def test_load_plugins_valid_yaml_file(tmp_path: Path) -> None:
    yaml_content: str = """
name: my-plugin
url: owner/repo
local: false
source:
  - plugin.tmux
tag: v1.2.3
skip_auto_update: false
"""
    plugin_file: Path = tmp_path / "plugin.yml"
    plugin_file.write_text(yaml_content)

    loader: pl.PluginLoader = pl.PluginLoader(str(tmp_path))
    plugins: List[Dict[str, Any]] = loader.load_plugins()

    assert len(plugins) == 1
    assert plugins[0]["name"] == "my-plugin"
    assert plugins[0]["url"] == "owner/repo"
    assert plugins[0]["local"] is False
    assert plugins[0]["source"] == ["plugin.tmux"]
    assert plugins[0]["tag"] == "v1.2.3"
    assert plugins[0]["skip_auto_update"] is False


def test_load_plugins_multiple_files(tmp_path: Path) -> None:
    yaml1: str = """
name: plugin1
url: owner/repo1
"""
    yaml2: str = """
name: plugin2
url: owner/repo2
"""
    (tmp_path / "plugin1.yml").write_text(yaml1)
    (tmp_path / "plugin2.yaml").write_text(yaml2)

    loader: pl.PluginLoader = pl.PluginLoader(str(tmp_path))
    plugins: List[Dict[str, Any]] = loader.load_plugins()

    assert len(plugins) == 2
    plugin_names: List[str] = [p["name"] for p in plugins]
    assert "plugin1" in plugin_names
    assert "plugin2" in plugin_names


def test_load_plugins_ignores_non_yaml_files(tmp_path: Path) -> None:
    yaml_content: str = """
name: my-plugin
url: owner/repo
"""
    (tmp_path / "plugin.yml").write_text(yaml_content)
    (tmp_path / "readme.txt").write_text("This is not a yaml file")
    (tmp_path / "config.json").write_text('{"key": "value"}')

    loader: pl.PluginLoader = pl.PluginLoader(str(tmp_path))
    plugins: List[Dict[str, Any]] = loader.load_plugins()

    assert len(plugins) == 1
    assert plugins[0]["name"] == "my-plugin"


def test_load_plugins_missing_required_fields_name(tmp_path: Path) -> None:
    yaml_content: str = """
url: owner/repo
"""
    (tmp_path / "plugin.yml").write_text(yaml_content)

    loader: pl.PluginLoader = pl.PluginLoader(str(tmp_path))
    plugins: List[Dict[str, Any]] = loader.load_plugins()

    # Plugin should be skipped due to missing name
    assert len(plugins) == 0


def test_load_plugins_missing_required_fields_url(tmp_path: Path) -> None:
    yaml_content: str = """
name: my-plugin
"""
    (tmp_path / "plugin.yml").write_text(yaml_content)

    loader: pl.PluginLoader = pl.PluginLoader(str(tmp_path))
    plugins: List[Dict[str, Any]] = loader.load_plugins()

    # Plugin should be skipped due to missing url
    assert len(plugins) == 0


def test_load_plugins_empty_yaml_file(tmp_path: Path) -> None:
    (tmp_path / "empty.yml").write_text("")

    loader: pl.PluginLoader = pl.PluginLoader(str(tmp_path))
    plugins: List[Dict[str, Any]] = loader.load_plugins()

    # Empty file should be skipped
    assert len(plugins) == 0


def test_load_plugins_invalid_yaml_syntax(tmp_path: Path, capsys: Any) -> None:
    invalid_yaml: str = """
name: my-plugin
  invalid: :: syntax
url: owner/repo
"""
    (tmp_path / "invalid.yml").write_text(invalid_yaml)

    loader: pl.PluginLoader = pl.PluginLoader(str(tmp_path))
    plugins: List[Dict[str, Any]] = loader.load_plugins()

    # Should handle exception and print error
    captured = capsys.readouterr()
    assert "Error Reading" in captured.out
    assert len(plugins) == 0


def test_load_plugins_default_values(tmp_path: Path) -> None:
    yaml_content: str = """
name: simple-plugin
url: owner/repo
"""
    (tmp_path / "plugin.yml").write_text(yaml_content)

    loader: pl.PluginLoader = pl.PluginLoader(str(tmp_path))
    plugins: List[Dict[str, Any]] = loader.load_plugins()

    assert len(plugins) == 1
    plugin: Dict[str, Any] = plugins[0]
    assert plugin["local"] is False
    assert plugin["source"] == []
    assert plugin["tag"] is None
    assert plugin["skip_auto_update"] is False


def test_load_plugins_with_all_fields(tmp_path: Path) -> None:
    yaml_content: str = """
name: complete-plugin
url: owner/complete-repo
local: true
source:
  - main.tmux
  - utils.tmux
tag: v2.0.0
skip_auto_update: true
"""
    (tmp_path / "complete.yaml").write_text(yaml_content)

    loader: pl.PluginLoader = pl.PluginLoader(str(tmp_path))
    plugins: List[Dict[str, Any]] = loader.load_plugins()

    assert len(plugins) == 1
    plugin: Dict[str, Any] = plugins[0]
    assert plugin["name"] == "complete-plugin"
    assert plugin["url"] == "owner/complete-repo"
    assert plugin["local"] is True
    assert plugin["source"] == ["main.tmux", "utils.tmux"]
    assert plugin["tag"] == "v2.0.0"
    assert plugin["skip_auto_update"] is True


def test_load_plugins_empty_directory(tmp_path: Path) -> None:
    loader: pl.PluginLoader = pl.PluginLoader(str(tmp_path))
    plugins: List[Dict[str, Any]] = loader.load_plugins()

    assert len(plugins) == 0


def test_load_plugins_file_read_error(tmp_path: Path, capsys: Any) -> None:
    yaml_file: Path = tmp_path / "plugin.yml"
    yaml_file.write_text("name: test\nurl: owner/repo")

    loader: pl.PluginLoader = pl.PluginLoader(str(tmp_path))

    # Mock open to raise an exception
    with patch("builtins.open", side_effect=PermissionError("Access denied")):
        plugins: List[Dict[str, Any]] = loader.load_plugins()

    captured = capsys.readouterr()
    assert "Error Reading" in captured.out
    assert len(plugins) == 0

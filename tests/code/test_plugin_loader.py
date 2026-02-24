from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from core import PluginLoader


def test_load_plugins_nonexistent_directory() -> None:
    loader = PluginLoader("/nonexistent/path")

    with pytest.raises(FileNotFoundError):
        loader.load_plugins()


def test_load_plugins_minimal_config_url_only(tmp_path: Path) -> None:
    yaml_content = """
url: https://github.com/owner/my-plugin.git
"""
    (tmp_path / "plugin.yml").write_text(yaml_content)

    loader = PluginLoader(str(tmp_path))
    plugins = loader.load_plugins()

    assert len(plugins) == 1
    plugin = plugins[0]

    assert plugin["url"] == "owner/my-plugin"
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


def test_load_plugins_missing_url_raises(tmp_path: Path) -> None:
    (tmp_path / "plugin.yml").write_text("name: no-url")

    loader = PluginLoader(str(tmp_path))

    with pytest.raises(ValueError):
        loader.load_plugins()


def test_load_plugins_empty_yaml_file_raises(tmp_path: Path) -> None:
    (tmp_path / "empty.yml").write_text("")

    loader = PluginLoader(str(tmp_path))

    with pytest.raises(ValueError):
        loader.load_plugins()


def test_load_plugins_invalid_yaml_syntax_raises(tmp_path: Path) -> None:
    (tmp_path / "broken.yml").write_text("""
name: bad
  invalid: ::::
url: owner/repo
""")

    loader = PluginLoader(str(tmp_path))

    with pytest.raises(yaml.YAMLError):
        loader.load_plugins()


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


def test_load_plugins_file_read_error_raises(tmp_path: Path) -> None:
    (tmp_path / "plugin.yml").write_text("url: owner/repo")

    loader = PluginLoader(str(tmp_path))

    with patch("builtins.open", side_effect=PermissionError("denied")):
        with pytest.raises(PermissionError):
            loader.load_plugins()


def test_load_plugins_duplicate_repo_across_files_raises(tmp_path: Path) -> None:
    (tmp_path / "a.yml").write_text("url: owner/repo")
    (tmp_path / "b.yml").write_text("url: owner/repo")

    loader = PluginLoader(str(tmp_path))

    with pytest.raises(ValueError, match="Duplicate plugin URL"):
        loader.load_plugins()


def test_load_plugins_duplicate_repo_different_url_forms_raises(tmp_path: Path) -> None:
    (tmp_path / "a.yml").write_text("url: owner/repo")
    (tmp_path / "b.yml").write_text("url: https://github.com/owner/repo.git")

    loader = PluginLoader(str(tmp_path))

    with pytest.raises(ValueError):
        loader.load_plugins()


def test_load_plugins_duplicate_repo_case_insensitive_raises(tmp_path: Path) -> None:
    (tmp_path / "a.yml").write_text("url: Owner/Repo")
    (tmp_path / "b.yml").write_text("url: owner/repo")

    loader = PluginLoader(str(tmp_path))

    with pytest.raises(ValueError):
        loader.load_plugins()


def test_plugin_name_derived_from_url(tmp_path: Path) -> None:
    (tmp_path / "plugin.yml").write_text("url: owner/my-plugin")

    loader = PluginLoader(str(tmp_path))
    plugin = loader.load_plugins()[0]

    assert plugin["name"] == "my-plugin"


def test_load_plugins_list_format_multiple_plugins(tmp_path: Path) -> None:
    yaml_content = """
- url: owner/plugin-b
- url: owner/plugin-c
  tag: v1.0
"""
    (tmp_path / "plugins.yaml").write_text(yaml_content)

    loader = PluginLoader(str(tmp_path))
    plugins = loader.load_plugins()

    assert len(plugins) == 2
    assert plugins[0]["name"] == "plugin-b"
    assert plugins[0]["url"] == "owner/plugin-b"
    assert plugins[1]["name"] == "plugin-c"
    assert plugins[1]["tag"] == "v1.0"


def test_load_plugins_list_format_full_config(tmp_path: Path) -> None:
    yaml_content = """
- name: custom-name
  url: owner/repo
  local: true
  source:
    - main.tmux
  tag: v2.0
  skip_auto_update: true
"""
    (tmp_path / "plugins.yaml").write_text(yaml_content)

    loader = PluginLoader(str(tmp_path))
    plugins = loader.load_plugins()

    assert len(plugins) == 1
    assert plugins[0] == {
        "name": "custom-name",
        "url": "owner/repo",
        "local": True,
        "source": ["main.tmux"],
        "tag": "v2.0",
        "skip_auto_update": True,
    }


def test_load_plugins_hybrid_single_and_list_files(tmp_path: Path) -> None:
    (tmp_path / "a-reset.yaml").write_text("url: owner/tmux-reset")
    list_yaml = """
- url: owner/plugin-a
- url: owner/plugin-b
"""
    (tmp_path / "b-batch.yaml").write_text(list_yaml)
    (tmp_path / "c-last.yaml").write_text("url: owner/plugin-last")

    loader = PluginLoader(str(tmp_path))
    plugins = loader.load_plugins()

    names = [p["name"] for p in plugins]
    assert "tmux-reset" in names
    assert "plugin-a" in names
    assert "plugin-b" in names
    assert "plugin-last" in names


def test_load_plugins_list_format_duplicate_within_list_raises(tmp_path: Path) -> None:
    yaml_content = """
- url: owner/repo
- url: owner/repo
"""
    (tmp_path / "plugins.yaml").write_text(yaml_content)

    loader = PluginLoader(str(tmp_path))

    with pytest.raises(ValueError, match="Duplicate plugin URL"):
        loader.load_plugins()


def test_load_plugins_list_format_duplicate_across_files_raises(tmp_path: Path) -> None:
    (tmp_path / "a.yaml").write_text("url: owner/repo")
    list_yaml = """
- url: owner/repo
"""
    (tmp_path / "b.yaml").write_text(list_yaml)

    loader = PluginLoader(str(tmp_path))

    with pytest.raises(ValueError, match="Duplicate plugin URL"):
        loader.load_plugins()


def test_load_plugins_list_format_empty_list_raises(tmp_path: Path) -> None:
    (tmp_path / "plugins.yaml").write_text("[]")

    loader = PluginLoader(str(tmp_path))

    with pytest.raises(ValueError, match="must not be empty"):
        loader.load_plugins()


def test_load_plugins_list_format_entry_not_a_dict_raises(tmp_path: Path) -> None:
    yaml_content = """
- "just-a-string"
"""
    (tmp_path / "plugins.yaml").write_text(yaml_content)

    loader = PluginLoader(str(tmp_path))

    with pytest.raises(ValueError, match="must be a mapping"):
        loader.load_plugins()


def test_load_plugins_list_format_entry_missing_url_raises(tmp_path: Path) -> None:
    yaml_content = """
- name: no-url-plugin
"""
    (tmp_path / "plugins.yaml").write_text(yaml_content)

    loader = PluginLoader(str(tmp_path))

    with pytest.raises(ValueError, match="Invalid plugin config"):
        loader.load_plugins()


def test_load_plugins_list_format_preserves_order(tmp_path: Path) -> None:
    yaml_content = """
- url: owner/third
- url: owner/first
- url: owner/second
"""
    (tmp_path / "plugins.yaml").write_text(yaml_content)

    loader = PluginLoader(str(tmp_path))
    plugins = loader.load_plugins()

    assert [p["name"] for p in plugins] == ["third", "first", "second"]

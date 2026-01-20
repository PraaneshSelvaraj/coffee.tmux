from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from core import PluginRemover


def make_remover() -> PluginRemover:
    return PluginRemover("/fake/path")


def test_get_installed_plugins_empty() -> None:
    with patch("core.lock_file_manager.read_lock_file", return_value={"plugins": []}):
        remover = make_remover()
        plugins = remover.get_installed_plugins()
        assert plugins == []


@patch("os.path.exists", return_value=True)
@patch("subprocess.run")
@patch("core.lock_file_manager.read_lock_file")
def test_get_installed_plugins_with_size_and_tag(
    mock_read: MagicMock,
    mock_run: MagicMock,
    mock_exists: MagicMock,
) -> None:
    mock_read.return_value = {
        "plugins": [
            {
                "name": "test-plugin",
                "enabled": True,
                "git": {
                    "tag": "v1.0.0",
                    "commit_hash": "abcdef123456",
                    "last_pull": "2024-10-01T10:00:00",
                },
            }
        ]
    }
    mock_run.return_value = MagicMock(returncode=0, stdout="5.2M\t/path\n")

    remover = make_remover()
    plugins = remover.get_installed_plugins()

    plugin = plugins[0]
    assert plugin["name"] == "test-plugin"
    assert plugin["version"] == "v1.0.0"
    assert plugin["size"] == "5.2M"
    assert plugin["enabled"] is True
    assert plugin["installed"] == "2024-10-01"


@patch("os.path.exists", return_value=False)
@patch("core.lock_file_manager.read_lock_file")
def test_get_installed_plugins_path_missing(
    mock_read: MagicMock,
    mock_exists: MagicMock,
) -> None:
    mock_read.return_value = {
        "plugins": [
            {
                "name": "missing-plugin",
                "enabled": False,
                "git": {
                    "commit_hash": "abc123456789",
                    "last_pull": None,
                },
            }
        ]
    }

    remover = make_remover()
    plugins = remover.get_installed_plugins()

    plugin = plugins[0]
    assert plugin["size"] == "Unknown"
    assert plugin["version"] == "abc1234"
    assert plugin["installed"] == "Unknown"


@patch("os.path.exists", return_value=True)
@patch("subprocess.run", side_effect=OSError("du failed"))
@patch("core.lock_file_manager.read_lock_file")
def test_get_installed_plugins_du_failure(
    mock_read: MagicMock,
    mock_run: MagicMock,
    mock_exists: MagicMock,
) -> None:
    mock_read.return_value = {
        "plugins": [{"name": "plugin", "enabled": True, "git": {"tag": "v2.0.0"}}]
    }

    remover = make_remover()
    plugins = remover.get_installed_plugins()
    assert plugins[0]["size"] == "Unknown"


@patch("os.path.exists", return_value=True)
@patch("shutil.rmtree")
@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file")
def test_remove_plugin_success(
    mock_read: MagicMock,
    mock_write: MagicMock,
    mock_rmtree: MagicMock,
    mock_exists: MagicMock,
) -> None:
    mock_read.return_value = {"plugins": [{"name": "plugin1"}, {"name": "plugin2"}]}

    remover = make_remover()
    result = remover.remove_plugin("plugin1")

    assert result is True
    mock_rmtree.assert_called_once_with("/fake/path/plugin1")

    written = mock_write.call_args[0][0]
    assert len(written["plugins"]) == 1
    assert written["plugins"][0]["name"] == "plugin2"


@patch("core.lock_file_manager.read_lock_file")
def test_remove_plugin_not_in_lock(mock_read: MagicMock) -> None:
    mock_read.return_value = {"plugins": [{"name": "plugin1"}]}

    remover = make_remover()
    assert remover.remove_plugin("missing") is False


@patch("os.path.exists", return_value=True)
@patch("shutil.rmtree", side_effect=OSError("permission denied"))
@patch("core.lock_file_manager.read_lock_file")
def test_remove_plugin_directory_failure_raises(
    mock_read: MagicMock,
    mock_rmtree: MagicMock,
    mock_exists: MagicMock,
) -> None:
    mock_read.return_value = {"plugins": [{"name": "plugin1"}]}
    remover = make_remover()

    with pytest.raises(OSError):
        remover.remove_plugin("plugin1")


@patch("os.path.exists", return_value=False)
@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file")
def test_remove_plugin_directory_missing_still_updates_lock(
    mock_read: MagicMock,
    mock_write: MagicMock,
    mock_exists: MagicMock,
) -> None:
    mock_read.return_value = {"plugins": [{"name": "plugin1"}]}

    remover = make_remover()
    assert remover.remove_plugin("plugin1") is True
    mock_write.assert_called_once()


@patch("os.path.exists", return_value=True)
@patch("shutil.rmtree")
@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file")
def test_remove_plugin_progress_callback(
    mock_read: MagicMock,
    mock_write: MagicMock,
    mock_rmtree: MagicMock,
    mock_exists: MagicMock,
) -> None:
    mock_read.return_value = {"plugins": [{"name": "plugin1"}]}
    calls: list[tuple[str, int]] = []

    def cb(name: str, p: int) -> None:
        calls.append((name, p))

    remover = make_remover()
    assert remover.remove_plugin("plugin1", progress_callback=cb) is True

    assert calls == [
        ("plugin1", 10),
        ("plugin1", 40),
        ("plugin1", 70),
        ("plugin1", 100),
    ]


@patch("core.lock_file_manager.read_lock_file", side_effect=OSError("read error"))
def test_remove_plugin_read_lock_failure_raises(
    mock_read: MagicMock,
) -> None:
    calls: list[tuple[str, int]] = []

    def cb(name: str, p: int) -> None:
        calls.append((name, p))

    remover = make_remover()

    with pytest.raises(OSError):
        remover.remove_plugin("plugin1", progress_callback=cb)

    assert calls[-1] == ("plugin1", 0)

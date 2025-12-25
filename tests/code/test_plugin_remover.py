from typing import Any
from unittest.mock import MagicMock, patch

from core import PluginRemover


def test_get_installed_plugins_empty() -> None:
    with patch("core.lock_file_manager.read_lock_file", return_value={"plugins": []}):
        remover: PluginRemover = PluginRemover("/fake/path")
        plugins: list[dict[str, str | bool | dict[str, Any]]] = (
            remover.get_installed_plugins()
        )
        assert len(plugins) == 0


@patch("os.path.exists", return_value=True)
@patch("subprocess.run")
@patch("core.lock_file_manager.read_lock_file")
def test_get_installed_plugins_with_size(
    mock_read: MagicMock, mock_run: MagicMock, mock_exists: MagicMock
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

    remover: PluginRemover = PluginRemover("/fake/path")
    plugins: list[dict[str, str | bool | dict[str, Any]]] = (
        remover.get_installed_plugins()
    )

    assert len(plugins) == 1
    assert plugins[0]["name"] == "test-plugin"
    assert plugins[0]["version"] == "v1.0.0"
    assert plugins[0]["size"] == "5.2M"
    assert plugins[0]["enabled"] is True
    assert plugins[0]["installed"] == "2024-10-01"


@patch("os.path.exists", return_value=False)
@patch("core.lock_file_manager.read_lock_file")
def test_get_installed_plugins_path_not_exists(
    mock_read: MagicMock, mock_exists: MagicMock
) -> None:
    mock_read.return_value = {
        "plugins": [
            {
                "name": "missing-plugin",
                "enabled": False,
                "git": {"tag": None, "commit_hash": "abc123", "last_pull": "Unknown"},
            }
        ]
    }

    remover: PluginRemover = PluginRemover("/fake/path")
    plugins: list[dict[str, str | bool | dict[str, Any]]] = (
        remover.get_installed_plugins()
    )

    assert len(plugins) == 1
    assert plugins[0]["name"] == "missing-plugin"
    assert plugins[0]["size"] == "Unknown"
    assert plugins[0]["version"] == "abc123"  # First 7 chars of commit hash
    assert plugins[0]["installed"] == "Unknown"


@patch("os.path.exists", return_value=True)
@patch("subprocess.run", side_effect=Exception("du failed"))
@patch("core.lock_file_manager.read_lock_file")
def test_get_installed_plugins_du_command_fails(
    mock_read: MagicMock, mock_run: MagicMock, mock_exists: MagicMock
) -> None:
    mock_read.return_value = {
        "plugins": [
            {
                "name": "test-plugin",
                "enabled": True,
                "git": {"tag": "v2.0", "commit_hash": "xyz789", "last_pull": "Unknown"},
            }
        ]
    }

    remover: PluginRemover = PluginRemover("/fake/path")
    plugins: list[dict[str, str | bool | dict[str, Any]]] = (
        remover.get_installed_plugins()
    )

    assert len(plugins) == 1
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
    mock_read.return_value = {
        "plugins": [
            {"name": "plugin1", "enabled": True},
            {"name": "plugin2", "enabled": False},
        ]
    }

    remover: PluginRemover = PluginRemover("/fake/path")
    result: bool = remover.remove_plugin("plugin1")

    assert result is True
    mock_rmtree.assert_called_once_with("/fake/path/plugin1")
    mock_write.assert_called_once()

    # Verify plugin1 was removed from the list
    written_data = mock_write.call_args[0][0]
    assert len(written_data["plugins"]) == 1
    assert written_data["plugins"][0]["name"] == "plugin2"


@patch("core.lock_file_manager.read_lock_file")
def test_remove_plugin_not_found(mock_read: MagicMock) -> None:
    mock_read.return_value = {"plugins": [{"name": "plugin1", "enabled": True}]}

    remover: PluginRemover = PluginRemover("/fake/path")
    result: bool = remover.remove_plugin("nonexistent-plugin")

    assert result is False


@patch("os.path.exists", return_value=True)
@patch("shutil.rmtree", side_effect=Exception("Permission denied"))
@patch("core.lock_file_manager.read_lock_file")
def test_remove_plugin_rmtree_fails(
    mock_read: MagicMock, mock_rmtree: MagicMock, mock_exists: MagicMock
) -> None:
    mock_read.return_value = {"plugins": [{"name": "plugin1", "enabled": True}]}

    remover: PluginRemover = PluginRemover("/fake/path")
    result: bool = remover.remove_plugin("plugin1")

    assert result is False


@patch("os.path.exists", return_value=False)
@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file")
def test_remove_plugin_path_not_exists(
    mock_read: MagicMock, mock_write: MagicMock, mock_exists: MagicMock
) -> None:
    mock_read.return_value = {"plugins": [{"name": "plugin1", "enabled": True}]}

    remover: PluginRemover = PluginRemover("/fake/path")
    result: bool = remover.remove_plugin("plugin1")

    # Should still succeed and update lock file even if directory doesn't exist
    assert result is True
    mock_write.assert_called_once()


@patch("os.path.exists", return_value=True)
@patch("shutil.rmtree")
@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file")
def test_remove_plugin_with_progress_callback(
    mock_read: MagicMock,
    mock_write: MagicMock,
    mock_rmtree: MagicMock,
    mock_exists: MagicMock,
) -> None:
    mock_read.return_value = {"plugins": [{"name": "plugin1", "enabled": True}]}

    progress_calls: list[tuple[str, int]] = []

    def progress_callback(name: str, progress: int) -> None:
        progress_calls.append((name, progress))

    remover: PluginRemover = PluginRemover("/fake/path")
    result: bool = remover.remove_plugin("plugin1", progress_callback=progress_callback)

    assert result is True
    assert len(progress_calls) == 4
    assert progress_calls[0] == ("plugin1", 10)
    assert progress_calls[1] == ("plugin1", 50)
    assert progress_calls[2] == ("plugin1", 80)
    assert progress_calls[3] == ("plugin1", 100)


@patch("core.lock_file_manager.read_lock_file")
def test_remove_plugin_with_progress_callback_failure(
    mock_read: MagicMock,
) -> None:
    mock_read.return_value = {"plugins": []}

    progress_calls: list[tuple[str, int]] = []

    def progress_callback(name: str, progress: int) -> None:
        progress_calls.append((name, progress))

    remover: PluginRemover = PluginRemover("/fake/path")
    result: bool = remover.remove_plugin(
        "nonexistent", progress_callback=progress_callback
    )

    assert result is False
    # Should have initial progress and failure (0)
    assert progress_calls[-1] == ("nonexistent", 0)


@patch("core.lock_file_manager.read_lock_file", side_effect=Exception("Read error"))
def test_remove_plugin_exception_handling(mock_read: MagicMock) -> None:
    progress_calls: list[tuple[str, int]] = []

    def progress_callback(name: str, progress: int) -> None:
        progress_calls.append((name, progress))

    remover: PluginRemover = PluginRemover("/fake/path")
    result: bool = remover.remove_plugin("plugin1", progress_callback=progress_callback)

    assert result is False
    assert progress_calls[-1] == ("plugin1", 0)


@patch("os.path.exists", return_value=True)
@patch("subprocess.run")
@patch("core.lock_file_manager.read_lock_file")
def test_get_installed_plugins_version_from_commit_hash(
    mock_read: MagicMock, mock_run: MagicMock, mock_exists: MagicMock
) -> None:
    mock_read.return_value = {
        "plugins": [
            {
                "name": "plugin-no-tag",
                "enabled": True,
                "git": {
                    "tag": None,
                    "commit_hash": "abcdef1234567890",
                    "last_pull": "2024-10-04T15:30:00Z",
                },
            }
        ]
    }
    mock_run.return_value = MagicMock(returncode=0, stdout="3.5M\t/path\n")

    remover: PluginRemover = PluginRemover("/fake/path")
    plugins: list[dict[str, str | bool | dict[str, Any]]] = (
        remover.get_installed_plugins()
    )

    assert len(plugins) == 1
    assert plugins[0]["version"] == "abcdef1"  # First 7 chars
    assert plugins[0]["installed"] == "2024-10-04"

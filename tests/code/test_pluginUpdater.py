import subprocess
import threading
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import core.pluginUpdater as pu


def test_safe_check_output_success() -> None:
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    with patch("subprocess.check_output", return_value="output\n"):
        result: Optional[str] = updater._safe_check_output(["git", "rev-parse", "HEAD"])
        assert result == "output"


def test_safe_check_output_failure_returns_default() -> None:
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    with patch(
        "subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "cmd")
    ):
        result: Optional[str] = updater._safe_check_output(
            ["git", "rev-parse", "HEAD"], default="default_value"
        )
        assert result == "default_value"


def test_get_local_head_commit_full() -> None:
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    with patch.object(updater, "_safe_check_output", return_value="abcdef1234567890"):
        commit: Optional[str] = updater._get_local_head_commit("/plugin/path")
        assert commit == "abcdef1234567890"


def test_get_local_head_commit_short() -> None:
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    with patch.object(updater, "_safe_check_output", return_value="abcdef1234567890"):
        commit: Optional[str] = updater._get_local_head_commit(
            "/plugin/path", short=True
        )
        assert commit == "abcdef1"


def test_get_repo_size_success() -> None:
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="5.2M\t.git\n")
        size: str = updater._get_repo_size("/plugin/path")
        assert size == "5.2M"


def test_get_repo_size_failure() -> None:
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    with patch("subprocess.run", side_effect=Exception("du failed")):
        size: str = updater._get_repo_size("/plugin/path")
        assert size == "Unknown"


def test_get_time_since_tag_success() -> None:
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="2 weeks ago\n")
        time: str = updater._get_time_since_tag("/plugin/path", "v1.0")
        assert time == "2 weeks ago"


def test_get_time_since_tag_no_tag() -> None:
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    time: str = updater._get_time_since_tag("/plugin/path", None)
    assert time == "Unknown"


def test_get_remote_tags_success() -> None:
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    git_output: str = """abc123\trefs/tags/v1.0.0
def456\trefs/tags/v1.1.0
ghi789\trefs/tags/v2.0.0^{}
"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=git_output)
        tags: List[str] = updater._get_remote_tags("https://github.com/owner/repo")
        assert "v1.0.0" in tags
        assert "v1.1.0" in tags
        assert "v2.0.0" in tags
        assert len(tags) == 3


def test_get_remote_tags_failure() -> None:
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        tags: List[str] = updater._get_remote_tags("https://github.com/owner/repo")
        assert tags == []


def test_get_latest_commit_success() -> None:
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc123def456\tHEAD\n")
        commit: Optional[str] = updater._get_latest_commit(
            "https://github.com/owner/repo"
        )
        assert commit == "abc123def456"


def test_get_latest_commit_failure() -> None:
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        commit: Optional[str] = updater._get_latest_commit(
            "https://github.com/owner/repo"
        )
        assert commit is None


def test_get_tag_commit_hash_success() -> None:
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="xyz789abc\trefs/tags/v1.0\n"
        )
        commit: Optional[str] = updater._get_tag_commit_hash(
            "https://github.com/owner/repo", "v1.0"
        )
        assert commit == "xyz789abc"


@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file")
def test_write_lockfile_update_success(
    mock_read: MagicMock, mock_write: MagicMock
) -> None:
    mock_read.return_value = {
        "plugins": [
            {"name": "plugin1", "git": {"tag": "v1.0", "commit_hash": "abc123"}}
        ]
    }
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    success: bool = updater._write_lockfile_update(
        "plugin1", new_tag="v2.0", new_commit="def456"
    )

    assert success is True
    mock_write.assert_called_once()
    written_data: Dict[str, Any] = mock_write.call_args[0][0]
    plugin = written_data["plugins"][0]
    assert plugin["git"]["tag"] == "v2.0"
    assert plugin["git"]["commit_hash"] == "def456"


@patch("core.lock_file_manager.read_lock_file", side_effect=Exception("Read error"))
def test_write_lockfile_update_failure(mock_read: MagicMock) -> None:
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    success: bool = updater._write_lockfile_update("plugin1", new_tag="v2.0")
    assert success is False


@patch("os.path.exists", return_value=False)
@patch("core.lock_file_manager.read_lock_file")
def test_check_for_updates_plugin_not_installed(
    mock_read: MagicMock, mock_exists: MagicMock
) -> None:
    mock_read.return_value = {
        "plugins": [{"name": "plugin1", "git": {"repo": "owner/repo", "tag": "v1.0"}}]
    }
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    updates: List[Dict[str, Any]] = updater.check_for_updates()

    assert len(updates) == 1
    assert updates[0]["name"] == "plugin1"
    assert updates[0]["current_version"] == "Not installed"
    assert updates[0]["_internal"]["update_available"] is False


@patch("os.path.exists", return_value=True)
@patch("core.lock_file_manager.read_lock_file")
def test_check_for_updates_up_to_date(
    mock_read: MagicMock, mock_exists: MagicMock
) -> None:
    mock_read.return_value = {
        "plugins": [
            {
                "name": "plugin1",
                "git": {"repo": "owner/repo", "tag": "v1.0", "commit_hash": "abc123"},
            }
        ]
    }
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")

    with patch.object(updater, "_get_remote_tags", return_value=["v1.0"]):
        with patch.object(updater, "_get_tag_commit_hash", return_value="abc123"):
            with patch.object(updater, "_get_repo_size", return_value="5.2M"):
                with patch.object(
                    updater, "_get_time_since_tag", return_value="2 weeks ago"
                ):
                    updates: List[Dict[str, Any]] = updater.check_for_updates()

    assert len(updates) == 1
    assert updates[0]["name"] == "plugin1"
    assert updates[0]["changelog"] == ["Up-to-date"]
    assert updates[0]["_internal"]["update_available"] is False


@patch("os.path.exists", return_value=True)
@patch("core.lock_file_manager.read_lock_file")
def test_check_for_updates_update_available(
    mock_read: MagicMock, mock_exists: MagicMock
) -> None:
    mock_read.return_value = {
        "plugins": [
            {
                "name": "plugin1",
                "git": {"repo": "owner/repo", "tag": "v1.0", "commit_hash": "abc123"},
            }
        ]
    }
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")

    with patch.object(updater, "_get_remote_tags", return_value=["v2.0", "v1.0"]):
        with patch.object(updater, "_get_tag_commit_hash", return_value="def456"):
            with patch.object(updater, "_get_repo_size", return_value="5.2M"):
                with patch.object(
                    updater, "_get_time_since_tag", return_value="1 week ago"
                ):
                    updates: List[Dict[str, Any]] = updater.check_for_updates()

    assert len(updates) == 1
    assert updates[0]["name"] == "plugin1"
    assert updates[0]["current_version"] == "v1.0"
    assert updates[0]["new_version"] == "v2.0"
    assert updates[0]["_internal"]["update_available"] is True


@patch("subprocess.run")
@patch.object(pu.PluginUpdater, "_get_local_head_commit", return_value="newcommit")
@patch.object(pu.PluginUpdater, "_write_lockfile_update", return_value=True)
def test_update_plugin_tag_success(
    mock_write: MagicMock, mock_commit: MagicMock, mock_run: MagicMock
) -> None:
    update_info: Dict[str, Any] = {
        "name": "plugin1",
        "_internal": {
            "type": "tag",
            "new_tag": "v2.0",
            "plugin_path": "/fake/path/plugin1",
            "repo_url": "https://github.com/owner/repo",
            "update_available": True,
        },
    }

    progress_calls: List[tuple[str, int]] = []

    def progress_callback(name: str, progress: int) -> None:
        progress_calls.append((name, progress))

    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    success: bool = updater.update_plugin(update_info, progress_callback)

    assert success is True
    assert len(progress_calls) == 4
    assert progress_calls[-1] == ("plugin1", 100)


@patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd"))
def test_update_plugin_failure(mock_run: MagicMock) -> None:
    update_info: Dict[str, Any] = {
        "name": "plugin1",
        "_internal": {
            "type": "tag",
            "new_tag": "v2.0",
            "plugin_path": "/fake/path/plugin1",
            "repo_url": "https://github.com/owner/repo",
            "update_available": True,
        },
    }

    progress_calls: List[tuple[str, int]] = []

    def progress_callback(name: str, progress: int) -> None:
        progress_calls.append((name, progress))

    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    success: bool = updater.update_plugin(update_info, progress_callback)

    assert success is False
    assert progress_calls[-1] == ("plugin1", 0)


def test_update_plugin_no_update_available() -> None:
    update_info: Dict[str, Any] = {
        "name": "plugin1",
        "_internal": {
            "update_available": False,
            "plugin_path": "/fake/path/plugin1",
            "repo_url": "https://github.com/owner/repo",
        },
    }

    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    success: bool = updater.update_plugin(update_info)
    assert success is False


@patch.object(pu.PluginUpdater, "update_plugin", return_value=True)
def test_update_plugin_async(mock_update: MagicMock) -> None:
    update_info: Dict[str, Any] = {
        "name": "plugin1",
        "_internal": {"update_available": True},
    }

    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    thread: threading.Thread = updater.update_plugin_async(update_info)

    assert isinstance(thread, threading.Thread)
    thread.join(timeout=2)
    mock_update.assert_called_once()


@patch.object(pu.PluginUpdater, "update_plugin_async")
def test_update_marked_plugins(mock_async: MagicMock) -> None:
    mock_async.return_value = threading.Thread(target=lambda: None)

    updates: List[Dict[str, Any]] = [
        {"name": "plugin1", "marked": True, "_internal": {}},
        {"name": "plugin2", "marked": False, "_internal": {}},
        {"name": "plugin3", "marked": True, "_internal": {}},
    ]

    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    threads: List[threading.Thread] = updater.update_marked_plugins(updates)

    assert len(threads) == 2
    assert mock_async.call_count == 2


@patch.object(pu.PluginUpdater, "update_plugin_async")
def test_update_all_plugins(mock_async: MagicMock) -> None:
    mock_async.return_value = threading.Thread(target=lambda: None)

    updates: List[Dict[str, Any]] = [
        {"name": "plugin1", "_internal": {"update_available": True}},
        {"name": "plugin2", "_internal": {"update_available": False}},
        {"name": "plugin3", "_internal": {"update_available": True}},
    ]

    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    threads: List[threading.Thread] = updater.update_all_plugins(updates)

    assert len(threads) == 2
    assert mock_async.call_count == 2


@patch.object(pu.PluginUpdater, "update_plugin", return_value=True)
@patch.object(pu.PluginUpdater, "check_for_updates")
@patch("core.lock_file_manager.read_lock_file")
def test_auto_update_all(
    mock_read: MagicMock, mock_check: MagicMock, mock_update: MagicMock, capsys: Any
) -> None:
    mock_read.return_value = {
        "plugins": [
            {"name": "plugin1", "skip_auto_update": False},
            {"name": "plugin2", "skip_auto_update": True},
        ]
    }
    mock_check.return_value = [
        {"name": "plugin1", "_internal": {"update_available": True}},
        {"name": "plugin2", "_internal": {"update_available": True}},
    ]

    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    updater.auto_update_all()

    # Only plugin1 should be updated (plugin2 has skip_auto_update=True)
    assert mock_update.call_count == 1
    captured = capsys.readouterr()
    assert "plugin1 updated successfully" in captured.out


def test_get_update_status() -> None:
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    thread: threading.Thread = threading.Thread(target=lambda: None)
    updater._update_threads["plugin1"] = thread

    status: Optional[threading.Thread] = updater.get_update_status("plugin1")
    assert status is thread


def test_cancel_update_not_running() -> None:
    updater: pu.PluginUpdater = pu.PluginUpdater("/fake/path")
    result: bool = updater.cancel_update("nonexistent")
    assert result is True

import subprocess
import datetime
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch, MagicMock
import core.pluginInstaller as pi


def make_installer_with_plugins(
    plugins: Optional[List[Dict[str, Any]]] = None,
) -> pi.PluginInstaller:
    if plugins is None:
        plugins = [{"name": "foo", "url": "owner/repo"}]
    return pi.PluginInstaller(plugins, "/plugins/dir", "/tmux.conf")


def test_get_latest_tag_returns_tag() -> None:
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "v1.0.0\nv0.9.0\n"
        tag: Optional[str] = make_installer_with_plugins()._get_latest_tag("dummy_path")
        assert tag == "v1.0.0"


def test_get_latest_tag_empty_returns_none() -> None:
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = ""
        tag: Optional[str] = make_installer_with_plugins()._get_latest_tag("dummy_path")
        assert tag is None


def test_get_latest_tag_raises_called_process_error() -> None:
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd")):
        tag: Optional[str] = make_installer_with_plugins()._get_latest_tag("dummy_path")
        assert tag is None


def test_get_commit_hash_success() -> None:
    installer: pi.PluginInstaller = make_installer_with_plugins()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "commit_hash_123"
        commit: Optional[str] = installer._get_commit_hash({"name": "foo"})
        assert commit == "commit_hash_123"


def test_get_commit_hash_failure() -> None:
    installer: pi.PluginInstaller = make_installer_with_plugins()
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd")):
        commit: Optional[str] = installer._get_commit_hash({"name": "foo"})
        assert commit is None


@patch("os.path.exists")
@patch("subprocess.run")
def test_install_git_plugin_existing_repo(
    mock_run: MagicMock, mock_exists: MagicMock
) -> None:
    mock_exists.return_value = True
    installer: pi.PluginInstaller = make_installer_with_plugins()
    success: bool
    tag: Optional[str]
    success, tag = installer._install_git_plugin({"name": "foo", "url": "owner/repo"})
    assert success is True
    assert tag is None
    mock_run.assert_not_called()


@patch("os.path.exists")
@patch("subprocess.run")
def test_install_git_plugin_clone_checkout_success(
    mock_run: MagicMock, mock_exists: MagicMock
) -> None:
    mock_exists.return_value = False
    mock_run.return_value = MagicMock()
    installer: pi.PluginInstaller = make_installer_with_plugins()

    plugin: Dict[str, Any] = {"name": "foo", "url": "owner/repo", "tag": "v1.0"}
    success: bool
    used_tag: Optional[str]
    success, used_tag = installer._install_git_plugin(plugin)

    assert success is True
    assert used_tag == "v1.0"
    assert mock_run.call_count >= 3
    mock_run.assert_any_call(
        ["git", "clone", "https://github.com/owner/repo", "/plugins/dir/foo"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    mock_run.assert_any_call(
        ["git", "fetch", "--tags"],
        cwd="/plugins/dir/foo",
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    mock_run.assert_any_call(
        ["git", "checkout", "v1.0"],
        cwd="/plugins/dir/foo",
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@patch("os.path.exists")
@patch("subprocess.run")
@patch.object(pi.PluginInstaller, "_get_latest_tag", return_value="v2.0")
def test_install_git_plugin_without_tag_uses_latest(
    mock_get_latest_tag: MagicMock, mock_run: MagicMock, mock_exists: MagicMock
) -> None:
    mock_exists.return_value = False
    mock_run.return_value = MagicMock()
    installer: pi.PluginInstaller = make_installer_with_plugins()

    plugin: Dict[str, Any] = {"name": "foo", "url": "owner/repo"}
    success: bool
    used_tag: Optional[str]
    success, used_tag = installer._install_git_plugin(plugin)

    assert success is True
    assert used_tag == "v2.0"
    mock_get_latest_tag.assert_called_once()


@patch("os.path.exists")
@patch("subprocess.run", side_effect=Exception("git error"))
def test_install_git_plugin_failure_returns_false(
    mock_run: MagicMock, mock_exists: MagicMock
) -> None:
    mock_exists.return_value = False
    installer: pi.PluginInstaller = make_installer_with_plugins()

    success: bool
    tag: Optional[str]
    success, tag = installer._install_git_plugin({"name": "foo", "url": "owner/repo"})
    assert success is False
    assert tag is None


@patch("os.path.exists")
@patch("subprocess.run")
def test_install_git_plugin_with_progress_already_exists_progress_reported(
    mock_run: MagicMock, mock_exists: MagicMock
) -> None:
    mock_exists.return_value = True
    progress_calls: List[int] = []

    def progress_callback(p: int) -> None:
        progress_calls.append(p)

    installer: pi.PluginInstaller = make_installer_with_plugins()
    result: Tuple[bool, Optional[str]] = installer._install_git_plugin_with_progress(
        {"name": "foo", "url": "owner/repo", "tag": "v1.0"},
        progress_callback=progress_callback,
    )
    assert result == (True, "v1.0")
    assert progress_calls[-1] == 100
    mock_run.assert_not_called()


@patch("os.path.exists")
@patch("subprocess.run")
@patch.object(pi.PluginInstaller, "_get_latest_tag", return_value="v2.0")
def test_install_git_plugin_with_progress_full_flow(
    mock_get_latest_tag: MagicMock, mock_run: MagicMock, mock_exists: MagicMock
) -> None:
    mock_exists.return_value = False

    progress_calls: List[int] = []

    def progress_callback(p: int) -> None:
        progress_calls.append(p)

    mock_run.return_value = MagicMock()
    installer: pi.PluginInstaller = make_installer_with_plugins()
    plugin: Dict[str, Any] = {"name": "foo", "url": "owner/repo"}
    success: bool
    tag: Optional[str]
    success, tag = installer._install_git_plugin_with_progress(
        plugin, progress_callback
    )
    assert success is True
    assert tag == "v2.0"
    assert progress_calls[0] == 5
    assert progress_calls[-1] == 90


@patch("os.path.exists")
@patch("subprocess.run", side_effect=Exception("git fail"))
def test_install_git_plugin_with_progress_failure_reports_zero_progress(
    mock_run: MagicMock, mock_exists: MagicMock
) -> None:
    mock_exists.return_value = False
    progress_calls: List[int] = []

    def progress_callback(p: int) -> None:
        progress_calls.append(p)

    installer: pi.PluginInstaller = make_installer_with_plugins()
    success: bool
    tag: Optional[str]
    success, tag = installer._install_git_plugin_with_progress(
        {"name": "foo", "url": "owner/repo"}, progress_callback
    )
    assert success is False
    assert tag is None


@patch("core.lock_file_manager.read_lock_file", return_value={"plugins": []})
@patch("core.lock_file_manager.write_lock_file")
@patch(
    "core.pluginInstaller.PluginInstaller._get_commit_hash", return_value="commit123"
)
@patch(
    "core.pluginInstaller.PluginInstaller._get_current_timestamp",
    return_value="timestamp",
)
def test_update_lock_file_adds_plugin(
    mock_timestamp: MagicMock,
    mock_commit_hash: MagicMock,
    mock_write: MagicMock,
    mock_read: MagicMock,
) -> None:
    installer: pi.PluginInstaller = make_installer_with_plugins()
    plugin: Dict[str, Any] = {
        "name": "foo",
        "url": "owner/repo",
        "source": ["source1", "source2"],
        "enabled": True,
        "skip_auto_update": False,
    }
    installer._update_lock_file(plugin, "v1.0")
    mock_read.assert_called_once()
    mock_write.assert_called_once()
    args: Any = mock_write.call_args[0][0]
    assert any(p["name"] == "foo" for p in args["plugins"])


def test_get_current_timestamp_format() -> None:
    installer: pi.PluginInstaller = make_installer_with_plugins()
    timestamp: str = installer._get_current_timestamp()
    # Check if timestamp can be parsed as datetime
    datetime.datetime.strptime(timestamp[:19], "%Y-%m-%d %H:%M:%S")


@patch("core.pluginInstaller.PluginInstaller._install_git_plugin")
@patch("core.pluginInstaller.PluginInstaller._update_lock_file")
def test_install_all_plugins_success(
    mock_update: MagicMock, mock_install: MagicMock, capsys: Any
) -> None:
    mock_install.return_value = (True, "v1.0")
    plugins: List[Dict[str, Any]] = [{"name": "test-plugin", "url": "owner/repo"}]
    installer: pi.PluginInstaller = make_installer_with_plugins(plugins)
    installer.install_all_plugins()

    mock_install.assert_called_once()
    mock_update.assert_called_once()
    captured = capsys.readouterr()
    assert "Installing test-plugin" in captured.out
    assert "Successfully installed test-plugin @ v1.0" in captured.out


@patch("core.pluginInstaller.PluginInstaller._install_git_plugin")
@patch("core.pluginInstaller.PluginInstaller._update_lock_file")
def test_install_all_plugins_failure(
    mock_update: MagicMock, mock_install: MagicMock, capsys: Any
) -> None:
    mock_install.return_value = (False, None)
    plugins: List[Dict[str, Any]] = [{"name": "test-plugin", "url": "owner/repo"}]
    installer: pi.PluginInstaller = make_installer_with_plugins(plugins)
    installer.install_all_plugins()

    mock_install.assert_called_once()
    mock_update.assert_not_called()
    captured = capsys.readouterr()
    assert "Failed to install test-plugin" in captured.out

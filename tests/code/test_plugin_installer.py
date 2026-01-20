import datetime
import subprocess
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from core import PluginInstaller


def make_installer_with_plugins(
    plugins: list[dict[str, Any]] | None = None,
) -> PluginInstaller:
    if plugins is None:
        plugins = [{"name": "foo", "url": "owner/repo"}]
    return PluginInstaller(plugins, "/plugins/dir", "/tmux.conf")


def test_get_latest_tag_returns_tag() -> None:
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "v1.0.0\nv0.9.0\n"
        tag = make_installer_with_plugins()._get_latest_tag("dummy_path")
        assert tag == "v1.0.0"


def test_get_latest_tag_empty_returns_none() -> None:
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = ""
        tag = make_installer_with_plugins()._get_latest_tag("dummy_path")
        assert tag is None


def test_get_latest_tag_called_process_error_returns_none() -> None:
    with patch(
        "subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "cmd"),
    ):
        tag = make_installer_with_plugins()._get_latest_tag("dummy_path")
        assert tag is None


def test_get_commit_hash_success() -> None:
    installer = make_installer_with_plugins()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "commit_hash_123"
        commit = installer._get_commit_hash({"name": "foo"})
        assert commit == "commit_hash_123"


def test_get_commit_hash_failure_returns_none() -> None:
    installer = make_installer_with_plugins()
    with patch(
        "subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "cmd"),
    ):
        commit = installer._get_commit_hash({"name": "foo"})
        assert commit is None


def test_get_current_timestamp_format() -> None:
    installer = make_installer_with_plugins()
    timestamp = installer._get_current_timestamp()
    datetime.datetime.strptime(timestamp[:19], "%Y-%m-%d %H:%M:%S")


@patch("core.PluginInstaller._get_latest_tag", return_value=None)
@patch("subprocess.run")
@patch("core.lock_file_manager.read_lock_file", return_value={"plugins": []})
@patch("core.lock_file_manager.write_lock_file")
def test_install_new_plugin_success(
    mock_write: MagicMock,
    mock_read: MagicMock,
    mock_run: MagicMock,
    mock_get_latest_tag: MagicMock,
) -> None:
    mock_run.return_value = MagicMock()
    installer = make_installer_with_plugins()

    plugin = {"name": "foo", "url": "owner/repo"}

    success, tag = installer.install_git_plugin(plugin)

    assert success is True
    assert tag is None
    mock_run.assert_called()
    mock_write.assert_called_once()


@patch("os.path.exists", return_value=True)
@patch(
    "core.lock_file_manager.read_lock_file",
    return_value={"plugins": [{"name": "foo", "git": {"tag": "v1.2.3"}}]},
)
@patch("subprocess.run")
def test_install_existing_plugin_without_force(
    mock_run: MagicMock,
    mock_read: MagicMock,
    mock_exists: MagicMock,
) -> None:
    installer = make_installer_with_plugins()

    success, tag = installer.install_git_plugin({"name": "foo", "url": "owner/repo"})

    assert success is True
    assert tag == "v1.2.3"
    mock_run.assert_not_called()


@patch("os.path.exists", return_value=True)
@patch("shutil.rmtree")
@patch("subprocess.run")
@patch("core.lock_file_manager.read_lock_file", return_value={"plugins": []})
@patch("core.lock_file_manager.write_lock_file")
def test_install_existing_plugin_with_force(
    mock_write: MagicMock,
    mock_read: MagicMock,
    mock_run: MagicMock,
    mock_rmtree: MagicMock,
    mock_exists: MagicMock,
) -> None:
    mock_run.return_value = MagicMock()
    installer = make_installer_with_plugins()

    success, _ = installer.install_git_plugin(
        {"name": "foo", "url": "owner/repo"},
        force=True,
    )

    assert success is True
    mock_rmtree.assert_called_once()
    mock_run.assert_called()


@patch("subprocess.run")
@patch("core.PluginInstaller._verify_git_tag_exists", return_value=False)
def test_install_with_missing_tag_raises(
    mock_verify: MagicMock,
    mock_run: MagicMock,
) -> None:
    installer = make_installer_with_plugins()

    with pytest.raises(ValueError):
        installer.install_git_plugin(
            {"name": "foo", "url": "owner/repo", "tag": "v9.9.9"}
        )


@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file", return_value={"plugins": []})
@patch("subprocess.run")
def test_progress_callback_called(
    mock_run: MagicMock,
    mock_read: MagicMock,
    mock_write: MagicMock,
) -> None:
    progress: list[int] = []

    def progress_callback(p: int) -> None:
        progress.append(p)

    mock_run.return_value = MagicMock()
    installer = make_installer_with_plugins()

    success, _ = installer.install_git_plugin(
        {"name": "foo", "url": "owner/repo"},
        progress_callback=progress_callback,
    )

    assert success is True
    assert progress
    assert progress[-1] == 100


@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file", return_value={"plugins": []})
@patch("subprocess.run")
@patch("os.walk")
def test_install_discovers_tmux_sources_when_not_provided(
    mock_walk: MagicMock,
    mock_run: MagicMock,
    mock_read: MagicMock,
    mock_write: MagicMock,
) -> None:
    mock_run.return_value = MagicMock()

    mock_walk.return_value = [
        ("/plugins/dir/foo", [], ["init.tmux", "extra.tmux", "README.md"]),
        ("/plugins/dir/foo/sub", [], ["nested.tmux"]),
    ]

    installer = make_installer_with_plugins()

    success, _ = installer.install_git_plugin({"name": "foo", "url": "owner/repo"})

    assert success is True
    mock_write.assert_called_once()

    written_lock = mock_write.call_args[0][0]
    plugin = written_lock["plugins"][0]

    assert sorted(plugin["source"]) == sorted(
        [
            "/plugins/dir/foo/init.tmux",
            "/plugins/dir/foo/extra.tmux",
            "/plugins/dir/foo/sub/nested.tmux",
        ]
    )


@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file", return_value={"plugins": []})
@patch("subprocess.run")
@patch("os.walk")
def test_install_respects_explicit_source_and_skips_discovery(
    mock_walk: MagicMock,
    mock_run: MagicMock,
    mock_read: MagicMock,
    mock_write: MagicMock,
) -> None:
    mock_run.return_value = MagicMock()

    installer = make_installer_with_plugins()

    success, _ = installer.install_git_plugin(
        {
            "name": "foo",
            "url": "owner/repo",
            "source": ["plugin.tmux"],
        }
    )

    assert success is True
    mock_walk.assert_not_called()

    written_lock = mock_write.call_args[0][0]
    plugin = written_lock["plugins"][0]

    assert plugin["source"] == ["/plugins/dir/foo/plugin.tmux"]

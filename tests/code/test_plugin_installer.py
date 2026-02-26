import asyncio
import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from core import PluginInstaller


class AsyncProcessMock:
    def __init__(self, returncode: int = 0, stdout: bytes = b""):
        self.returncode = returncode
        self._stdout = stdout

    async def wait(self) -> int:
        return self.returncode

    async def communicate(self) -> tuple[bytes, bytes]:
        return (self._stdout, b"")


def make_installer_with_plugins(
    plugins: list[dict[str, Any]] | None = None,
) -> PluginInstaller:
    if plugins is None:
        plugins = [{"name": "foo", "url": "owner/repo"}]
    return PluginInstaller(plugins, "/plugins/dir", "/tmux.conf")


@pytest.mark.asyncio
async def test_get_latest_tag_returns_tag() -> None:
    installer = make_installer_with_plugins()

    mock_process = AsyncProcessMock(
        returncode=0,
        stdout=b"v1.0.0\nv0.9.0\n",
    )

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        tag = await installer._get_latest_tag("dummy_path")

    assert tag == "v1.0.0"


@pytest.mark.asyncio
async def test_get_latest_tag_empty_returns_none() -> None:
    installer = make_installer_with_plugins()

    mock_process = AsyncProcessMock(returncode=0, stdout=b"")

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        tag = await installer._get_latest_tag("dummy_path")

    assert tag is None


@pytest.mark.asyncio
async def test_get_commit_hash_success() -> None:
    installer = make_installer_with_plugins()

    mock_process = AsyncProcessMock(
        returncode=0,
        stdout=b"commit_hash_123",
    )

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        commit = await installer._get_commit_hash({"name": "foo"})

    assert commit == "commit_hash_123"


@pytest.mark.asyncio
async def test_get_commit_hash_failure_returns_none() -> None:
    installer = make_installer_with_plugins()

    mock_process = AsyncProcessMock(returncode=1, stdout=b"")

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        commit = await installer._get_commit_hash({"name": "foo"})

    assert commit is None


def test_get_current_timestamp_format() -> None:
    installer = make_installer_with_plugins()
    timestamp = installer._get_current_timestamp()
    datetime.datetime.fromisoformat(timestamp)


@pytest.mark.asyncio
async def test_install_new_plugin_success() -> None:
    installer = make_installer_with_plugins()

    mock_process = AsyncProcessMock(returncode=0, stdout=b"")

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        result = await installer.install_git_plugin(
            {"name": "foo", "url": "owner/repo"}
        )

    assert result["plugin"]["name"] == "foo"


@pytest.mark.asyncio
async def test_install_existing_plugin_without_force() -> None:
    installer = make_installer_with_plugins()

    with (
        patch("os.path.exists", return_value=True),
        patch(
            "core.lock_file_manager.read_lock_file",
            return_value={
                "plugins": [
                    {"name": "foo", "git": {"tag": "v1.2.3", "commit_hash": "abc"}}
                ]
            },
        ),
    ):
        result = await installer.install_git_plugin(
            {"name": "foo", "url": "owner/repo"}
        )

    assert result["used_tag"] == "v1.2.3"


@pytest.mark.asyncio
async def test_install_existing_plugin_with_force() -> None:
    installer = make_installer_with_plugins()

    mock_process = AsyncProcessMock(returncode=0, stdout=b"")

    with (
        patch("os.path.exists", return_value=True),
        patch("shutil.rmtree"),
        patch("asyncio.create_subprocess_exec", return_value=mock_process),
    ):
        result = await installer.install_git_plugin(
            {"name": "foo", "url": "owner/repo"},
            force=True,
        )

    assert result["plugin"]["name"] == "foo"


@pytest.mark.asyncio
async def test_install_with_missing_tag_raises() -> None:
    installer = make_installer_with_plugins()

    mock_process = AsyncProcessMock(returncode=0, stdout=b"")

    with (
        patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_process,
        ),
        patch.object(
            installer,
            "_verify_git_tag_exists",
            return_value=False,
        ),
    ):
        with pytest.raises(ValueError):
            await installer.install_git_plugin(
                {"name": "foo", "url": "owner/repo", "tag": "v9.9.9"}
            )


@pytest.mark.asyncio
async def test_progress_callback_called() -> None:
    installer = make_installer_with_plugins()
    progress: list[int] = []

    def progress_callback(p: int) -> None:
        progress.append(p)

    mock_process = AsyncProcessMock(returncode=0, stdout=b"")

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        await installer.install_git_plugin(
            {"name": "foo", "url": "owner/repo"},
            progress_callback=progress_callback,
        )

    assert progress
    assert progress[-1] == 100


@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file", return_value={"plugins": []})
def test_update_lock_file(mock_read: MagicMock, mock_write: MagicMock) -> None:
    installer = make_installer_with_plugins()

    results = [
        {
            "plugin": {"name": "foo", "url": "owner/repo"},
            "used_tag": "v1.0.0",
            "commit_hash": "abc123",
        }
    ]

    installer.update_lock_file(results)

    mock_write.assert_called_once()


@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file", return_value={"plugins": []})
@patch("os.walk")
def test_update_lock_file_discovers_tmux_sources(
    mock_walk: MagicMock,
    mock_read: MagicMock,
    mock_write: MagicMock,
) -> None:
    mock_walk.return_value = [
        ("/plugins/dir/foo", [], ["init.tmux", "extra.tmux", "README.md"]),
        ("/plugins/dir/foo/sub", [], ["nested.tmux"]),
    ]

    installer = make_installer_with_plugins()

    installer.update_lock_file([
        {
            "plugin": {"name": "foo", "url": "owner/repo"},
            "used_tag": "v1.0.0",
            "commit_hash": "abc123",
        }
    ])

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
@patch("os.walk")
def test_update_lock_file_respects_explicit_source(
    mock_walk: MagicMock,
    mock_read: MagicMock,
    mock_write: MagicMock,
) -> None:
    installer = make_installer_with_plugins()

    installer.update_lock_file([
        {
            "plugin": {"name": "foo", "url": "owner/repo", "source": ["plugin.tmux"]},
            "used_tag": "v1.0.0",
            "commit_hash": "abc123",
        }
    ])

    mock_walk.assert_not_called()
    written_lock = mock_write.call_args[0][0]
    plugin = written_lock["plugins"][0]
    assert plugin["source"] == ["/plugins/dir/foo/plugin.tmux"]


@patch("core.lock_file_manager.write_lock_file")
@patch(
    "core.lock_file_manager.read_lock_file",
    return_value={
        "plugins": [
            {"name": "charlie", "enabled": True},
            {"name": "alpha", "enabled": True},
            {"name": "bravo", "enabled": True},
        ]
    },
)
def test_update_lock_file_reorders_to_match_config(
    mock_read: MagicMock,
    mock_write: MagicMock,
) -> None:
    config = [
        {"name": "alpha", "url": "owner/alpha"},
        {"name": "bravo", "url": "owner/bravo"},
        {"name": "charlie", "url": "owner/charlie"},
    ]
    installer = PluginInstaller(config, "/plugins/dir", "/tmux.conf")

    installer.update_lock_file([
        {
            "plugin": {"name": "charlie", "url": "owner/charlie"},
            "used_tag": None,
            "commit_hash": None,
        }
    ])

    written_lock = mock_write.call_args[0][0]
    names = [p["name"] for p in written_lock["plugins"]]
    assert names == ["alpha", "bravo", "charlie"]


@patch("core.lock_file_manager.write_lock_file")
@patch(
    "core.lock_file_manager.read_lock_file",
    return_value={"plugins": []},
)
def test_update_lock_file_preserves_list_format_order(
    mock_read: MagicMock,
    mock_write: MagicMock,
) -> None:
    config = [
        {"name": "third", "url": "owner/third"},
        {"name": "first", "url": "owner/first"},
        {"name": "second", "url": "owner/second"},
    ]
    installer = PluginInstaller(config, "/plugins/dir", "/tmux.conf")

    installer.update_lock_file([
        {
            "plugin": {"name": "first", "url": "owner/first"},
            "used_tag": None,
            "commit_hash": None,
        }
    ])

    written_lock = mock_write.call_args[0][0]
    names = [p["name"] for p in written_lock["plugins"]]
    assert names == ["first"]

    # Simulate second install: "first" already in lock file
    mock_read.return_value = written_lock
    installer.update_lock_file([
        {
            "plugin": {"name": "third", "url": "owner/third"},
            "used_tag": None,
            "commit_hash": None,
        }
    ])

    written_lock = mock_write.call_args[0][0]
    names = [p["name"] for p in written_lock["plugins"]]
    assert names == ["third", "first"]

    # Simulate third install
    mock_read.return_value = written_lock
    installer.update_lock_file([
        {
            "plugin": {"name": "second", "url": "owner/second"},
            "used_tag": None,
            "commit_hash": None,
        }
    ])

    written_lock = mock_write.call_args[0][0]
    names = [p["name"] for p in written_lock["plugins"]]
    assert names == ["third", "first", "second"]


@patch("core.lock_file_manager.write_lock_file")
@patch(
    "core.lock_file_manager.read_lock_file",
    return_value={
        "plugins": [
            {"name": "extra", "enabled": True},
        ]
    },
)
def test_update_lock_file_keeps_unknown_plugins_at_end(
    mock_read: MagicMock,
    mock_write: MagicMock,
) -> None:
    config = [
        {"name": "alpha", "url": "owner/alpha"},
        {"name": "bravo", "url": "owner/bravo"},
    ]
    installer = PluginInstaller(config, "/plugins/dir", "/tmux.conf")

    installer.update_lock_file([
        {
            "plugin": {"name": "alpha", "url": "owner/alpha"},
            "used_tag": None,
            "commit_hash": None,
        }
    ])

    written_lock = mock_write.call_args[0][0]
    names = [p["name"] for p in written_lock["plugins"]]
    assert names == ["alpha", "extra"]

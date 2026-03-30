from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core import PluginRemover


def make_remover() -> PluginRemover:
    return PluginRemover("/fake/path")


@pytest.mark.asyncio
@patch("core.lock_file_manager.read_lock_file", return_value={"plugins": []})
async def test_get_installed_plugins_empty(mock_read: MagicMock) -> None:
    remover = make_remover()
    plugins = await remover.get_installed_plugins()
    assert plugins == []


@pytest.mark.asyncio
@patch("core.lock_file_manager.read_lock_file")
@patch.object(PluginRemover, "_get_directory_size", new_callable=AsyncMock)
async def test_get_installed_plugins_with_data(
    mock_size: AsyncMock,
    mock_read: MagicMock,
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

    mock_size.return_value = "5.2M"

    remover = make_remover()
    plugins = await remover.get_installed_plugins()

    plugin = plugins[0]
    assert plugin["name"] == "test-plugin"
    assert plugin["version"] == "v1.0.0"
    assert plugin["size"] == "5.2M"
    assert plugin["enabled"] is True
    assert plugin["installed"] == "2024-10-01"


@pytest.mark.asyncio
@patch("core.lock_file_manager.read_lock_file")
@patch.object(PluginRemover, "_remove_directory", new_callable=AsyncMock)
async def test_remove_plugin_success(
    mock_remove: AsyncMock,
    mock_read: MagicMock,
) -> None:
    mock_read.return_value = {"plugins": [{"name": "plugin1"}]}

    remover = make_remover()
    result = await remover.remove_plugin("plugin1")

    assert result == {"plugin_name": "plugin1"}
    mock_remove.assert_awaited_once()


@pytest.mark.asyncio
@patch("core.lock_file_manager.read_lock_file")
async def test_remove_plugin_not_in_lock(mock_read: MagicMock) -> None:
    mock_read.return_value = {"plugins": [{"name": "plugin1"}]}

    remover = make_remover()
    result = await remover.remove_plugin("missing")

    assert result is None


@pytest.mark.asyncio
@patch("core.lock_file_manager.read_lock_file")
@patch.object(
    PluginRemover,
    "_remove_directory",
    new_callable=AsyncMock,
    side_effect=OSError("permission denied"),
)
async def test_remove_plugin_directory_failure_raises(
    mock_remove: AsyncMock,
    mock_read: MagicMock,
) -> None:
    mock_read.return_value = {"plugins": [{"name": "plugin1"}]}

    remover = make_remover()

    with pytest.raises(OSError):
        await remover.remove_plugin("plugin1")


@pytest.mark.asyncio
@patch("core.lock_file_manager.read_lock_file")
@patch.object(PluginRemover, "_remove_directory", new_callable=AsyncMock)
async def test_remove_plugin_progress_callback(
    mock_remove: AsyncMock,
    mock_read: MagicMock,
) -> None:
    mock_read.return_value = {"plugins": [{"name": "plugin1"}]}

    calls: list[tuple[str, int]] = []

    def cb(name: str, p: int) -> None:
        calls.append((name, p))

    remover = make_remover()
    await remover.remove_plugin("plugin1", progress_callback=cb)

    assert calls == [
        ("plugin1", 10),
        ("plugin1", 40),
        ("plugin1", 100),
    ]


@pytest.mark.asyncio
@patch("core.lock_file_manager.read_lock_file", side_effect=OSError("read error"))
async def test_remove_plugin_read_lock_failure_raises(
    mock_read: MagicMock,
) -> None:
    calls: list[tuple[str, int]] = []

    def cb(name: str, p: int) -> None:
        calls.append((name, p))

    remover = make_remover()

    with pytest.raises(OSError):
        await remover.remove_plugin("plugin1", progress_callback=cb)

    assert calls[-1] == ("plugin1", 0)


@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file")
def test_update_lock_file_success(
    mock_read: MagicMock,
    mock_write: MagicMock,
) -> None:
    mock_read.return_value = {"plugins": [{"name": "plugin1"}, {"name": "plugin2"}]}

    remover = make_remover()

    updated = remover.update_lock_file([{"plugin_name": "plugin1"}])

    assert updated is True
    mock_write.assert_called_once()

    written = mock_write.call_args[0][0]
    assert len(written["plugins"]) == 1
    assert written["plugins"][0]["name"] == "plugin2"


@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file")
def test_update_lock_file_no_changes(
    mock_read: MagicMock,
    mock_write: MagicMock,
) -> None:
    mock_read.return_value = {"plugins": [{"name": "plugin1"}]}

    remover = make_remover()

    updated = remover.update_lock_file([{"plugin_name": "missing"}])

    assert updated is False
    mock_write.assert_not_called()

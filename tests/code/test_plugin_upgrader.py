from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core import PluginUpgrader


def make_plan(
    *,
    update_type: str = "tag",
    update_available: bool = True,
) -> dict[str, Any]:
    return {
        "name": "plugin1",
        "_internal": {
            "type": update_type,
            "update_available": update_available,
            "plugin_path": "/fake/plugins/plugin1",
            "new_tag": "v2.0.0",
            "new_commit": "def456",
        },
    }


@pytest.mark.asyncio
@patch.object(
    PluginUpgrader, "_upgrade_to_tag", new_callable=AsyncMock, return_value=True
)
@patch.object(
    PluginUpgrader,
    "_get_local_head_commit",
    new_callable=AsyncMock,
    return_value="finalcommit",
)
async def test_upgrade_plugin_tag_success(
    mock_head: AsyncMock,
    mock_upgrade: AsyncMock,
) -> None:
    upgrader = PluginUpgrader()
    plan = make_plan(update_type="tag")

    progress_calls: list[int] = []

    def progress_cb(p: int) -> None:
        progress_calls.append(p)

    result = await upgrader.upgrade_plugin(plan, progress_callback=progress_cb)

    assert result is not None
    assert result["plugin_name"] == "plugin1"
    assert result["new_commit"] == "finalcommit"
    mock_upgrade.assert_awaited_once()

    assert progress_calls[0] == 10
    assert progress_calls[-1] == 100


@pytest.mark.asyncio
@patch.object(
    PluginUpgrader, "_upgrade_to_commit", new_callable=AsyncMock, return_value=True
)
@patch.object(
    PluginUpgrader,
    "_get_local_head_commit",
    new_callable=AsyncMock,
    return_value="finalcommit",
)
async def test_upgrade_plugin_commit_success(
    mock_head: AsyncMock,
    mock_upgrade: AsyncMock,
) -> None:
    upgrader = PluginUpgrader()
    plan = make_plan(update_type="commit")

    result = await upgrader.upgrade_plugin(plan)

    assert result is not None
    assert result["plugin_name"] == "plugin1"
    mock_upgrade.assert_awaited_once()


@pytest.mark.asyncio
async def test_upgrade_plugin_no_update_available() -> None:
    upgrader = PluginUpgrader()
    plan = make_plan(update_available=False)

    result = await upgrader.upgrade_plugin(plan)

    assert result is None


@pytest.mark.asyncio
@patch.object(
    PluginUpgrader, "_upgrade_to_tag", new_callable=AsyncMock, return_value=False
)
async def test_upgrade_plugin_tag_failure_returns_none(
    mock_upgrade: AsyncMock,
) -> None:
    upgrader = PluginUpgrader()
    plan = make_plan(update_type="tag")

    progress_calls: list[int] = []

    def progress_cb(p: int) -> None:
        progress_calls.append(p)

    result = await upgrader.upgrade_plugin(plan, progress_callback=progress_cb)

    assert result is None
    assert progress_calls[-1] == 0


@pytest.mark.asyncio
@patch.object(
    PluginUpgrader, "_get_local_head_commit", new_callable=AsyncMock, return_value=None
)
@patch.object(
    PluginUpgrader, "_upgrade_to_tag", new_callable=AsyncMock, return_value=True
)
async def test_upgrade_plugin_missing_head_commit_returns_none(
    mock_upgrade: AsyncMock,
    mock_head: AsyncMock,
) -> None:
    upgrader = PluginUpgrader()
    plan = make_plan(update_type="tag")

    result = await upgrader.upgrade_plugin(plan)

    assert result is None


# ---------- Lock File Tests ----------


@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file")
def test_update_lock_file_success(
    mock_read: MagicMock,
    mock_write: MagicMock,
) -> None:
    mock_read.return_value = {
        "plugins": [
            {
                "name": "plugin1",
                "git": {
                    "commit_hash": "old",
                    "tag": "v1.0.0",
                },
            }
        ]
    }

    upgrader = PluginUpgrader()

    results = [
        {
            "plugin_name": "plugin1",
            "new_tag": "v2.0.0",
            "new_commit": "def456",
            "last_pull": "timestamp",
        }
    ]

    updated = upgrader.update_lock_file(results)

    assert updated is True
    mock_write.assert_called_once()

    written = mock_write.call_args[0][0]
    plugin_git = written["plugins"][0]["git"]

    assert plugin_git["tag"] == "v2.0.0"
    assert plugin_git["commit_hash"] == "def456"
    assert plugin_git["last_pull"] == "timestamp"


@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file")
def test_update_lock_file_no_results(
    mock_read: MagicMock,
    mock_write: MagicMock,
) -> None:
    upgrader = PluginUpgrader()

    updated = upgrader.update_lock_file([])

    assert updated is False
    mock_write.assert_not_called()

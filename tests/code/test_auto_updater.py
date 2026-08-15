import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core import lock_file_manager as lfm
from core.auto_updater import AutoUpdater


def make_lock(
    plugins: list[dict[str, Any]] | None = None,
    metadata: lfm.LockMetadata | None = None,
) -> lfm.LockData:
    lock: lfm.LockData = {"plugins": plugins or []}
    if metadata is not None:
        lock["metadata"] = metadata
    return lock


@pytest.mark.asyncio
async def test_run_upgrades_skips_when_not_due() -> None:
    updater = AutoUpdater("/plugins")

    with (
        patch(
            "core.lock_file_manager.read_lock_file",
            return_value=make_lock(
                metadata={
                    "last_auto_update_check": int(time.time()),
                    "last_self_update_check": 0,
                }
            ),
        ),
        patch.object(updater, "_check_for_updates", new_callable=AsyncMock) as check,
        patch.object(updater, "_record_check") as record,
    ):
        await updater.run_upgrades()

    check.assert_not_called()
    record.assert_not_called()


@pytest.mark.asyncio
async def test_run_upgrades_executes_available_updates() -> None:
    updater = AutoUpdater("/plugins")

    candidates: list[dict[str, Any]] = [{"name": "spot"}]
    updates: list[dict[str, Any]] = [
        {"name": "spot", "_internal": {"update_available": True}}
    ]

    with (
        patch(
            "core.lock_file_manager.read_lock_file",
            return_value=make_lock(plugins=candidates),
        ),
        patch.object(updater, "_should_run", return_value=True),
        patch.object(
            updater, "_check_for_updates", new=AsyncMock(return_value=updates)
        ),
        patch.object(updater, "_upgrade_plugins", new=AsyncMock()) as upgrade,
        patch.object(updater, "_record_check") as record,
    ):
        await updater.run_upgrades()

    upgrade.assert_awaited_once_with(updates)
    record.assert_called_once()


@pytest.mark.asyncio
async def test_run_upgrades_no_updates_only_records_check() -> None:
    updater = AutoUpdater("/plugins")

    plugins: list[dict[str, Any]] = [{"name": "spot"}]

    with (
        patch(
            "core.lock_file_manager.read_lock_file",
            return_value=make_lock(plugins=plugins),
        ),
        patch.object(updater, "_should_run", return_value=True),
        patch.object(updater, "_check_for_updates", new=AsyncMock(return_value=[])),
        patch.object(updater, "_upgrade_plugins", new=AsyncMock()) as upgrade,
        patch.object(updater, "_record_check") as record,
    ):
        await updater.run_upgrades()

    upgrade.assert_not_called()
    record.assert_called_once()


@pytest.mark.asyncio
async def test_check_for_updates_filters_only_available() -> None:
    updater = AutoUpdater("/plugins")

    available = {"name": "spot", "_internal": {"update_available": True}}
    unavailable = {"name": "cpu", "_internal": {"update_available": False}}

    with patch(
        "core.auto_updater.PluginUpdater.check_for_update",
        new=AsyncMock(side_effect=[available, unavailable]),
    ):
        result = await updater._check_for_updates([{"name": "spot"}, {"name": "cpu"}])

    assert result == [available]


@pytest.mark.asyncio
async def test_upgrade_plugins_updates_lock_file() -> None:
    updater = AutoUpdater("/plugins")

    result = {"plugin_name": "spot", "new_tag": "v2.0.0"}

    with (
        patch(
            "core.auto_updater.PluginUpgrader.upgrade_plugin",
            new=AsyncMock(return_value=result),
        ),
        patch("core.auto_updater.PluginUpgrader.update_lock_file") as write_lock,
    ):
        await updater._upgrade_plugins([{"name": "spot"}])

    write_lock.assert_called_once_with([result])


@pytest.mark.asyncio
async def test_upgrade_plugins_ignores_failed_results() -> None:
    updater = AutoUpdater("/plugins")

    with (
        patch(
            "core.auto_updater.PluginUpgrader.upgrade_plugin",
            new=AsyncMock(side_effect=[RuntimeError("boom"), None]),
        ),
        patch("core.auto_updater.PluginUpgrader.update_lock_file") as write_lock,
    ):
        await updater._upgrade_plugins([{"name": "a"}, {"name": "b"}])

    write_lock.assert_not_called()


def test_should_run_without_metadata_returns_true() -> None:
    updater = AutoUpdater("/plugins")

    assert updater._should_run(make_lock())


def test_should_run_after_interval_returns_true() -> None:
    updater = AutoUpdater("/plugins")

    lock = make_lock(
        metadata={
            "last_auto_update_check": int(time.time()) - 90000,
            "last_self_update_check": 0,
        }
    )

    assert updater._should_run(lock)


def test_should_run_before_interval_returns_false() -> None:
    updater = AutoUpdater("/plugins")

    lock = make_lock(
        metadata={
            "last_auto_update_check": int(time.time()) - 60,
            "last_self_update_check": 0,
        }
    )

    assert not updater._should_run(lock)


def test_should_run_uses_latest_of_auto_and_self() -> None:
    updater = AutoUpdater("/plugins")

    lock = make_lock(
        metadata={
            "last_auto_update_check": int(time.time()) - 90000,
            "last_self_update_check": int(time.time()) - 30,
        }
    )

    assert not updater._should_run(lock)


@patch("core.lock_file_manager.write_lock_file")
@patch(
    "core.lock_file_manager.read_lock_file",
    return_value=make_lock(
        metadata={
            "last_auto_update_check": 1,
            "last_self_update_check": 42,
        }
    ),
)
def test_record_check_preserves_self_update(
    mock_read: MagicMock,
    mock_write: MagicMock,
) -> None:
    updater = AutoUpdater("/plugins")

    before = int(time.time())
    updater._record_check()
    after = int(time.time())

    written: lfm.LockData = mock_write.call_args[0][0]

    assert written["metadata"]["last_self_update_check"] == 42
    assert before <= written["metadata"]["last_auto_update_check"] <= after


def test_get_candidates_skips_auto_update_plugins() -> None:
    updater = AutoUpdater("/plugins")

    plugins: list[dict[str, Any]] = [
        {"name": "spot"},
        {"name": "cpu", "skip_auto_update": True},
        {"name": "flash-copy", "skip_auto_update": False},
    ]

    result = updater._get_candidates(plugins)

    assert [p["name"] for p in result] == ["spot", "flash-copy"]

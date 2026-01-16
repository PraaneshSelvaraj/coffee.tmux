import subprocess
from typing import Any
from unittest.mock import MagicMock, patch

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


@patch.object(PluginUpgrader, "_upgrade_to_tag")
@patch.object(PluginUpgrader, "_get_local_head_commit", return_value="finalcommit")
@patch.object(PluginUpgrader, "_write_lockfile_update")
def test_upgrade_plugin_tag_success(
    mock_write: MagicMock,
    mock_head: MagicMock,
    mock_upgrade: MagicMock,
) -> None:
    upgrader = PluginUpgrader()
    plan = make_plan(update_type="tag")

    progress_calls: list[int] = []

    def progress_cb(p: int) -> None:
        progress_calls.append(p)

    success = upgrader.upgrade_plugin(plan, progress_callback=progress_cb)

    assert success is True
    mock_upgrade.assert_called_once()
    mock_write.assert_called_once_with(
        name="plugin1",
        new_tag="v2.0.0",
        new_commit="finalcommit",
    )

    # Progress flow sanity check
    assert progress_calls[0] == 10
    assert progress_calls[-1] == 100


@patch.object(PluginUpgrader, "_upgrade_to_commit")
@patch.object(PluginUpgrader, "_get_local_head_commit", return_value="finalcommit")
@patch.object(PluginUpgrader, "_write_lockfile_update")
def test_upgrade_plugin_commit_success(
    mock_write: MagicMock,
    mock_head: MagicMock,
    mock_upgrade: MagicMock,
) -> None:
    upgrader = PluginUpgrader()
    plan = make_plan(update_type="commit")

    success = upgrader.upgrade_plugin(plan)

    assert success is True
    mock_upgrade.assert_called_once()
    mock_write.assert_called_once()


def test_upgrade_plugin_no_update_available() -> None:
    upgrader = PluginUpgrader()
    plan = make_plan(update_available=False)

    success = upgrader.upgrade_plugin(plan)

    assert success is False


@patch.object(PluginUpgrader, "_upgrade_to_tag", side_effect=Exception("git failed"))
def test_upgrade_plugin_failure_reports_zero_progress(
    mock_upgrade: MagicMock,
) -> None:
    upgrader = PluginUpgrader()
    plan = make_plan(update_type="tag")

    progress_calls: list[int] = []

    def progress_cb(p: int) -> None:
        progress_calls.append(p)

    success = upgrader.upgrade_plugin(plan, progress_callback=progress_cb)

    assert success is False
    assert progress_calls[-1] == 0


@patch("subprocess.run")
def test_upgrade_to_tag_executes_git_commands(mock_run: MagicMock) -> None:
    upgrader = PluginUpgrader()

    calls: list[int] = []

    def progress(p: int) -> None:
        calls.append(p)

    upgrader._upgrade_to_tag(
        plugin_path="/fake/plugins/plugin1",
        tag="v2.0.0",
        progress=progress,
    )

    assert mock_run.call_count == 2

    fetch_cmd = mock_run.call_args_list[0][0][0]
    checkout_cmd = mock_run.call_args_list[1][0][0]

    assert fetch_cmd[:2] == ["git", "fetch"]
    assert "refs/tags/v2.0.0" in fetch_cmd[-1]
    assert checkout_cmd == ["git", "checkout", "--detach", "tags/v2.0.0"]

    assert calls == [40, 70]


@patch("subprocess.run")
def test_upgrade_to_commit_executes_git_commands(mock_run: MagicMock) -> None:
    upgrader = PluginUpgrader()

    calls: list[int] = []

    def progress(p: int) -> None:
        calls.append(p)

    upgrader._upgrade_to_commit(
        plugin_path="/fake/plugins/plugin1",
        commit="abc123",
        progress=progress,
    )

    assert mock_run.call_count == 2

    fetch_cmd = mock_run.call_args_list[0][0][0]
    checkout_cmd = mock_run.call_args_list[1][0][0]

    assert fetch_cmd == ["git", "fetch", "origin", "abc123"]
    assert checkout_cmd == ["git", "checkout", "--detach", "abc123"]

    assert calls == [40, 70]


@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file")
def test_write_lockfile_update(
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

    upgrader._write_lockfile_update(
        name="plugin1",
        new_tag="v2.0.0",
        new_commit="def456",
    )

    mock_write.assert_called_once()
    written = mock_write.call_args[0][0]

    plugin = written["plugins"][0]["git"]
    assert plugin["tag"] == "v2.0.0"
    assert plugin["commit_hash"] == "def456"
    assert "last_pull" in plugin

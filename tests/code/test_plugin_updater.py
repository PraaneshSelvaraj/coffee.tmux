import subprocess
from typing import Any
from unittest.mock import MagicMock, patch

from core import PluginUpdater


def make_updater() -> PluginUpdater:
    return PluginUpdater("/fake/plugins")


def test_semantic_sort_tags_basic() -> None:
    updater = make_updater()
    tags = ["v1.0.0", "v2.0.0", "v1.5.0"]
    result = updater._semantic_sort_tags(tags)
    assert result == ["v2.0.0", "v1.5.0", "v1.0.0"]


def test_semantic_sort_skips_prerelease_and_invalid() -> None:
    updater = make_updater()
    tags = ["v1.0.0", "v2.0.0-beta", "nightly", "foo"]
    result = updater._semantic_sort_tags(tags)
    assert result == ["v1.0.0"]


def test_get_remote_tags_success() -> None:
    updater = make_updater()

    git_output = """abc\trefs/tags/v1.0.0
def\trefs/tags/v1.1.0
ghi\trefs/tags/v2.0.0^{}
"""

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=git_output)
        tags = updater._get_remote_tags("https://github.com/owner/repo")

    assert tags == ["v2.0.0", "v1.1.0", "v1.0.0"]


def test_get_remote_tags_failure() -> None:
    updater = make_updater()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        tags = updater._get_remote_tags("https://github.com/owner/repo")

    assert tags == []


def test_get_latest_commit_success() -> None:
    updater = make_updater()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc123\tHEAD\n")
        commit = updater._get_latest_commit("https://github.com/owner/repo")

    assert commit == "abc123"


def test_get_latest_commit_failure() -> None:
    updater = make_updater()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        commit = updater._get_latest_commit("https://github.com/owner/repo")

    assert commit is None


def test_get_tag_commit_hash_success() -> None:
    updater = make_updater()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="def456\trefs/tags/v1.0\n"
        )
        commit = updater._get_tag_commit_hash("https://github.com/owner/repo", "v1.0")

    assert commit == "def456"


@patch("os.path.exists", return_value=False)
def test_plan_plugin_update_not_installed(mock_exists: MagicMock) -> None:
    updater = make_updater()

    plugin = {
        "name": "plugin1",
        "git": {"repo": "owner/repo"},
    }

    plan = updater._plan_plugin_update(plugin)

    assert plan["_internal"]["update_available"] is False
    assert plan["_internal"]["reason"] == "not_installed_or_missing_repo"


@patch("os.path.exists", return_value=True)
def test_plan_plugin_update_tag_up_to_date(mock_exists: MagicMock) -> None:
    updater = make_updater()

    plugin = {
        "name": "plugin1",
        "git": {
            "repo": "owner/repo",
            "tag": "v1.0.0",
            "commit_hash": "abc",
        },
    }

    with patch.object(updater, "_get_remote_tags", return_value=["v1.0.0"]):
        plan = updater._plan_plugin_update(plugin)

    assert plan["_internal"]["update_available"] is False
    assert plan["_internal"]["type"] == "tag"


@patch("os.path.exists", return_value=True)
def test_plan_plugin_update_tag_update_available(mock_exists: MagicMock) -> None:
    updater = make_updater()

    plugin = {
        "name": "plugin1",
        "git": {
            "repo": "owner/repo",
            "tag": "v1.0.0",
            "commit_hash": "abc",
        },
    }

    with patch.object(updater, "_get_remote_tags", return_value=["v2.0.0", "v1.0.0"]):
        with patch.object(updater, "_get_tag_commit_hash", return_value="def"):
            plan = updater._plan_plugin_update(plugin)

    internal = plan["_internal"]
    assert internal["update_available"] is True
    assert internal["new_tag"] == "v2.0.0"
    assert internal["type"] == "tag"


@patch("os.path.exists", return_value=True)
def test_plan_plugin_update_commit_update(mock_exists: MagicMock) -> None:
    updater = make_updater()

    plugin = {
        "name": "plugin1",
        "git": {
            "repo": "owner/repo",
            "commit_hash": "abc",
        },
    }

    with patch.object(updater, "_get_latest_commit", return_value="def"):
        plan = updater._plan_plugin_update(plugin)

    internal = plan["_internal"]
    assert internal["update_available"] is True
    assert internal["new_commit"] == "def"
    assert internal["type"] == "commit"


def test_build_update_view_up_to_date() -> None:
    updater = make_updater()

    plan = {
        "name": "plugin1",
        "_internal": {
            "update_available": False,
        },
    }

    view = updater._build_update_view(plan)

    assert view["changelog"] == ["Up-to-date"]
    assert view["marked"] is False
    assert view["progress"] == 0


def test_build_update_view_with_update() -> None:
    updater = make_updater()

    plan = {
        "name": "plugin1",
        "_internal": {
            "update_available": True,
            "old_tag": "v1.0.0",
            "new_tag": "v2.0.0",
            "plugin_path": "/fake/plugins/plugin1",
        },
    }

    with patch.object(updater, "_get_repo_size", return_value="5.2M"):
        with patch.object(updater, "_get_time_since_tag", return_value="1 week ago"):
            view = updater._build_update_view(plan)

    assert view["current_version"] == "v1.0.0"
    assert view["new_version"] == "v2.0.0"
    assert "Update available" in view["changelog"][0]


@patch("core.lock_file_manager.read_lock_file")
@patch("os.path.exists", return_value=True)
def test_check_for_updates_integration(
    mock_exists: MagicMock, mock_read: MagicMock
) -> None:
    mock_read.return_value = {
        "plugins": [
            {
                "name": "plugin1",
                "git": {
                    "repo": "owner/repo",
                    "tag": "v1.0.0",
                    "commit_hash": "abc",
                },
            }
        ]
    }

    updater = make_updater()

    with patch.object(updater, "_get_remote_tags", return_value=["v2.0.0"]):
        with patch.object(updater, "_get_tag_commit_hash", return_value="def"):
            with patch.object(updater, "_get_repo_size", return_value="5.2M"):
                with patch.object(
                    updater, "_get_time_since_tag", return_value="1 week ago"
                ):
                    updates = updater.check_for_updates()

    assert len(updates) == 1
    assert updates[0]["_internal"]["update_available"] is True

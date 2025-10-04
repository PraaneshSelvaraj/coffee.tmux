import subprocess
from typing import Any, Dict, List
from unittest.mock import patch, MagicMock
import core.pluginSourcer as ps


@patch("core.lock_file_manager.read_lock_file")
@patch.object(ps.PluginSourcer, "_source_plugin")
def test_source_enabled_plugins_empty(
    mock_source: MagicMock, mock_read: MagicMock
) -> None:
    mock_read.return_value = {"plugins": []}
    sourcer: ps.PluginSourcer = ps.PluginSourcer()
    sourcer.source_enabled_plugins()
    mock_source.assert_not_called()


@patch("core.lock_file_manager.read_lock_file")
@patch.object(ps.PluginSourcer, "_source_plugin")
def test_source_enabled_plugins_only_enabled(
    mock_source: MagicMock, mock_read: MagicMock
) -> None:
    mock_read.return_value = {
        "plugins": [
            {"name": "plugin1", "enabled": True, "sources": ["/path/script1.tmux"]},
            {"name": "plugin2", "enabled": False, "sources": ["/path/script2.tmux"]},
            {"name": "plugin3", "enabled": True, "sources": ["/path/script3.tmux"]},
        ]
    }
    sourcer: ps.PluginSourcer = ps.PluginSourcer()
    sourcer.source_enabled_plugins()

    assert mock_source.call_count == 2
    sourced_plugins: List[str] = [
        call_args[0][0]["name"] for call_args in mock_source.call_args_list
    ]
    assert "plugin1" in sourced_plugins
    assert "plugin3" in sourced_plugins
    assert "plugin2" not in sourced_plugins


@patch.object(ps.PluginSourcer, "_run_plugin_script")
def test_source_plugin_with_scripts(mock_run: MagicMock, capsys: Any) -> None:
    plugin: Dict[str, Any] = {
        "name": "test-plugin",
        "enabled": True,
        "sources": ["/path/to/script1.tmux", "/path/to/script2.tmux"],
    }
    sourcer: ps.PluginSourcer = ps.PluginSourcer()
    sourcer._source_plugin(plugin)

    assert mock_run.call_count == 2
    mock_run.assert_any_call("/path/to/script1.tmux")
    mock_run.assert_any_call("/path/to/script2.tmux")

    captured = capsys.readouterr()
    assert "Executed test-plugin script" in captured.out


def test_source_plugin_no_scripts(capsys: Any) -> None:
    plugin: Dict[str, Any] = {"name": "test-plugin", "enabled": True, "sources": []}
    sourcer: ps.PluginSourcer = ps.PluginSourcer()
    sourcer._source_plugin(plugin)

    captured = capsys.readouterr()
    assert captured.out == ""


def test_source_plugin_disabled_plugin() -> None:
    plugin: Dict[str, Any] = {
        "name": "test-plugin",
        "enabled": False,
        "sources": ["/path/to/script.tmux"],
    }
    with patch.object(ps.PluginSourcer, "_run_plugin_script") as mock_run:
        sourcer: ps.PluginSourcer = ps.PluginSourcer()
        sourcer._source_plugin(plugin)
        mock_run.assert_not_called()


@patch("subprocess.run")
def test_run_plugin_script_success(mock_run: MagicMock, capsys: Any) -> None:
    mock_run.return_value = MagicMock()
    sourcer: ps.PluginSourcer = ps.PluginSourcer()
    sourcer._run_plugin_script("/path/to/script.tmux")

    mock_run.assert_called_once_with(
        ["tmux", "run-shell", "/path/to/script.tmux"], check=True
    )
    captured = capsys.readouterr()
    assert "Ran script: /path/to/script.tmux" in captured.out


@patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd"))
def test_run_plugin_script_failure(mock_run: MagicMock, capsys: Any) -> None:
    sourcer: ps.PluginSourcer = ps.PluginSourcer()
    sourcer._run_plugin_script("/path/to/script.tmux")

    captured = capsys.readouterr()
    assert "Error running script /path/to/script.tmux" in captured.out


@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file")
def test_set_plugin_enabled_true(
    mock_read: MagicMock, mock_write: MagicMock, capsys: Any
) -> None:
    mock_read.return_value = {
        "plugins": [
            {"name": "plugin1", "enabled": False},
            {"name": "plugin2", "enabled": True},
        ]
    }

    sourcer: ps.PluginSourcer = ps.PluginSourcer()
    sourcer._set_plugin_enabled("plugin1", True)

    mock_write.assert_called_once()
    written_data: Dict[str, Any] = mock_write.call_args[0][0]
    plugin1 = next(p for p in written_data["plugins"] if p["name"] == "plugin1")
    assert plugin1["enabled"] is True

    captured = capsys.readouterr()
    assert "Plugin 'plugin1' is now enabled" in captured.out


@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file")
def test_set_plugin_enabled_false(
    mock_read: MagicMock, mock_write: MagicMock, capsys: Any
) -> None:
    mock_read.return_value = {
        "plugins": [
            {"name": "plugin1", "enabled": True},
            {"name": "plugin2", "enabled": True},
        ]
    }

    sourcer: ps.PluginSourcer = ps.PluginSourcer()
    sourcer._set_plugin_enabled("plugin1", False)

    mock_write.assert_called_once()
    written_data: Dict[str, Any] = mock_write.call_args[0][0]
    plugin1 = next(p for p in written_data["plugins"] if p["name"] == "plugin1")
    assert plugin1["enabled"] is False

    captured = capsys.readouterr()
    assert "Plugin 'plugin1' is now disabled" in captured.out


@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file")
def test_set_plugin_enabled_not_found(
    mock_read: MagicMock, mock_write: MagicMock, capsys: Any
) -> None:
    mock_read.return_value = {"plugins": [{"name": "plugin1", "enabled": True}]}

    sourcer: ps.PluginSourcer = ps.PluginSourcer()
    sourcer._set_plugin_enabled("nonexistent", True)

    mock_write.assert_not_called()
    captured = capsys.readouterr()
    assert "Plugin 'nonexistent' not found in the lock file" in captured.out


@patch.object(ps.PluginSourcer, "source_enabled_plugins")
@patch.object(ps.PluginSourcer, "_set_plugin_enabled")
def test_activate_plugin(mock_set: MagicMock, mock_source: MagicMock) -> None:
    sourcer: ps.PluginSourcer = ps.PluginSourcer()
    sourcer.activate_plugin("test-plugin")

    mock_set.assert_called_once_with("test-plugin", True)
    mock_source.assert_called_once()


@patch.object(ps.PluginSourcer, "_set_plugin_enabled")
def test_deactivate_plugin(mock_set: MagicMock) -> None:
    sourcer: ps.PluginSourcer = ps.PluginSourcer()
    sourcer.deactivate_plugin("test-plugin")

    mock_set.assert_called_once_with("test-plugin", False)


@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file")
@patch.object(ps.PluginSourcer, "source_enabled_plugins")
def test_activate_plugin_integration(
    mock_source: MagicMock, mock_read: MagicMock, mock_write: MagicMock, capsys: Any
) -> None:
    mock_read.return_value = {
        "plugins": [
            {"name": "my-plugin", "enabled": False, "sources": ["/path/script.tmux"]}
        ]
    }

    sourcer: ps.PluginSourcer = ps.PluginSourcer()
    sourcer.activate_plugin("my-plugin")

    # Check that plugin was enabled
    written_data: Dict[str, Any] = mock_write.call_args[0][0]
    assert written_data["plugins"][0]["enabled"] is True

    # Check that source_enabled_plugins was called
    mock_source.assert_called_once()

    captured = capsys.readouterr()
    assert "Plugin 'my-plugin' is now enabled" in captured.out


@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file")
def test_deactivate_plugin_integration(
    mock_read: MagicMock, mock_write: MagicMock, capsys: Any
) -> None:
    mock_read.return_value = {
        "plugins": [
            {"name": "my-plugin", "enabled": True, "sources": ["/path/script.tmux"]}
        ]
    }

    sourcer: ps.PluginSourcer = ps.PluginSourcer()
    sourcer.deactivate_plugin("my-plugin")

    # Check that plugin was disabled
    written_data: Dict[str, Any] = mock_write.call_args[0][0]
    assert written_data["plugins"][0]["enabled"] is False

    captured = capsys.readouterr()
    assert "Plugin 'my-plugin' is now disabled" in captured.out


@patch("core.lock_file_manager.read_lock_file")
@patch.object(ps.PluginSourcer, "_run_plugin_script")
def test_source_enabled_plugins_multiple_scripts_per_plugin(
    mock_run: MagicMock, mock_read: MagicMock, capsys: Any
) -> None:
    mock_read.return_value = {
        "plugins": [
            {
                "name": "multi-script-plugin",
                "enabled": True,
                "sources": [
                    "/path/to/script1.tmux",
                    "/path/to/script2.tmux",
                    "/path/to/script3.tmux",
                ],
            }
        ]
    }

    sourcer: ps.PluginSourcer = ps.PluginSourcer()
    sourcer.source_enabled_plugins()

    assert mock_run.call_count == 3
    captured = capsys.readouterr()
    assert "Executed multi-script-plugin script" in captured.out

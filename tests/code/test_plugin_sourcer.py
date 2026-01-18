from unittest.mock import MagicMock, patch

from core import PluginSourcer


@patch("core.lock_file_manager.read_lock_file")
@patch.object(PluginSourcer, "_source_plugin")
def test_source_enabled_plugins_empty(
    mock_source: MagicMock, mock_read: MagicMock
) -> None:
    mock_read.return_value = {"plugins": []}

    sourcer = PluginSourcer()
    sourcer.source_enabled_plugins()

    mock_source.assert_not_called()


@patch("core.lock_file_manager.read_lock_file")
@patch.object(PluginSourcer, "_source_plugin")
def test_source_enabled_plugins_only_enabled(
    mock_source: MagicMock, mock_read: MagicMock
) -> None:
    mock_read.return_value = {
        "plugins": [
            {"name": "plugin1", "enabled": True},
            {"name": "plugin2", "enabled": False},
            {"name": "plugin3", "enabled": True},
        ]
    }

    sourcer = PluginSourcer()
    sourcer.source_enabled_plugins()

    assert mock_source.call_count == 2
    names = [call.args[0]["name"] for call in mock_source.call_args_list]
    assert "plugin1" in names
    assert "plugin3" in names
    assert "plugin2" not in names


@patch("subprocess.run")
@patch("os.path.exists", return_value=True)
def test_source_plugin_sources_all_scripts(
    mock_exists: MagicMock, mock_run: MagicMock
) -> None:
    plugin = {
        "name": "plugin1",
        "enabled": True,
        "install_path": "/plugins/plugin1",
        "source": ["a.tmux", "b.tmux"],
    }

    sourcer = PluginSourcer()
    sourcer._source_plugin(plugin)

    assert mock_run.call_count == 2
    mock_run.assert_any_call(
        ["tmux", "run-shell", "/plugins/plugin1/a.tmux"], check=False
    )
    mock_run.assert_any_call(
        ["tmux", "run-shell", "/plugins/plugin1/b.tmux"], check=False
    )


@patch("subprocess.run")
def test_source_plugin_skips_when_no_install_path(mock_run: MagicMock) -> None:
    plugin = {"enabled": True, "source": ["a.tmux"]}

    sourcer = PluginSourcer()
    sourcer._source_plugin(plugin)

    mock_run.assert_not_called()


@patch("subprocess.run")
def test_source_plugin_skips_when_no_sources(mock_run: MagicMock) -> None:
    plugin = {"enabled": True, "install_path": "/plugins/x"}

    sourcer = PluginSourcer()
    sourcer._source_plugin(plugin)

    mock_run.assert_not_called()


@patch("subprocess.run")
@patch("os.path.exists", return_value=False)
def test_run_tmux_source_skips_missing_file(
    mock_exists: MagicMock, mock_run: MagicMock
) -> None:
    sourcer = PluginSourcer()
    sourcer._run_tmux_source("/missing/script.tmux")

    mock_run.assert_not_called()


@patch("subprocess.run")
@patch("os.path.exists", return_value=True)
def test_run_tmux_source_executes_tmux(
    mock_exists: MagicMock, mock_run: MagicMock
) -> None:
    sourcer = PluginSourcer()
    sourcer._run_tmux_source("/plugins/p/init.tmux")

    mock_run.assert_called_once_with(
        ["tmux", "run-shell", "/plugins/p/init.tmux"],
        check=False,
    )


@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file")
def test_activate_plugin_sets_enabled_true(
    mock_read: MagicMock, mock_write: MagicMock
) -> None:
    lock_data = {
        "plugins": [
            {"name": "plugin1", "enabled": False},
        ]
    }
    mock_read.return_value = lock_data

    sourcer = PluginSourcer()
    with patch.object(sourcer, "source_enabled_plugins") as mock_source:
        sourcer.activate_plugin("plugin1")

    assert lock_data["plugins"][0]["enabled"] is True
    mock_write.assert_called_once_with(lock_data)
    mock_source.assert_called_once()


@patch("core.lock_file_manager.write_lock_file")
@patch("core.lock_file_manager.read_lock_file")
def test_deactivate_plugin_sets_enabled_false(
    mock_read: MagicMock, mock_write: MagicMock
) -> None:
    lock_data = {
        "plugins": [
            {"name": "plugin1", "enabled": True},
        ]
    }
    mock_read.return_value = lock_data

    sourcer = PluginSourcer()
    sourcer.deactivate_plugin("plugin1")

    assert lock_data["plugins"][0]["enabled"] is False
    mock_write.assert_called_once_with(lock_data)


@patch("core.lock_file_manager.read_lock_file")
@patch("core.lock_file_manager.write_lock_file")
def test_set_plugin_enabled_noop_when_not_found(
    mock_write: MagicMock, mock_read: MagicMock
) -> None:
    mock_read.return_value = {"plugins": []}

    sourcer = PluginSourcer()
    sourcer.activate_plugin("missing")

    mock_write.assert_not_called()

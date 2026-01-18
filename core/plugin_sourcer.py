import os
import subprocess
from typing import Any

from core import lock_file_manager as lfm


class PluginSourcer:
    def source_enabled_plugins(self) -> None:
        lock_data = lfm.read_lock_file()

        for plugin in lock_data.get("plugins", []):
            if plugin.get("enabled", False):
                self._source_plugin(plugin)

    def activate_plugin(self, plugin_name: str) -> None:
        self._set_plugin_enabled(plugin_name, True)
        self.source_enabled_plugins()

    def deactivate_plugin(self, plugin_name: str) -> None:
        # Disabled plugins will not be sourced on next run
        self._set_plugin_enabled(plugin_name, False)

    def _source_plugin(self, plugin: dict[str, Any]) -> None:
        install_path: str | None = plugin.get("install_path")
        scripts: list[str] = plugin.get("source", [])

        if not install_path or not scripts:
            return

        for script in scripts:
            script_path = os.path.join(install_path, script)
            self._run_tmux_source(script_path)

    def _run_tmux_source(self, script_path: str) -> None:
        if not os.path.exists(script_path):
            return

        subprocess.run(
            ["tmux", "run-shell", script_path],
            check=False,
        )

    def _set_plugin_enabled(self, plugin_name: str, state: bool) -> None:
        lock_data = lfm.read_lock_file()

        for plugin in lock_data.get("plugins", []):
            if plugin.get("name") == plugin_name:
                plugin["enabled"] = state
                break
        else:
            return

        lfm.write_lock_file(lock_data)

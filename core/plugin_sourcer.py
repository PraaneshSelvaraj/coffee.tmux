import os
import subprocess
from typing import Any

from core import lock_file_manager as lfm


class PluginSourcer:
    def source_enabled_plugins(self) -> None:
        lock_data = lfm.read_lock_file()
        enabled_plugins: list[dict[str, Any]] = [
            plugin
            for plugin in lock_data.get("plugins", [])
            if plugin.get("enabled", False)
        ]
        for plugin in enabled_plugins:
            self._source_plugin(plugin)

    def _source_plugin(self, plugin: dict[str, Any]) -> None:
        plugin_name: str | None = plugin.get("name")
        scripts: list[str] = plugin.get("sources", [])
        plugin_dir: str | None = os.path.dirname(scripts[0]) if scripts else None
        if not scripts or not plugin_dir:
            return
        for script in scripts:
            if plugin.get("enabled", True):
                self._run_plugin_script(script)
                print(f"Executed {plugin_name} script from {script}")

    def _run_plugin_script(self, script_path: str) -> None:
        try:
            subprocess.run(["tmux", "run-shell", f"{script_path}"], check=True)
            print(f"Ran script: {script_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error running script {script_path}: {e}")

    def activate_plugin(self, plugin_name: str) -> None:
        self._set_plugin_enabled(plugin_name, True)
        self.source_enabled_plugins()

    def deactivate_plugin(self, plugin_name: str) -> None:
        # Will not be activated on the next run
        self._set_plugin_enabled(plugin_name, False)

    def _set_plugin_enabled(self, plugin_name: str, state: bool) -> None:
        lock_data = lfm.read_lock_file()
        plugins: list[dict[str, Any]] = lock_data.get("plugins", [])
        for plugin in plugins:
            if plugin.get("name") == plugin_name:
                plugin["enabled"] = state
                status = "enabled" if state else "disabled"
                print(f"Plugin '{plugin_name}' is now {status}.")
                break
        else:
            print(f"Plugin '{plugin_name}' not found in the lock file.")
            return
        lfm.write_lock_file(lock_data)

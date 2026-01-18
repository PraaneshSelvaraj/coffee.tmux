import os
import shutil
import subprocess
from datetime import datetime
from typing import Any, Callable

from core import lock_file_manager as lfm
from core.lock_file_manager import LockData


class PluginRemover:
    def __init__(self, plugin_base_dir: str) -> None:
        self.plugin_base_dir = plugin_base_dir

    def get_installed_plugins(
        self,
    ) -> list[dict[str, str | bool | dict[str, Any]]]:
        """
        Return installed plugins with UI-friendly metadata.
        """
        lock_data = lfm.read_lock_file()
        plugins = lock_data.get("plugins", [])

        installed_plugins: list[dict[str, str | bool | dict[str, Any]]] = []

        for plugin in plugins:
            plugin_name = plugin.get("name", "")
            plugin_path = os.path.join(self.plugin_base_dir, plugin_name)

            size = self._get_directory_size(plugin_path)
            version = self._get_plugin_version(plugin)
            installed_time = self._format_installed_time(
                plugin.get("git", {}).get("last_pull")
            )

            installed_plugins.append(
                {
                    "name": plugin_name,
                    "version": version,
                    "size": size,
                    "installed": installed_time,
                    "enabled": plugin.get("enabled", False),
                }
            )

        return installed_plugins

    def remove_plugin(
        self,
        plugin_name: str,
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> bool:
        """
        Remove a plugin directory and update the lock file.
        """

        def progress(p: int) -> None:
            if progress_callback:
                progress_callback(plugin_name, p)

        try:
            progress(10)

            lock_data = lfm.read_lock_file()
            plugins = lock_data.get("plugins", [])

            if not self._plugin_exists_in_lock(plugin_name, plugins):
                progress(0)
                return False

            progress(40)
            self._remove_directory(plugin_name)

            progress(70)
            self._update_lock_file(lock_data, plugin_name)

            progress(100)
            return True

        except Exception:
            progress(0)
            return False

    def _remove_directory(self, plugin_name: str) -> None:
        plugin_path = os.path.join(self.plugin_base_dir, plugin_name)

        if os.path.exists(plugin_path):
            shutil.rmtree(plugin_path)

    def _update_lock_file(self, lock_data: LockData, plugin_name: str) -> None:
        lock_data["plugins"] = [
            p for p in lock_data.get("plugins", []) if p.get("name") != plugin_name
        ]
        lfm.write_lock_file(lock_data)

    def _plugin_exists_in_lock(
        self,
        plugin_name: str,
        plugins: list[dict[str, Any]],
    ) -> bool:
        return any(p.get("name") == plugin_name for p in plugins)

    def _get_directory_size(self, plugin_path: str) -> str:
        if not os.path.exists(plugin_path):
            return "Unknown"

        try:
            result = subprocess.run(
                ["du", "-sh", plugin_path],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip().split()[0]
        except Exception:
            pass

        return "Unknown"

    def _get_plugin_version(self, plugin: dict[str, Any]) -> str:
        git_info = plugin.get("git", {})
        if git_info.get("tag"):
            return git_info["tag"]
        if git_info.get("commit_hash"):
            return git_info["commit_hash"][:7]
        return "N/A"

    def _format_installed_time(self, last_pull: str | None) -> str:
        if not last_pull:
            return "Unknown"

        try:
            dt = datetime.fromisoformat(last_pull.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return "Unknown"

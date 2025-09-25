import os
import shutil
import subprocess
from typing import Any, Callable, Dict, List, Optional, Union

from core import lock_file_manager as lfm


class PluginRemover:
    def __init__(self, plugin_base_dir: str) -> None:
        self.plugin_base_dir = plugin_base_dir

    def get_installed_plugins(
        self,
    ) -> List[Dict[str, Union[str, bool, Dict[str, Any]]]]:
        lock_data = lfm.read_lock_file()
        plugins = lock_data.get("plugins", [])
        installed_plugins: List[Dict[str, Union[str, bool, Dict[str, Any]]]] = []

        for plugin in plugins:
            plugin_name = plugin.get("name", "")
            plugin_path = os.path.join(self.plugin_base_dir, plugin_name)
            size: str = "Unknown"

            if os.path.exists(plugin_path):
                try:
                    result = subprocess.run(
                        ["du", "-sh", plugin_path],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if result.returncode == 0:
                        size = result.stdout.strip().split()[0]
                except Exception:
                    pass

            git_info = plugin.get("git", {})
            version: str = git_info.get("tag") or (
                git_info.get("commit_hash", "")[:7]
                if git_info.get("commit_hash")
                else "N/A"
            )
            installed_time: str = git_info.get("last_pull", "Unknown")

            if installed_time != "Unknown":
                try:
                    from datetime import datetime

                    dt = datetime.fromisoformat(installed_time.replace("Z", "+00:00"))
                    installed_time = dt.strftime("%Y-%m-%d")
                except Exception:
                    installed_time = "Unknown"

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
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> bool:
        def send_progress(progress: int) -> None:
            if progress_callback:
                progress_callback(plugin_name, progress)

        try:
            send_progress(10)
            lock_data = lfm.read_lock_file()
            plugins = lock_data.get("plugins", [])
            plugin_entry = next(
                (p for p in plugins if p.get("name") == plugin_name), None
            )

            if not plugin_entry:
                send_progress(0)
                return False

            send_progress(50)
            plugin_path = os.path.join(self.plugin_base_dir, plugin_name)

            if os.path.exists(plugin_path):
                try:
                    shutil.rmtree(plugin_path)
                except Exception:
                    send_progress(0)
                    return False

            send_progress(80)
            lock_data["plugins"] = [p for p in plugins if p.get("name") != plugin_name]
            lfm.write_lock_file(lock_data)

            send_progress(100)
            return True

        except Exception:
            send_progress(0)
            return False

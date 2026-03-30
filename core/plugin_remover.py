import asyncio
import os
import shutil
import subprocess
from datetime import datetime
from typing import Any, Callable

from core import lock_file_manager as lfm


class PluginRemover:
    def __init__(self, plugin_base_dir: str) -> None:
        self.plugin_base_dir = plugin_base_dir

    async def get_installed_plugins(self) -> list[dict[str, Any]]:
        lock_data = lfm.read_lock_file()
        plugins = lock_data.get("plugins", [])

        tasks = []
        for plugin in plugins:
            plugin_name = plugin.get("name", "")
            plugin_path = os.path.join(self.plugin_base_dir, plugin_name)
            tasks.append(self._get_directory_size(plugin_path))

        sizes = await asyncio.gather(*tasks)

        installed_plugins = []
        for plugin, size in zip(plugins, sizes):
            installed_plugins.append(
                {
                    "name": plugin["name"],
                    "version": self._get_plugin_version(plugin),
                    "size": size,
                    "installed": self._format_installed_time(
                        plugin.get("git", {}).get("last_pull")
                    ),
                    "enabled": plugin.get("enabled", False),
                }
            )

        return installed_plugins

    async def remove_plugin(
        self,
        plugin_name: str,
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> dict[str, Any] | None:
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
                return None

            progress(40)
            await self._remove_directory(plugin_name)

            progress(100)
            return {"plugin_name": plugin_name}

        except (OSError, ValueError):
            progress(0)
            raise

    async def _remove_directory(self, plugin_name: str) -> None:
        plugin_path = os.path.join(self.plugin_base_dir, plugin_name)

        if os.path.exists(plugin_path):
            try:
                await asyncio.to_thread(shutil.rmtree, plugin_path)
            except OSError as e:
                raise OSError(
                    f"Failed to remove plugin directory: {plugin_path}"
                ) from e

    def update_lock_file(self, removed: list[dict[str, str]]) -> bool:
        if not removed:
            return False

        lock_data = lfm.read_lock_file()
        removed_names = {r["plugin_name"] for r in removed}

        original_len = len(lock_data.get("plugins", []))

        lock_data["plugins"] = [
            p
            for p in lock_data.get("plugins", [])
            if p.get("name") not in removed_names
        ]

        if len(lock_data["plugins"]) != original_len:
            lfm.write_lock_file(lock_data)
            return True

        return False

    def _plugin_exists_in_lock(
        self,
        plugin_name: str,
        plugins: list[dict[str, Any]],
    ) -> bool:
        return any(p.get("name") == plugin_name for p in plugins)

    async def _get_directory_size(self, plugin_path: str) -> str:
        if not os.path.exists(plugin_path):
            return "Unknown"

        try:
            process = await asyncio.create_subprocess_exec(
                "du",
                "-sh",
                plugin_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )

            stdout, _ = await process.communicate()

            if process.returncode != 0:
                return "Unknown"

            return stdout.decode().strip().split()[0]

        except (OSError, subprocess.SubprocessError):
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
        except ValueError:
            return "Unknown"

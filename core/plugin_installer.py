import asyncio
import os
import shutil
from datetime import datetime, timezone
from typing import Any, Callable

from core import lock_file_manager as lfm


class PluginInstaller:
    def __init__(
        self,
        plugins_config: list[dict[str, Any]],
        plugins_dir: str,
        tmux_conf_path: str,
    ) -> None:
        self.plugins_config = plugins_config
        self.plugins_dir = plugins_dir
        self.tmux_conf_path = tmux_conf_path

    async def install_git_plugin(
        self,
        plugin: dict[str, Any],
        progress_callback: Callable[[int], None] | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        plugin_path = os.path.abspath(os.path.join(self.plugins_dir, plugin["name"]))
        plugins_dir = os.path.abspath(self.plugins_dir)

        # Already exists
        if os.path.exists(plugin_path):
            if not force:
                lock_data = lfm.read_lock_file()
                existing = next(
                    (p for p in lock_data["plugins"] if p["name"] == plugin["name"]),
                    None,
                )
                used_tag = existing.get("git", {}).get("tag") if existing else None

                if progress_callback:
                    progress_callback(100)

                return {
                    "plugin": plugin,
                    "used_tag": used_tag,
                    "commit_hash": (
                        existing.get("git", {}).get("commit_hash") if existing else None
                    ),
                }

            if not plugin_path.startswith(plugins_dir + os.sep):
                raise OSError("Refusing to delete outside plugins directory")

            if progress_callback:
                progress_callback(5)

            shutil.rmtree(plugin_path)

        if "url" not in plugin:
            raise ValueError("Plugin config missing 'url'")

        repo_url = f"https://github.com/{plugin['url']}"
        used_tag = plugin.get("tag")

        if progress_callback:
            progress_callback(0)

        process = await asyncio.create_subprocess_exec(
            "git",
            "clone",
            repo_url,
            plugin_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        await process.wait()

        if process.returncode != 0:
            raise RuntimeError("Git clone failed")

        if progress_callback:
            progress_callback(40)

        if used_tag:
            exists = await self._verify_git_tag_exists(plugin_path, used_tag)
            if not exists:
                raise ValueError(f"Tag '{used_tag}' does not exist")

            await self._checkout_tag(plugin_path, used_tag, progress_callback)
        else:
            if progress_callback:
                progress_callback(55)

            latest_tag = await self._get_latest_tag(plugin_path)
            if latest_tag:
                await self._checkout_tag(plugin_path, latest_tag, progress_callback)
                used_tag = latest_tag

        commit_hash = await self._get_commit_hash(plugin)

        if progress_callback:
            progress_callback(100)

        return {
            "plugin": plugin,
            "used_tag": used_tag,
            "commit_hash": commit_hash,
        }

    async def _get_latest_tag(self, plugin_path: str) -> str | None:
        process = await asyncio.create_subprocess_exec(
            "git",
            "tag",
            "--sort=-version:refname",
            cwd=plugin_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

        stdout, _ = await process.communicate()

        if process.returncode != 0:
            return None

        tags = stdout.decode().strip().split("\n")
        return tags[0] if tags and tags[0] else None

    async def _checkout_tag(
        self,
        plugin_path: str,
        tag: str,
        progress_callback: Callable[[int], None] | None = None,
    ) -> None:
        if progress_callback:
            progress_callback(70)

        process = await asyncio.create_subprocess_exec(
            "git",
            "checkout",
            "--detach",
            f"tags/{tag}",
            cwd=plugin_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        await process.wait()

        if process.returncode != 0:
            raise RuntimeError(f"Git checkout failed for tag {tag}")

        if progress_callback:
            progress_callback(85)

    async def _verify_git_tag_exists(self, repo_path: str, tag: str) -> bool:
        process = await asyncio.create_subprocess_exec(
            "git",
            "show-ref",
            "--tags",
            "--verify",
            "--quiet",
            f"refs/tags/{tag}",
            cwd=repo_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        await process.wait()
        return process.returncode == 0

    async def _get_commit_hash(self, plugin: dict[str, Any]) -> str | None:
        plugin_path = os.path.join(self.plugins_dir, plugin["name"])

        process = await asyncio.create_subprocess_exec(
            "git",
            "rev-parse",
            "HEAD",
            cwd=plugin_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

        stdout, _ = await process.communicate()

        if process.returncode != 0:
            return None

        return stdout.decode().strip()

    def update_lock_file(self, results: list[dict[str, Any]]) -> None:
        lock_data = lfm.read_lock_file()

        for result in results:
            plugin = result["plugin"]
            used_tag = result["used_tag"]
            commit_hash = result["commit_hash"]

            plugin_path = os.path.join(self.plugins_dir, plugin["name"])

            if plugin.get("source"):
                sources = [
                    os.path.join(plugin_path, s) for s in plugin.get("source", [])
                ]
            else:
                sources = self._discover_tmux_sources(plugin_path)

            plugin_data = {
                "name": plugin["name"],
                "source": sources,
                "enabled": plugin.get("enabled", True),
                "install_path": plugin_path,
                "skip_auto_update": plugin.get("skip_auto_update", False),
                "git": {
                    "repo": plugin["url"],
                    "tag": used_tag,
                    "commit_hash": commit_hash,
                    "last_pull": self._get_current_timestamp(),
                },
            }

            lock_data["plugins"] = [
                p for p in lock_data["plugins"] if p["name"] != plugin["name"]
            ]

            lock_data["plugins"].append(plugin_data)

        lfm.write_lock_file(lock_data)

    def _discover_tmux_sources(self, plugin_path: str) -> list[str]:
        sources: list[str] = []

        for root, _, files in os.walk(plugin_path):
            for file in files:
                if file.endswith(".tmux"):
                    sources.append(os.path.join(root, file))

        return sorted(sources)

    def _get_current_timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

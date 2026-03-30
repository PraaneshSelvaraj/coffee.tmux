import asyncio
from datetime import datetime, timezone
from typing import Any, Callable

from core import lock_file_manager as lfm


class PluginUpgrader:
    async def upgrade_plugin(
        self,
        update_plan: dict[str, Any],
        progress_callback: Callable[[int], None] | None = None,
    ) -> dict[str, Any] | None:
        name = update_plan["name"]
        internal = update_plan["_internal"]

        if not internal.get("update_available", False):
            return None

        plugin_path = internal["plugin_path"]
        update_type = internal["type"]

        def progress(p: int) -> None:
            if progress_callback:
                progress_callback(p)

        try:
            progress(10)

            if update_type == "tag":
                success = await self._upgrade_to_tag(
                    plugin_path=plugin_path,
                    tag=internal["new_tag"],
                    progress=progress,
                )

                if not success:
                    progress(0)
                    return None
            else:
                success = await self._upgrade_to_commit(
                    plugin_path=plugin_path,
                    commit=internal["new_commit"],
                    progress=progress,
                )

                if not success:
                    progress(0)
                    return None

            progress(90)

            actual_commit = await self._get_local_head_commit(plugin_path)

            if not actual_commit:
                progress(0)
                return None

            progress(100)

            return {
                "plugin_name": name,
                "new_tag": internal["new_tag"],
                "new_commit": actual_commit,
                "last_pull": datetime.now(timezone.utc).isoformat(),
            }

        except (OSError, ValueError):
            progress(0)
            raise

    async def _upgrade_to_tag(
        self,
        plugin_path: str,
        tag: str,
        progress: Callable[[int], None],
    ) -> bool:
        process = await asyncio.create_subprocess_exec(
            "git",
            "fetch",
            "origin",
            f"refs/tags/{tag}:refs/tags/{tag}",
            cwd=plugin_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await process.wait()

        if process.returncode != 0:
            progress(0)
            return False

        progress(40)

        process = await asyncio.create_subprocess_exec(
            "git",
            "checkout",
            "--detach",
            f"tags/{tag}",
            cwd=plugin_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await process.wait()

        if process.returncode != 0:
            progress(0)
            return False

        progress(70)

        return True

    async def _upgrade_to_commit(
        self,
        plugin_path: str,
        commit: str,
        progress: Callable[[int], None],
    ) -> bool:
        process = await asyncio.create_subprocess_exec(
            "git",
            "fetch",
            "origin",
            commit,
            cwd=plugin_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await process.wait()

        if process.returncode != 0:
            progress(0)
            return False

        progress(40)

        process = await asyncio.create_subprocess_exec(
            "git",
            "checkout",
            "--detach",
            commit,
            cwd=plugin_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await process.wait()

        if process.returncode != 0:
            progress(0)
            return False

        progress(70)

        return True

    def update_lock_file(self, results: list[dict[str, Any]]) -> bool:
        if not results:
            return False

        lock_data = lfm.read_lock_file()
        updated = False

        results_map = {r["plugin_name"]: r for r in results}

        for plugin in lock_data.get("plugins", []):
            plugin_name = plugin.get("name")

            if plugin_name in results_map:
                result = results_map[plugin_name]
                git_info = plugin.setdefault("git", {})

                git_info["commit_hash"] = result.get("new_commit")
                git_info["tag"] = result.get("new_tag")
                git_info["last_pull"] = result.get("last_pull")

                updated = True

        if updated:
            lfm.write_lock_file(lock_data)

        return updated

    async def _get_local_head_commit(self, plugin_path: str) -> str | None:
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

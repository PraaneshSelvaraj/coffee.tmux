import subprocess
from datetime import datetime, timezone
from typing import Any, Callable

from core import lock_file_manager as lfm


class PluginUpgrader:
    def upgrade_plugin(
        self,
        update_plan: dict[str, Any],
        progress_callback: Callable[[int], None] | None = None,
    ) -> bool:
        name = update_plan["name"]
        internal = update_plan["_internal"]

        if not internal.get("update_available", False):
            return False

        plugin_path = internal["plugin_path"]
        update_type = internal["type"]

        def progress(p: int) -> None:
            if progress_callback:
                progress_callback(p)

        try:
            progress(10)

            if update_type == "tag":
                self._upgrade_to_tag(
                    plugin_path=plugin_path,
                    tag=internal["new_tag"],
                    progress=progress,
                )
            else:
                self._upgrade_to_commit(
                    plugin_path=plugin_path,
                    commit=internal["new_commit"],
                    progress=progress,
                )

            progress(90)

            actual_commit = self._get_local_head_commit(plugin_path)
            self._write_lockfile_update(
                name=name,
                new_tag=internal.get("new_tag"),
                new_commit=actual_commit,
            )

            progress(100)
            return True

        except (subprocess.CalledProcessError, OSError, ValueError):
            progress(0)
            raise

    def _upgrade_to_tag(
        self,
        plugin_path: str,
        tag: str,
        progress: Callable[[int], None],
    ) -> None:
        subprocess.run(
            [
                "git",
                "fetch",
                "origin",
                f"refs/tags/{tag}:refs/tags/{tag}",
            ],
            cwd=plugin_path,
            check=True,
            capture_output=True,
            text=True,
        )
        progress(40)

        subprocess.run(
            ["git", "checkout", "--detach", f"tags/{tag}"],
            cwd=plugin_path,
            check=True,
            capture_output=True,
            text=True,
        )
        progress(70)

    def _upgrade_to_commit(
        self,
        plugin_path: str,
        commit: str,
        progress: Callable[[int], None],
    ) -> None:
        subprocess.run(
            ["git", "fetch", "origin", commit],
            cwd=plugin_path,
            check=True,
            capture_output=True,
            text=True,
        )
        progress(40)

        subprocess.run(
            ["git", "checkout", "--detach", commit],
            cwd=plugin_path,
            check=True,
            capture_output=True,
            text=True,
        )
        progress(70)

    def _write_lockfile_update(
        self,
        name: str,
        new_tag: str | None,
        new_commit: str | None,
    ) -> None:
        lock_data = lfm.read_lock_file()

        for plugin in lock_data.get("plugins", []):
            if plugin["name"] == name:
                git_info = plugin.setdefault("git", {})
                git_info["commit_hash"] = new_commit
                git_info["tag"] = new_tag
                git_info["last_pull"] = datetime.now(timezone.utc).isoformat()
                break

        lfm.write_lock_file(lock_data)

    def _get_local_head_commit(self, plugin_path: str) -> str:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=plugin_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

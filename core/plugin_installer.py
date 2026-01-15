import os
import shutil
import subprocess
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

    def install_git_plugin(
        self,
        plugin: dict[str, Any],
        progress_callback: Callable[[int], None] | None = None,
        force: bool = False,
    ) -> tuple[bool, str | None]:
        plugin_path = os.path.abspath(os.path.join(self.plugins_dir, plugin["name"]))
        plugins_dir = os.path.abspath(self.plugins_dir)

        # Plugin already exists
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

                return True, used_tag

            if not plugin_path.startswith(plugins_dir + os.sep):
                raise RuntimeError("Refusing to delete outside plugins directory")

            if progress_callback:
                progress_callback(5)  # removing existing plugin

            try:
                shutil.rmtree(plugin_path)
            except OSError as e:
                if progress_callback:
                    progress_callback(0)
                raise RuntimeError(f"Failed to remove existing plugin: {e}")

        if "url" not in plugin:
            raise RuntimeError("Plugin config missing 'url'")

        repo_url = f"https://github.com/{plugin['url']}"
        used_tag = plugin.get("tag")

        try:
            if progress_callback:
                progress_callback(0)  # start

            subprocess.run(
                ["git", "clone", repo_url, plugin_path],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            if progress_callback:
                progress_callback(40)  # clone complete

            if used_tag:
                if not self._verify_git_tag_exists(plugin_path, used_tag):
                    raise RuntimeError(f"Tag '{used_tag}' does not exist")
                self._checkout_tag(plugin_path, used_tag, progress_callback)
            else:
                if progress_callback:
                    progress_callback(55)  # resolving latest tag

                latest_tag = self._get_latest_tag(plugin_path)
                if latest_tag:
                    self._checkout_tag(plugin_path, latest_tag, progress_callback)
                    used_tag = latest_tag

            if progress_callback:
                progress_callback(95)  # writing lock file

            self._update_lock_file(plugin, used_tag)

            if progress_callback:
                progress_callback(100)  # done

        except (subprocess.CalledProcessError, RuntimeError):
            if progress_callback:
                progress_callback(0)
            return False, None

        return True, used_tag or None

    def _get_latest_tag(self, plugin_path: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", "tag", "--sort=-version:refname"],
                cwd=plugin_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=True,
                text=True,
            )
            tags = result.stdout.strip().split("\n")
            return tags[0] if tags and tags[0] else None
        except subprocess.CalledProcessError:
            return None

    def _checkout_tag(
        self,
        plugin_path: str,
        tag: str,
        progress_callback: Callable[[int], None] | None = None,
    ) -> None:
        if progress_callback:
            progress_callback(70)  # checkout start

        subprocess.run(
            ["git", "checkout", "--detach", f"tags/{tag}"],
            cwd=plugin_path,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if progress_callback:
            progress_callback(85)  # checkout complete

    def _verify_git_tag_exists(self, repo_path: str, tag: str) -> bool:
        result = subprocess.run(
            [
                "git",
                "show-ref",
                "--tags",
                "--verify",
                "--quiet",
                f"refs/tags/{tag}",
            ],
            cwd=str(repo_path),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0

    def _get_commit_hash(self, plugin: dict[str, Any]) -> str | None:
        plugin_path = os.path.join(self.plugins_dir, plugin["name"])
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=plugin_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def _update_lock_file(self, plugin: dict[str, Any], used_tag: str | None) -> None:
        plugin_path = os.path.join(self.plugins_dir, plugin["name"])

        sources = [
            os.path.join(plugin_path, source) for source in plugin.get("source", [])
        ]

        plugin_data: dict[str, Any] = {
            "name": plugin["name"],
            "sources": sources,
            "enabled": plugin.get("enabled", True),
            "skip_auto_update": plugin.get("skip_auto_update", False),
            "git": {
                "repo": plugin["url"],
                "tag": used_tag,
                "commit_hash": self._get_commit_hash(plugin),
                "last_pull": self._get_current_timestamp(),
            },
        }

        lock_data = lfm.read_lock_file()

        existing_plugin = next(
            (p for p in lock_data["plugins"] if p["name"] == plugin["name"]), None
        )

        if existing_plugin:
            lock_data["plugins"].remove(existing_plugin)

        lock_data["plugins"].append(plugin_data)
        lfm.write_lock_file(lock_data)

    def _get_current_timestamp(self) -> str:
        return str(datetime.now(timezone.utc))

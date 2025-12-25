import os
import subprocess
import threading
from datetime import datetime, timezone
from typing import Any, Callable

from core import lock_file_manager as lfm


class PluginUpdater:
    def __init__(self, plugins_dir: str) -> None:
        self.plugins_dir = plugins_dir
        self._update_threads: dict[str, threading.Thread] = {}

    def _safe_check_output(
        self, cmd: list[str], cwd: str | None = None, default: Any | None = None
    ) -> str | None:
        try:
            return subprocess.check_output(cmd, cwd=cwd, text=True).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return default

    def _get_local_head_commit(
        self, plugin_path: str, short: bool = False
    ) -> str | None:
        out = self._safe_check_output(["git", "rev-parse", "HEAD"], cwd=plugin_path)
        if out and short:
            return out[:7]

        return out

    def _get_repo_size(self, plugin_path: str) -> str:
        try:
            result = subprocess.run(
                ["du", "-sh", ".git"], cwd=plugin_path, capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout.strip().split()[0]
        except Exception:
            pass

        return "Unknown"

    def _get_time_since_tag(self, plugin_path: str, tag: str | None) -> str:
        if not tag:
            return "Unknown"

        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%cr", f"tags/{tag}"],
                cwd=plugin_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

        return "Unknown"

    def _get_remote_tags(self, repo_url: str) -> list[str]:
        try:
            result = subprocess.run(
                ["git", "ls-remote", "--tags", repo_url],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                return []
            tags: list[str] = []
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) == 2 and "refs/tags/" in parts[1]:
                    tag = parts[1].split("/")[-1]
                    if tag.endswith("^{}"):
                        tag = tag[:-3]
                    tags.append(tag)
            return sorted(set(tags), reverse=True)
        except Exception:
            return []

    def _get_latest_commit(self, repo_url: str, branch: str = "HEAD") -> str | None:
        try:
            result = subprocess.run(
                ["git", "ls-remote", repo_url, branch],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.split()[0]
        except Exception:
            pass
        return None

    def _get_tag_commit_hash(self, repo_url: str, tag: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", "ls-remote", repo_url, f"refs/tags/{tag}"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.split()[0]
        except Exception:
            pass
        return None

    def _write_lockfile_update(
        self,
        name: str,
        new_tag: str | None = None,
        new_commit: str | None = None,
    ) -> bool:
        try:
            lock_data = lfm.read_lock_file()
            for plugin in lock_data.get("plugins", []):
                if plugin["name"] == name:
                    git_info = plugin.setdefault("git", {})
                    if new_commit:
                        git_info["commit_hash"] = new_commit
                    if new_tag is not None:
                        git_info["tag"] = new_tag
                    git_info["last_pull"] = datetime.now(timezone.utc).isoformat()
                    break
            lfm.write_lock_file(lock_data)
            return True
        except Exception:
            return False

    def check_for_updates(self) -> list[dict[str, Any]]:
        updates: list[dict[str, Any]] = []
        lock_data = lfm.read_lock_file()
        for plugin in lock_data.get("plugins", []):
            name = plugin["name"]
            plugin_path = os.path.join(self.plugins_dir, name)
            git_info = plugin.get("git", {})
            repo = git_info.get("repo")
            repo_url = f"https://github.com/{repo}" if repo else None

            if not os.path.exists(plugin_path) or not repo_url:
                updates.append(
                    {
                        "name": name,
                        "current_version": "Not installed",
                        "new_version": "Not installed",
                        "size": "N/A",
                        "released": "N/A",
                        "changelog": ["Plugin not installed or missing URL"],
                        "marked": False,
                        "progress": 0,
                        "_internal": {"update_available": False},
                    }
                )
                continue

            current_tag = git_info.get("tag")
            current_commit = git_info.get("commit_hash")
            update_available = False
            new_tag = None
            new_commit = None
            update_type = "commit"

            if current_tag:
                remote_tags = self._get_remote_tags(repo_url)
                if remote_tags:
                    latest_tag = remote_tags[0]
                    new_tag = latest_tag
                    update_type = "tag"
                    if current_tag != latest_tag:
                        new_commit = self._get_tag_commit_hash(repo_url, latest_tag)
                        update_available = True
                    else:
                        new_tag = current_tag
                        new_commit = current_commit
                else:
                    new_tag = current_tag
                    new_commit = current_commit
            else:
                latest_commit = self._get_latest_commit(repo_url)
                if latest_commit:
                    new_commit = latest_commit
                    update_available = current_commit != latest_commit
                else:
                    new_commit = current_commit

            current_version = current_tag or (
                current_commit[:7] if current_commit else "Unknown"
            )
            new_version = new_tag or (new_commit[:7] if new_commit else "Unknown")

            updates.append(
                {
                    "name": name,
                    "current_version": current_version,
                    "new_version": new_version,
                    "size": self._get_repo_size(plugin_path),
                    "released": self._get_time_since_tag(
                        plugin_path, new_tag or current_tag
                    ),
                    "changelog": (
                        [f"Update available: {current_version} → {new_version}"]
                        if update_available
                        else ["Up-to-date"]
                    ),
                    "marked": False,
                    "progress": 0,
                    "_internal": {
                        "type": update_type,
                        "old_tag": current_tag,
                        "new_tag": new_tag,
                        "old_commit": current_commit,
                        "new_commit": new_commit,
                        "plugin_path": plugin_path,
                        "repo_url": repo_url,
                        "update_available": update_available,
                    },
                }
            )

        return updates

    def update_plugin(
        self,
        update_info: dict[str, Any],
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> bool:
        name = update_info["name"]
        internal = update_info["_internal"]
        plugin_path = internal["plugin_path"]
        repo_url = internal["repo_url"]
        if not internal.get("update_available", False):
            return False

        def send_progress(progress: int) -> None:
            if progress_callback:
                progress_callback(name, progress)

        try:
            send_progress(10)

            if internal["type"] == "tag":
                tag = internal["new_tag"]
                subprocess.run(
                    [
                        "git",
                        "fetch",
                        "--depth=1",
                        "origin",
                        f"refs/tags/{tag}:refs/tags/{tag}",
                    ],
                    cwd=plugin_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                send_progress(50)
                subprocess.run(
                    ["git", "checkout", f"tags/{tag}"],
                    cwd=plugin_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )
            else:
                commit = internal["new_commit"]
                subprocess.run(
                    ["git", "fetch", "origin", commit],
                    cwd=plugin_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                send_progress(50)
                subprocess.run(
                    ["git", "checkout", commit],
                    cwd=plugin_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )

            send_progress(90)

            actual_commit = self._get_local_head_commit(plugin_path)
            success = self._write_lockfile_update(
                name,
                new_tag=internal.get("new_tag"),
                new_commit=actual_commit,
            )

            if success:
                send_progress(100)
                return True
            else:
                return False

        except subprocess.CalledProcessError as e:
            if hasattr(e, "stderr") and e.stderr:
                print(f"[red]Error details:[/red] {e.stderr}")
            send_progress(0)
            return False
        except Exception:
            send_progress(0)
            return False

    def update_plugin_async(
        self,
        update_info: dict[str, Any],
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> threading.Thread:
        name = update_info["name"]

        def thread_fn() -> None:
            try:
                success = self.update_plugin(update_info, progress_callback)
                if not success and progress_callback:
                    progress_callback(name, 0)
            except Exception:
                if progress_callback:
                    progress_callback(name, 0)
            finally:
                self._update_threads.pop(name, None)

        thread = threading.Thread(target=thread_fn, daemon=True)
        self._update_threads[name] = thread
        thread.start()
        return thread

    def update_marked_plugins(
        self,
        updates: list[dict[str, Any]],
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> list[threading.Thread]:
        threads: list[threading.Thread] = []
        for update in updates:
            if update.get("marked", False):
                thread = self.update_plugin_async(update, progress_callback)
                threads.append(thread)
        return threads

    def update_all_plugins(
        self,
        updates: list[dict[str, Any]],
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> list[threading.Thread]:
        threads: list[threading.Thread] = []
        for update in updates:
            if update.get("_internal", {}).get("update_available", False):
                thread = self.update_plugin_async(update, progress_callback)
                threads.append(thread)
        return threads

    def auto_update_all(self) -> None:
        updates = self.check_for_updates()
        lock_data = lfm.read_lock_file()
        available_updates = [
            u for u in updates if u.get("_internal", {}).get("update_available", False)
        ]

        if not available_updates:
            return

        for update in available_updates:
            name = update["name"]
            plugin_info = next(
                (p for p in lock_data.get("plugins", []) if p["name"] == name), None
            )

            if plugin_info and plugin_info.get("skip_auto_update", False):
                continue

            success = self.update_plugin(update)
            if success:
                print(f"{name} updated successfully")
            else:
                print(f"Failed to update {name}")

    def get_update_status(self, plugin_name: str) -> threading.Thread | None:
        return self._update_threads.get(plugin_name)

    def cancel_update(self, plugin_name: str) -> bool:
        thread = self._update_threads.get(plugin_name)
        if thread and thread.is_alive():
            return False
        return True

import asyncio
import os
from typing import Any

from packaging.version import InvalidVersion, Version


class PluginUpdater:
    def __init__(self, plugins_dir: str) -> None:
        self.plugins_dir = plugins_dir

    async def _plan_plugin_update(self, plugin: dict[str, Any]) -> dict[str, Any]:
        name = plugin["name"]
        plugin_path = os.path.join(self.plugins_dir, name)
        git_info = plugin.get("git", {})
        repo = git_info.get("repo")
        repo_url = f"https://github.com/{repo}" if repo else None

        if not os.path.exists(plugin_path) or not repo_url:
            return {
                "name": name,
                "_internal": {
                    "update_available": False,
                    "reason": "not_installed_or_missing_repo",
                },
            }

        current_tag = git_info.get("tag")
        current_commit = git_info.get("commit_hash")

        new_tag = None
        new_commit = None
        update_type = "commit"
        update_available = False

        if current_tag:
            remote_tags = await self._get_remote_tags(repo_url)
            if remote_tags:
                latest_tag = remote_tags[0]
                update_type = "tag"
                new_tag = latest_tag
                if current_tag != latest_tag:
                    new_commit = await self._get_tag_commit_hash(repo_url, latest_tag)
                    update_available = True
                else:
                    new_commit = current_commit
            else:
                new_commit = current_commit
        else:
            latest_commit = await self._get_latest_commit(repo_url)
            if latest_commit and latest_commit != current_commit:
                new_commit = latest_commit
                update_available = True
            else:
                new_commit = current_commit

        return {
            "name": name,
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

    async def _build_update_view(self, plan: dict[str, Any]) -> dict[str, Any]:
        name = plan["name"]
        internal = plan["_internal"]

        if not internal.get("update_available"):
            return {
                "name": name,
                "current_version": "Unknown",
                "new_version": "Unknown",
                "size": "N/A",
                "released": "N/A",
                "changelog": ["Up-to-date"],
                "marked": False,
                "progress": 0,
                "_internal": internal,
            }

        plugin_path = internal["plugin_path"]

        old_version = internal["old_tag"] or (
            internal["old_commit"][:7] if internal["old_commit"] else "Unknown"
        )
        new_version = internal["new_tag"] or (
            internal["new_commit"][:7] if internal["new_commit"] else "Unknown"
        )

        return {
            "name": name,
            "current_version": old_version,
            "new_version": new_version,
            "size": await self._get_repo_size(plugin_path),
            "released": await self._get_time_since_tag(
                plugin_path, internal.get("new_tag") or internal.get("old_tag")
            ),
            "changelog": [f"Update available: {old_version} → {new_version}"],
            "marked": False,
            "progress": 0,
            "_internal": internal,
        }

    async def check_for_update(self, plugin: dict[str, Any]) -> dict[str, Any]:
        plan = await self._plan_plugin_update(plugin)
        view = await self._build_update_view(plan)
        return view

    async def _get_local_head_commit(
        self, plugin_path: str, short: bool = False
    ) -> str | None:
        try:
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

            output = stdout.decode().strip()
            if short:
                return output[:7]

            return output

        except OSError:
            return None

    async def _get_repo_size(self, plugin_path: str) -> str:
        try:
            process = await asyncio.create_subprocess_exec(
                "du",
                "-sh",
                ".git",
                cwd=plugin_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )

            stdout, _ = await process.communicate()

            if process.returncode != 0:
                return "Unknown"

            output = stdout.decode().strip()

            if not output:
                return "Unknown"

            return output.split()[0]

        except OSError:
            return "Unknown"

    async def _get_time_since_tag(self, plugin_path: str, tag: str | None) -> str:
        if not tag:
            return "Unknown"

        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                "log",
                "-1",
                "--format=%cr",
                f"tags/{tag}",
                cwd=plugin_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )

            stdout, _ = await process.communicate()

            if process.returncode != 0:
                return "Unknown"

            return stdout.decode().strip()
        except OSError:
            return "Unknown"

    def _semantic_sort_tags(self, tags: list[str]) -> list[str]:
        versions: list[tuple[Version, str]] = []

        for tag in set(tags):
            try:
                version = Version(tag.lstrip("v"))
                if version.is_prerelease:
                    continue
                versions.append((version, tag))
            except InvalidVersion:
                continue

        versions.sort(key=lambda x: x[0], reverse=True)
        return [tag for _, tag in versions]

    async def _get_remote_tags(self, repo_url: str) -> list[str]:
        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                "ls-remote",
                "--tags",
                repo_url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )

            stdout, _ = await process.communicate()

            if process.returncode != 0:
                return []

            tags: list[str] = []
            for line in stdout.decode().splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[1].startswith("refs/tags/"):
                    tag = parts[1].split("/")[-1]
                    if tag.endswith("^{}"):
                        tag = tag[:-3]
                    tags.append(tag)
            return self._semantic_sort_tags(tags)
        except OSError:
            return []

    async def _get_latest_commit(
        self, repo_url: str, branch: str = "HEAD"
    ) -> str | None:
        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                "ls-remote",
                repo_url,
                branch,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )

            stdout, _ = await process.communicate()

            if process.returncode != 0:
                return None

            output = stdout.decode().strip()
            if not output:
                return None

            return output.split()[0]

        except OSError:
            return None

    async def _get_tag_commit_hash(self, repo_url: str, tag: str) -> str | None:
        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                "ls-remote",
                repo_url,
                f"refs/tags/{tag}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )

            stdout, _ = await process.communicate()

            if process.returncode != 0:
                return None

            output = stdout.decode().strip()
            if not output:
                return None

            return output.split()[0]
        except OSError:
            return None

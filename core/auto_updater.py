import asyncio
import time
from datetime import timedelta
from typing import Any

from core import lock_file_manager as lfm
from core.plugin_updater import PluginUpdater
from core.plugin_upgrader import PluginUpgrader


class AutoUpdater:
    def __init__(
        self, plugins_dir: str, interval: timedelta = timedelta(days=1)
    ) -> None:
        self.plugins_dir = plugins_dir
        self.interval = interval

    async def run_upgrades(self) -> None:
        lock_file = lfm.read_lock_file()

        if not self._should_run(lock_file):
            return

        candidates = self._get_candidates(lock_file.get("plugins", []))

        if candidates:
            available_updates = await self._check_for_updates(candidates)

            if available_updates:
                await self._upgrade_plugins(available_updates)

        self._record_check()

    async def _check_for_updates(
        self, candidates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        updater = PluginUpdater(self.plugins_dir)

        checks = await asyncio.gather(
            *(updater.check_for_update(plugin) for plugin in candidates),
            return_exceptions=True,
        )

        return [
            check
            for check in checks
            if isinstance(check, dict)
            and check.get("_internal", {}).get("update_available", False)
        ]

    async def _upgrade_plugins(self, available_updates: list[dict[str, Any]]) -> None:
        upgrader = PluginUpgrader()

        results = await asyncio.gather(
            *(upgrader.upgrade_plugin(update) for update in available_updates),
            return_exceptions=True,
        )

        successful_results = [result for result in results if isinstance(result, dict)]

        if successful_results:
            upgrader.update_lock_file(successful_results)

    def _record_check(self) -> None:
        lock_file = lfm.read_lock_file()
        metadata = lock_file.get("metadata")

        new_metadata: lfm.LockMetadata = {
            "last_auto_update_check": int(time.time()),
            "last_self_update_check": (
                metadata.get("last_self_update_check", 0) if metadata else 0
            ),
        }

        lock_file["metadata"] = new_metadata
        lfm.write_lock_file(lock_file)

    def _should_run(self, lock_file: lfm.LockData) -> bool:
        metadata = lock_file.get("metadata")

        if not metadata:
            return True

        last_check = max(
            metadata.get("last_auto_update_check", 0),
            metadata.get("last_self_update_check", 0),
        )

        time_diff = time.time() - last_check

        return time_diff >= self.interval.total_seconds()

    def _get_candidates(self, plugins: list[dict[str, Any]]) -> list[dict[str, Any]]:
        candidates = [
            plugin for plugin in plugins if not plugin.get("skip_auto_update", False)
        ]
        return candidates

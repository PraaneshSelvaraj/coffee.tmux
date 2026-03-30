"""
Upgrade command implementation
"""

import asyncio
from typing import Any

from rich.progress import TaskID

from core import PluginUpdater, PluginUpgrader
from core import lock_file_manager as lfm

from ..utils import (
    COFFEE_PLUGINS_DIR,
    HIGHLIGHT_COLOR,
    confirm_action,
    console,
    create_progress,
    print_error,
    print_info,
)


class Args:
    plugin: str | None
    quiet: bool


async def run(args: Args) -> int:
    """Run upgrade command"""
    try:
        updater = PluginUpdater(COFFEE_PLUGINS_DIR)

        lock_data = lfm.read_lock_file()
        plugins = lock_data.get("plugins", [])

        update_tasks = [updater.check_for_update(plugin) for plugin in plugins]
        updates = await asyncio.gather(*update_tasks)

        # Filter plugins with available updates
        available_updates = [
            u for u in updates if u.get("_internal", {}).get("update_available", False)
        ]

        if not available_updates:
            if not args.quiet:
                console.print(f"[bold {HIGHLIGHT_COLOR}]All plugins are up-to-date![/]")
            return 0

        # Filter for specific plugin if requested
        if args.plugin:
            available_updates = [
                u for u in available_updates if u.get("name") == args.plugin
            ]
            if not available_updates:
                print_error(f"No updates available for '{args.plugin}'")
                return 1

        # Confirm upgrade
        if not args.quiet:
            plugin_names = [u.get("name", "Unknown") for u in available_updates]
            if not confirm_action(
                f"Upgrade {len(available_updates)} plugin(s): {', '.join(plugin_names)}?",
                True,
            ):
                print_info("Upgrade cancelled")
                return 0

        # Perform upgrades
        if not args.quiet:
            print_info(f"Upgrading {len(available_updates)} plugin(s)...")

        upgrader = PluginUpgrader()
        results: list[dict[str, Any] | None] = []

        if args.quiet:
            # Quiet mode - no progress bars
            tasks = [upgrader.upgrade_plugin(update) for update in available_updates]
            results = await asyncio.gather(*tasks)

        else:
            # Normal mode with progress bars
            with create_progress() as progress:
                tasks = []

                for update in available_updates:
                    task_id: TaskID = progress.add_task(
                        f"Upgrading {update.get('name', 'Unknown')}", total=100
                    )

                    # Callback for progress update
                    def callback(percent: int, task_id: TaskID = task_id) -> None:
                        progress.update(task_id, completed=percent)

                    tasks.append(
                        upgrader.upgrade_plugin(update, progress_callback=callback)
                    )

                results = await asyncio.gather(*tasks)

        successful_results = [r for r in results if r is not None]
        if successful_results:
            upgrader.update_lock_file(successful_results)

        success_count = len(successful_results)

        if not args.quiet:
            if success_count == len(available_updates):
                console.print(
                    f"[bold {HIGHLIGHT_COLOR}]SUCCESS[/] All {success_count} plugin(s) upgraded successfully!",
                    highlight=False,
                )
            else:
                print_info(f"Upgraded {success_count}/{len(available_updates)} plugins")

        return 0

    except Exception as e:
        print_error(f"Upgrade failed: {e}")
        return 1

"""
Upgrade command implementation
"""

from typing import Any, List, Optional

from rich.progress import TaskID

from core import PluginUpdater

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
    plugin: Optional[str]
    quiet: bool


def run(args: Args) -> int:
    """Run upgrade command"""
    try:
        updater = PluginUpdater(COFFEE_PLUGINS_DIR)
        updates: List[dict[str, Any]] = updater.check_for_updates()

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

        success_count = 0

        if args.quiet:
            # Quiet mode - no progress bars
            for update in available_updates:
                success = updater.update_plugin(update)
                if success:
                    success_count += 1
        else:
            # Normal mode with progress bars
            with create_progress() as progress:
                for update in available_updates:
                    task_id: TaskID = progress.add_task(
                        f"Upgrading {update.get('name', 'Unknown')}", total=100
                    )

                    # Callback for progress update
                    def callback(
                        plugin_name: str, percent: int, task_id: TaskID = task_id
                    ) -> None:
                        progress.update(task_id, completed=percent)

                    success = updater.update_plugin(update, callback)
                    if success:
                        success_count += 1
                        progress.update(task_id, completed=100)
                        console.print(
                            f"[bold {HIGHLIGHT_COLOR}]UPGRADED[/] {update.get('name', 'Unknown')} to [bold white]{update.get('new_version', 'N/A')}[/]"
                        )
                    else:
                        progress.update(task_id, completed=0)
                        print_error(
                            f"Failed to upgrade {update.get('name', 'Unknown')}"
                        )

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

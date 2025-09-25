"""
Update command implementation
"""

from typing import Any, List

from core import PluginUpdater

from ..utils import (
    ACCENT_COLOR,
    COFFEE_PLUGINS_DIR,
    HIGHLIGHT_COLOR,
    console,
    print_error,
    print_info,
)


class Args:
    quiet: bool


def run(args: Args) -> int:
    """Run update command"""
    try:
        if not args.quiet:
            print_info("Checking for plugin updates...")
        updater = PluginUpdater(COFFEE_PLUGINS_DIR)
        updates: List[dict[str, Any]] = updater.check_for_updates()

        if not updates:
            if not args.quiet:
                print_info("No plugins installed")
            return 0

        # Filter plugins with available updates
        available_updates = [
            u for u in updates if u.get("_internal", {}).get("update_available", False)
        ]

        if not available_updates:
            if not args.quiet:
                console.print(f"[bold {HIGHLIGHT_COLOR}]All plugins are up-to-date![/]")
            return 0

        if not args.quiet:
            # Show available updates
            console.print(
                f"\n[bold {ACCENT_COLOR}]UPDATES[/] {len(available_updates)} update(s) available:",
                highlight=False,
            )

            for update in available_updates:
                console.print(
                    f"  [bold white]{update['name']}[/]: [dim white]{update['current_version']}[/] → [bold {HIGHLIGHT_COLOR}]{update['new_version']}[/]"
                )
            console.print(f"\nRun [bold white]'coffee upgrade'[/] to install updates")
        return 0

    except Exception as e:
        print_error(f"Update check failed: {e}")
        return 1

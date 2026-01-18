"""
Remove command implementation
"""

from typing import Optional

from rich.progress import TaskID

from core import PluginRemover

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
    plugin: str
    force: bool
    quiet: bool


def run(args: Args) -> int:
    """Run remove command"""
    try:
        remover = PluginRemover(COFFEE_PLUGINS_DIR)
        installed_plugins = remover.get_installed_plugins()

        # Check if plugin exists
        plugin_to_remove: Optional[dict] = None
        for plugin in installed_plugins:
            if plugin.get("name") == args.plugin:
                plugin_to_remove = plugin
                break
        if not plugin_to_remove:
            print_error(f"Plugin '{args.plugin}' is not installed")
            return 1

        # Confirm removal
        if not args.force and not args.quiet:
            plugin_info = (
                f"{plugin_to_remove['name']} ({plugin_to_remove.get('version', 'N/A')})"
            )
            if not confirm_action(f"Remove plugin {plugin_info}?", False):
                print_info("Removal cancelled")
                return 0

        # Remove plugin
        if not args.quiet:
            print_info(f"Removing {args.plugin}...")

        success: bool
        if args.quiet:
            # Quiet mode - no progress bar
            success = remover.remove_plugin(args.plugin)
        else:
            # Normal mode with progress bar
            with create_progress() as progress:
                task_id: TaskID = progress.add_task(
                    f"Removing {args.plugin}", total=100
                )

                # Callback to update progress
                def callback(
                    plugin_name: str, percent: int, task_id: TaskID = task_id
                ) -> None:
                    progress.update(task_id, completed=percent)

                success = remover.remove_plugin(args.plugin, callback)
                if success:
                    progress.update(task_id, completed=100)

        if success:
            if not args.quiet:
                console.print(
                    f"[bold {HIGHLIGHT_COLOR}]SUCCESS[/] Successfully removed {args.plugin}"
                )
            return 0
        else:
            print_error(f"Failed to remove {args.plugin}")
            return 1

    except Exception as e:
        print_error(f"Remove failed: {e}")
        return 1

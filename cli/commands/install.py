"""
Install command implementation
"""

import os
from typing import Any, Optional

from rich.progress import TaskID

from core import PluginInstaller, PluginLoader

from ..utils import (
    ACCENT_COLOR,
    COFFEE_CONFIG_DIR,
    COFFEE_PLUGINS_DIR,
    HIGHLIGHT_COLOR,
    console,
    create_progress,
    print_error,
    print_info,
)


class Args:
    plugin: Optional[str]
    quiet: bool
    force: bool


def run(args: Args) -> int:
    """Run install command"""
    try:
        # Load plugin configurations
        plugin_loader = PluginLoader(COFFEE_CONFIG_DIR)
        plugins: list[dict[str, Any]] = plugin_loader.load_plugins()

        if not plugins:
            if not args.quiet:
                print_info(
                    "No plugins configured. Add YAML files to ~/.config/tmux/coffee/plugins/"
                )
            return 0

        # Filter for specific plugin if requested
        if args.plugin:
            plugins = [p for p in plugins if p["name"] == args.plugin]
            if not plugins:
                print_error(f"Plugin '{args.plugin}' not found in configuration")
                return 1

        # Check which plugins actually need installation
        plugins_to_install: list[dict[str, Any]] = []
        for plugin in plugins:
            plugin_path = os.path.join(COFFEE_PLUGINS_DIR, plugin["name"])

            if not os.path.exists(plugin_path) or args.force:
                plugins_to_install.append(plugin)

            elif not args.quiet:
                console.print(
                    f"[bold {ACCENT_COLOR}]SKIP[/] {plugin['name']} (already installed)"
                )

        if not plugins_to_install:
            if not args.quiet:
                console.print(
                    f"[bold {HIGHLIGHT_COLOR}]All plugins are already installed![/]"
                )
            return 0

        # Install plugins
        installer = PluginInstaller(
            plugins_to_install,
            COFFEE_PLUGINS_DIR,
            os.path.expanduser("~/.config/tmux/"),
        )

        if not args.quiet:
            print_info(f"Installing {len(plugins_to_install)} plugin(s)...")

        if args.quiet:
            # Quiet mode - no progress bars
            for plugin in plugins_to_install:
                success, used_tag = installer.install_git_plugin(
                    plugin, force=args.force
                )
                if not success:
                    print_error(f"Failed to install {plugin['name']}")
                    return 1
        else:
            # Normal mode with progress bars
            with create_progress() as progress:
                for plugin in plugins_to_install:
                    task_id: TaskID = progress.add_task(
                        f"Installing {plugin['name']}", total=100
                    )

                    # Fixed callback - only expects percent argument
                    def callback(percent: int, task_id: TaskID = task_id) -> None:
                        progress.update(task_id, completed=percent)

                    success, used_tag = installer.install_git_plugin(
                        plugin, callback, force=args.force
                    )

                    if success:
                        progress.update(task_id, completed=100)
                        console.print(
                            f"[bold {HIGHLIGHT_COLOR}]SUCCESS[/] Installed {plugin['name']} @ [bold white]{used_tag or 'latest'}[/]"
                        )

                    else:
                        progress.update(task_id, completed=0)
                        print_error(f"Failed to install {plugin['name']}")

        if not args.quiet:
            console.print(f"[bold {HIGHLIGHT_COLOR}]SUCCESS[/] Installation complete!")

        return 0

    except Exception as e:
        print_error(f"Installation failed: {e}")
        return 1

"""
List command implementation
"""

from typing import Any, List

from core import PluginRemover

from ..utils import (
    ACCENT_COLOR,
    COFFEE_PLUGINS_DIR,
    ERROR_COLOR,
    HIGHLIGHT_COLOR,
    console,
    format_plugin_table,
    print_error,
    print_info,
)


class Args:
    quiet: bool
    table: bool


def run(args: Args) -> int:
    """Run list command"""
    try:
        remover = PluginRemover(COFFEE_PLUGINS_DIR)
        plugins: List[dict[str, Any]] = remover.get_installed_plugins()

        if not plugins:
            if not args.quiet:
                print_info("No plugins installed")
            return 0

        if args.table:
            # Table format
            table = format_plugin_table(plugins, f"Installed Plugins ({len(plugins)})")
            console.print(table)
        else:
            # Simple format (default)
            console.print(
                f"[bold {ACCENT_COLOR}]Installed plugins ({len(plugins)}):[/]"
            )

            for plugin in plugins:
                name = plugin["name"]
                version = plugin.get("version", "N/A")
                enabled = plugin.get("enabled", True)

                if enabled:
                    console.print(
                        f"  [{HIGHLIGHT_COLOR}]●[/] [bold white]{name}[/] [dim white]{version}[/]"
                    )
                else:
                    console.print(
                        f"  [{ERROR_COLOR}]●[/] [bold white]{name}[/] [dim white]{version}[/]"
                    )
        return 0

    except Exception as e:
        print_error(f"List failed: {e}")
        return 1

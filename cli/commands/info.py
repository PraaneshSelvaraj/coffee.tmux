"""
Info command implementation
"""

from typing import Any, Optional

from rich.panel import Panel
from rich.text import Text

from core import PluginRemover
from core import lock_file_manager as lfm

from ..utils import (
    ACCENT_COLOR,
    COFFEE_PLUGINS_DIR,
    ERROR_COLOR,
    HIGHLIGHT_COLOR,
    SECTION_COLOR,
    console,
    print_error,
)


class Args:
    plugin: str


def run(args: Args) -> int:
    """Run info command"""
    try:
        remover = PluginRemover(COFFEE_PLUGINS_DIR)
        installed_plugins: list[dict[str, Any]] = remover.get_installed_plugins()

        # Find the plugin
        plugin_info: Optional[dict[str, Any]] = None

        for plugin in installed_plugins:
            if plugin.get("name") == args.plugin:
                plugin_info = plugin
                break
        if not plugin_info:
            print_error(f"Plugin '{args.plugin}' is not installed")
            return 1

        # Get additional info from lock file
        lock_data: lfm.LockData = lfm.read_lock_file()
        lock_plugin: Optional[dict[str, Any]] = None

        for p in lock_data.get("plugins", []):
            if p.get("name") == args.plugin:
                lock_plugin = p
                break

        # Create info display
        info_text = Text()
        info_text.append(f"Name: {plugin_info['name']}\n", style="bold white")
        info_text.append(
            f"Version: {plugin_info.get('version', 'N/A')}\n", style=ACCENT_COLOR
        )
        info_text.append(
            f"Size: {plugin_info.get('size', 'N/A')}\n", style=SECTION_COLOR
        )
        info_text.append(f"Installed: {plugin_info.get('installed', 'N/A')}\n")

        status = "Enabled" if plugin_info.get("enabled", True) else "Disabled"
        status_style = (
            HIGHLIGHT_COLOR if plugin_info.get("enabled", True) else ERROR_COLOR
        )
        info_text.append(f"Status: {status}\n", style=f"bold {status_style}")

        if lock_plugin:
            git_info = lock_plugin.get("git", {})

            if git_info.get("repo"):
                info_text.append(f"Repository: {git_info['repo']}\n", style="dim white")

            if git_info.get("commit_hash"):
                commit_hash = git_info["commit_hash"]
                info_text.append(
                    f"Commit: {commit_hash[:7] if commit_hash else 'N/A'}\n",
                    style="dim white",
                )

            if git_info.get("last_pull"):
                info_text.append(
                    f"Last Updated: {git_info['last_pull']}\n", style="dim white"
                )

            sources = lock_plugin.get("sources", [])
            if sources:
                info_text.append("\nSource Files:\n", style="bold white")
                for source in sources:
                    info_text.append(f"  {source}\n", style=ACCENT_COLOR)

        panel = Panel(
            info_text,
            title=f"[bold {ACCENT_COLOR}]Coffee - {plugin_info['name']}[/]",
            border_style=ACCENT_COLOR,
        )
        console.print(panel)

        return 0

    except Exception as e:
        print_error(f"Info failed: {e}")
        return 1

from typing import Any

from rich.box import ROUNDED
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from core import PluginLoader
from core import lock_file_manager as lfm

from ..constants import (
    ACCENT_COLOR,
    BACKGROUND_STYLE,
    COFFEE_PLUGINS_LIST_DIR,
    HIGHLIGHT_COLOR,
    SECTION_COLOR,
    SELECTION_COLOR,
)
from .base import Tab


class InstallTab(Tab):
    def __init__(self) -> None:
        super().__init__("Install")

    def _get_installable_plugins(self, app_state: Any) -> list[dict[str, Any]]:
        plugin_loader = PluginLoader(COFFEE_PLUGINS_LIST_DIR)
        config_plugins = plugin_loader.load_plugins()
        lock_data = lfm.read_lock_file()
        installed_plugin_names = {p.get("name") for p in lock_data.get("plugins", [])}
        installable = []
        for plugin in config_plugins:
            if plugin["name"] not in installed_plugin_names:
                plugin_data = {
                    "name": plugin["name"],
                    "url": plugin["url"],
                    "tag": plugin.get("tag", "latest"),
                    "description": f"{plugin['url']}",
                    "sources": len(plugin.get("source", [])),
                    "marked": False,
                    "progress": 0,
                    "_config": plugin,
                }
                installable.append(plugin_data)
        return installable

    def build_install_list_panel(self, app_state: Any) -> Panel:
        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column("Plugin", ratio=1)

        if not hasattr(app_state, "install_data") or not app_state.install_data:
            installable_plugins = self._get_installable_plugins(app_state)
            app_state.install_data = installable_plugins
        else:
            installable_plugins = app_state.install_data

        if not installable_plugins:
            table.add_row(
                Text("✓ All configured plugins are installed", style="bold #9ece6a")
            )
        else:
            for i, plugin in enumerate(installable_plugins):
                is_selected = i == app_state.install_selected
                marked = plugin.get("marked", False)
                mark_text = Text(
                    "[✓] " if marked else "[ ] ",
                    style=f"bold {SELECTION_COLOR}" if marked else "dim white",
                )
                tag_text = f" ({plugin['tag']})" if plugin["tag"] != "latest" else ""
                name_text = Text(
                    f"{plugin['name']}{tag_text}",
                    style=f"bold {SELECTION_COLOR}" if is_selected else "white",
                )
                progress = plugin.get("progress", 0)
                progress_text_obj = Text()
                if 0 < progress < 100:
                    bar_len = 15
                    filled_len = int(progress / 100 * bar_len)
                    bar = "█" * filled_len + "░" * (bar_len - filled_len)
                    progress_text_obj = Text(f" {bar} {progress}%", style="yellow")
                elif progress == 100:
                    progress_text_obj = Text(" ✔ Installed", style="green")
                row_text_obj = Text.assemble(mark_text, name_text, progress_text_obj)
                table.add_row(row_text_obj)
        title = f"Available for Install ({len(installable_plugins)})"
        return Panel(
            table,
            title=title,
            border_style=ACCENT_COLOR,
            box=ROUNDED,
            style=BACKGROUND_STYLE,
        )

    def build_install_details_panel(self, app_state: Any) -> Panel:
        installable_plugins = getattr(app_state, "install_data", [])
        if not installable_plugins or app_state.install_selected >= len(
            installable_plugins
        ):
            details = Text(
                "No plugin selected or all plugins installed.\n\nAdd plugins to your YAML config files to see them here."
            )
        else:
            plugin = installable_plugins[app_state.install_selected]
            details = Text()
            details.append(f"● {plugin['name']}\n\n", style=f"bold {SECTION_COLOR}")
            details.append(
                f"{'Repository':<18}: {plugin['description']}\n", style="white"
            )
            details.append(f"{'Version':<18}: {plugin['tag']}\n", style="white")
            progress = plugin.get("progress", 0)
            if 0 < progress < 100:
                bar_len = 20
                filled_len = int(progress / 100 * bar_len)
                bar = "█" * filled_len + "░" * (bar_len - filled_len)
                details.append(f"Installing... {bar} {progress}%\n", style="yellow")
            elif progress == 100:
                details.append("✔ Successfully installed\n", style="green")
            elif plugin.get("marked", False):
                details.append("Status: Marked for installation\n", style="yellow")
            else:
                details.append("Status: Ready to install\n", style=HIGHLIGHT_COLOR)
        return Panel(
            details,
            title="Plugin Details",
            border_style=ACCENT_COLOR,
            box=ROUNDED,
            style=BACKGROUND_STYLE,
        )

    def build_install_controls_panel(self, app_state: Any) -> Panel:
        controls = Text()
        controls.append("[Space] Mark/Unmark ", style="#5F9EA0")
        controls.append("[i] Install Marked ", style="#5F9EA0")
        controls.append("[ctrl+a] Install All ", style="#5F9EA0")
        installable_plugins = getattr(app_state, "install_data", [])
        marked_count = len([p for p in installable_plugins if p.get("marked", False)])
        if marked_count > 0:
            controls.append(f"({marked_count} marked)", style="yellow")
        return Panel(
            controls,
            title="Controls",
            border_style=ACCENT_COLOR,
            box=ROUNDED,
            style=BACKGROUND_STYLE,
        )

    def build_panel(self, app_state: Any) -> Layout:
        left = self.build_install_list_panel(app_state)
        right = self.build_install_details_panel(app_state)
        layout = Layout(name="install_layout")
        layout.split_row(Layout(left, ratio=1), Layout(right, ratio=1))
        bottom = self.build_install_controls_panel(app_state)
        main_layout = Layout()
        main_layout.split_column(Layout(layout, ratio=3), Layout(bottom, size=3))
        return main_layout

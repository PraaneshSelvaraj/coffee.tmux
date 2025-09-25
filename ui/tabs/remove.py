from typing import Any, List, Set

from rich.box import ROUNDED
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..constants import (
    ACCENT_COLOR,
    BACKGROUND_STYLE,
    HIGHLIGHT_COLOR,
    SECTION_COLOR,
    SELECTION_COLOR,
)
from .base import Tab


class RemoveTab(Tab):
    def __init__(self) -> None:
        super().__init__("Remove")

    def build_remove_list_panel(self, app_state: Any) -> Panel:
        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column("Plugin", ratio=1)

        if not app_state.remove_data:
            table.add_row(Text("No plugins installed", style="bold #9ece6a"))
        else:
            for i, plugin in enumerate(app_state.remove_data):
                is_selected = i == app_state.remove_selected
                marked = plugin["name"] in getattr(
                    app_state, "marked_for_removal", set()
                )
                mark_text = Text(
                    "[✓] " if marked else "[ ] ",
                    style=f"bold {SELECTION_COLOR}" if marked else "dim white",
                )
                version_text = (
                    f" ({plugin['version']})" if plugin["version"] != "N/A" else ""
                )
                name_text = Text(
                    f"{plugin['name']}{version_text}",
                    style=f"bold {SELECTION_COLOR}" if is_selected else "white",
                )
                progress = app_state.removing_progress.get(plugin["name"], 0)
                progress_text_obj = Text()
                if 0 < progress < 100:
                    bar_len = 15
                    filled_len = int(progress / 100 * bar_len)
                    bar = "█" * filled_len + "░" * (bar_len - filled_len)
                    progress_text_obj = Text(f" {bar} {progress}%", style="yellow")
                elif progress == 100:
                    progress_text_obj = Text(" ✔ Removed", style="green")
                row_text_obj = Text.assemble(mark_text, name_text, progress_text_obj)
                table.add_row(row_text_obj)

        title = f"Installed Plugins ({len(app_state.remove_data) if app_state.remove_data else 0})"
        return Panel(
            table,
            title=title,
            border_style=ACCENT_COLOR,
            box=ROUNDED,
            style=BACKGROUND_STYLE,
        )

    def build_remove_details_panel(self, app_state: Any) -> Panel:
        if not app_state.remove_data or app_state.remove_selected >= len(
            app_state.remove_data
        ):
            details = Text(
                "No plugin selected or no plugins installed.\n\nPress 'R' to refresh the plugin list."
            )
        else:
            plugin = app_state.remove_data[app_state.remove_selected]
            details = Text()
            details.append(f"● {plugin['name']}\n\n", style=f"bold {SECTION_COLOR}")
            details.append(f"{'Version':<18}: {plugin['version']}\n", style="white")
            details.append(f"{'Size':<18}: {plugin['size']}\n", style="white")
            details.append(f"{'Installed':<18}: {plugin['installed']}\n", style="white")
            details.append(
                f"{'Status':<18}: {'Enabled' if plugin['enabled'] else 'Disabled'}\n",
                style="white",
            )
            details.append("\n")
            progress = app_state.removing_progress.get(plugin["name"], 0)
            if 0 < progress < 100:
                bar_len = 20
                filled_len = int(progress / 100 * bar_len)
                bar = "█" * filled_len + "░" * (bar_len - filled_len)
                details.append(f"Removing... {bar} {progress}%\n", style="yellow")
            elif progress == 100:
                details.append("✔ Successfully removed\n", style="green")
            elif plugin["name"] in getattr(app_state, "marked_for_removal", set()):
                details.append("Status: Marked for removal\n", style="yellow")
            else:
                details.append("Status: Available for removal\n", style=HIGHLIGHT_COLOR)
        return Panel(
            details,
            title="Plugin Details",
            border_style=ACCENT_COLOR,
            box=ROUNDED,
            style=BACKGROUND_STYLE,
        )

    def build_remove_controls_panel(self, app_state: Any) -> Panel:
        controls = Text()
        controls.append("[Space] Mark/Unmark ", style="#5F9EA0")
        controls.append("[r] Remove Marked ", style="#5F9EA0")
        marked_count = len(getattr(app_state, "marked_for_removal", set()))
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
        left = self.build_remove_list_panel(app_state)
        right = self.build_remove_details_panel(app_state)
        layout = Layout(name="remove_layout")
        layout.split_row(Layout(left, ratio=1), Layout(right, ratio=1))
        bottom = self.build_remove_controls_panel(app_state)
        main_layout = Layout()
        main_layout.split_column(Layout(layout, ratio=3), Layout(bottom, size=3))
        return main_layout

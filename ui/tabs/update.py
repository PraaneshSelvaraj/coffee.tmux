from typing import Any

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


class UpdateTab(Tab):
    def __init__(self) -> None:
        super().__init__("Update")

    def _get_updates_with_updates(self, app_state: Any) -> list[dict[str, Any]]:
        return [
            p
            for p in app_state.update_data
            if p.get("_internal", {}).get("update_available", False)
        ]

    def build_update_list_panel(self, app_state: Any) -> Panel:
        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column("Plugin", ratio=1)
        updates_with_updates = self._get_updates_with_updates(app_state)
        if app_state.checking_updates:
            table.add_row(Text("🔄 Checking for updates...", style="bold yellow"))
        elif not updates_with_updates:
            table.add_row(Text("✓ All plugins are up to date", style="bold #9ece6a"))
        else:
            for i, plugin in enumerate(updates_with_updates):
                is_selected = i == app_state.update_selected
                marked = plugin.get("marked", False)
                mark_text = Text(
                    "[✓] " if marked else "[ ] ",
                    style=f"bold {SELECTION_COLOR}" if marked else "dim white",
                )
                version_text = f" → {plugin['new_version']}"
                name_text = Text(
                    f"{plugin['name']}{version_text}",
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
                    progress_text_obj = Text(" ✔ Done", style="green")
                row_text_obj = Text.assemble(mark_text, name_text, progress_text_obj)
                table.add_row(row_text_obj)
        title = f"Available Updates ({len(updates_with_updates)})"
        return Panel(
            table,
            title=title,
            border_style=ACCENT_COLOR,
            box=ROUNDED,
            style=BACKGROUND_STYLE,
        )

    def build_update_details_panel(self, app_state: Any) -> Panel:
        updates_with_updates = self._get_updates_with_updates(app_state)
        if app_state.checking_updates:
            details = Text("🔄 Checking for updates...", style="yellow")
        elif not updates_with_updates or app_state.update_selected >= len(
            updates_with_updates
        ):
            details = Text(
                "No plugin selected or no update data available.\n\nPress 'c' to check for updates."
            )
        else:
            plugin = updates_with_updates[app_state.update_selected]
            internal_info = plugin.get("_internal", {})
            details = Text()
            details.append(f"● {plugin['name']}\n\n", style=f"bold {SECTION_COLOR}")
            details.append(
                f"{'Version':<18}: {plugin['current_version']} → {plugin['new_version']}\n",
                style="white",
            )
            details.append(f"{'Size':<18}: {plugin['size']}\n", style="white")
            details.append(f"{'Released':<18}: {plugin['released']}\n\n", style="white")
            if internal_info.get("update_available", False):
                details.append("What's New:\n", style="#5F9EA0")
                for line in plugin["changelog"][:5]:
                    details.append(f" • {line}\n", style="white")
            else:
                details.append("Status: Up to date\n", style=HIGHLIGHT_COLOR)
            progress = plugin.get("progress", 0)
            if progress > 0:
                bar_len = 20
                filled_len = int(progress / 100 * bar_len)
                bar = "█" * filled_len + "░" * (bar_len - filled_len)
                details.append(
                    f"\nUpdating... {bar} {progress}%\n", style=HIGHLIGHT_COLOR
                )
        return Panel(
            details,
            title="Update Details",
            border_style=ACCENT_COLOR,
            box=ROUNDED,
            style=BACKGROUND_STYLE,
        )

    def build_update_status_panel(self, app_state: Any) -> Panel:
        controls = Text()
        controls.append("[c] Check Updates ", style="#5F9EA0")
        controls.append("[Space] Mark/Unmark ", style="#5F9EA0")
        controls.append(f"[u] Update Marked ", style="#5F9EA0")
        controls.append(f"[Ctrl+u] Update All", style="#5F9EA0")
        return Panel(
            controls,
            title="Controls",
            border_style=ACCENT_COLOR,
            box=ROUNDED,
            style=BACKGROUND_STYLE,
        )

    def build_panel(self, app_state: Any) -> Layout:
        left = self.build_update_list_panel(app_state)
        right = self.build_update_details_panel(app_state)
        layout = Layout(name="update_layout")
        layout.split_row(Layout(left, ratio=1), Layout(right, ratio=1))
        bottom = self.build_update_status_panel(app_state)
        main_layout = Layout()
        main_layout.split_column(Layout(layout, ratio=3), Layout(bottom, size=3))
        return main_layout

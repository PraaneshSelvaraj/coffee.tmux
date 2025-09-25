from rich.layout import Layout
from rich.panel import Panel

from ..constants import BACKGROUND_STYLE, TABS


class Tab:
    def __init__(self, name: str) -> None:
        self.name = name

    def create_tab_bar(self, active_tab: str = "Home") -> Panel:
        tabs = ""
        for tab in TABS:
            if tab == active_tab:
                tabs += f"[reverse bold #1D8E5E bold white] {tab} [/] "
            else:
                tabs += f"[bold white] {tab} [/]"

        return Panel(
            tabs,
            title="Coffee",
            border_style="cyan",
            style=BACKGROUND_STYLE,
            padding=(0, 2),
        )

    def build_layout(self, active_tab: str = "Home") -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(self.create_tab_bar(active_tab), name="tab_bar", size=3),
            Layout(name="body", ratio=2),
        )
        return layout

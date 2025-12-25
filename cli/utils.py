"""
CLI utility functions
"""

import os
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
)
from rich.table import Table

console: Console = Console()

ACCENT_COLOR: str = "#7aa2f7"
BACKGROUND_COLOR: str = "#1a1b26"
HIGHLIGHT_COLOR: str = "#9ece6a"
SELECTION_COLOR: str = "#bb9af7"
SECTION_COLOR: str = "#e0af68"
ERROR_COLOR: str = "#f7768e"

# Directories
COFFEE_BASE_DIR: str = os.path.expanduser("~/.tmux/coffee")
COFFEE_SOURCE_DIR: str = os.path.expanduser("~/.local/share/coffee")
COFFEE_PLUGINS_DIR: str = os.path.join(COFFEE_BASE_DIR, "plugins")
COFFEE_CONFIG_DIR: str = os.path.expanduser("~/.config/tmux/coffee/plugins")
LOCK_FILE_PATH: str = os.path.join(COFFEE_BASE_DIR, "caffeine-lock.json")


def setup_directories() -> None:
    """Create necessary directories"""
    os.makedirs(COFFEE_PLUGINS_DIR, exist_ok=True)
    os.makedirs(COFFEE_BASE_DIR, exist_ok=True)
    os.makedirs(COFFEE_CONFIG_DIR, exist_ok=True)


def print_version() -> None:
    """Print Coffee version"""
    try:
        __version__: str = version("coffee-tmux")
    except PackageNotFoundError:
        __version__ = "0.1.0"
    console.print(
        f"Coffee {__version__}", style=f"bold {ACCENT_COLOR}", highlight=False
    )
    console.print("Modern tmux plugin manager", highlight=False)


def print_success(message: str) -> None:
    """Print success message"""
    console.print(f"[bold {HIGHLIGHT_COLOR}]SUCCESS[/] {message}", highlight=False)


def print_error(message: str) -> None:
    """Print error message"""
    console.print(f"[bold {ERROR_COLOR}]ERROR[/] {message}", highlight=False)


def print_warning(message: str) -> None:
    """Print warning message"""
    console.print(f"[bold {SECTION_COLOR}]WARNING[/] {message}", highlight=False)


def print_info(message: str) -> None:
    """Print info message"""
    console.print(f"[bold {ACCENT_COLOR}]INFO[/] {message}", highlight=False)


def confirm_action(message: str, default: bool = False) -> bool:
    """Ask for user confirmation"""
    suffix: str = " [Y/n]" if default else " [y/N]"
    try:
        response: str = input(f"{message}{suffix}: ").strip().lower()
        if not response:
            return default
        return response in ["y", "yes"]
    except KeyboardInterrupt:
        return False


def create_progress() -> Progress:
    """Create a rich progress bar"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(
            bar_width=40,
            style="grey70",
            complete_style=SELECTION_COLOR,
            finished_style=SELECTION_COLOR,
        ),
        TextColumn(
            f"[{SELECTION_COLOR}][progress.percentage]{{task.percentage:>3.0f}}%[/]"
        ),
        console=console,
    )


def format_plugin_table(plugins: list[dict[str, Any]], title: str = "Plugins") -> Table:
    """Format plugins as a rich table"""
    table: Table = Table(
        title=f"[bold {ACCENT_COLOR}]{title}[/]", border_style=ACCENT_COLOR
    )
    table.add_column("Name", style="bold white")
    table.add_column("Version", style=ACCENT_COLOR)
    table.add_column("Size", style=SECTION_COLOR)
    table.add_column("Status", style="white")

    for plugin in plugins:
        status: str = (
            f"[bold {HIGHLIGHT_COLOR}]Enabled[/]"
            if plugin.get("enabled", True)
            else f"[bold {ERROR_COLOR}]Disabled[/]"
        )
        table.add_row(
            plugin["name"],
            plugin.get("version", "N/A"),
            plugin.get("size", "N/A"),
            status,
        )
    return table

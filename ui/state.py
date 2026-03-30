import asyncio
from typing import Any

from rich.console import Console

from core import lock_file_manager as lfm

console = Console()


class AppState:
    def __init__(self, plugin_updater: Any, plugin_remover: Any) -> None:
        self.scroll_offset = 0
        self.current_selection = 0
        self.current_tab = "Home"
        self.mode = "normal"

        self.update_selected = 0
        self.update_data: list[dict] = []
        self.update_progress: dict[str, int] = {}
        self.checking_updates = False

        self.remove_selected = 0
        self.marked_for_removal: set[str] = set()
        self.removing_progress: dict[str, int] = {}
        self.remove_data: list[dict] = []

        self.install_selected = 0
        self.install_data: list[dict] = []
        self.installing_progress: dict[str, int] = {}

        self.plugin_remover = plugin_remover
        self.plugin_updater = plugin_updater
        self._app_ref: Any | None = None

    async def refresh_updates(self) -> None:
        self.checking_updates = True
        self.update_data = []
        self.update_progress = {}

        try:
            lock_data = lfm.read_lock_file()
            plugins = lock_data.get("plugins", [])

            tasks = [self.plugin_updater.check_for_update(plugin) for plugin in plugins]

            updates = await asyncio.gather(*tasks)

            self.update_data = updates

        except Exception as e:
            console.log(f"[ERROR] Error checking updates: {e}")
            self.update_data = []

        finally:
            self.checking_updates = False
            if self._app_ref:
                self._app_ref.rich_display.refresh()

    async def refresh_remove_data(self) -> None:
        try:
            self.remove_data = await self.plugin_remover.get_installed_plugins()
        except Exception as e:
            console.log(f"[ERROR] Error refreshing remove data: {e}")
            self.remove_data = []
        if self._app_ref:
            self._app_ref.rich_display.refresh()

    def update_progress_callback(self, plugin_name: str, progress: int) -> None:
        self.update_progress[plugin_name] = progress
        for plugin in self.update_data:
            if plugin["name"] == plugin_name:
                plugin["progress"] = progress
                break
        if self._app_ref:
            self._app_ref.rich_display.refresh()

    def remove_progress_callback(self, plugin_name: str, progress: int) -> None:
        self.removing_progress[plugin_name] = progress
        if self._app_ref:
            self._app_ref.rich_display.refresh()

    def install_progress_callback(self, plugin_name: str, progress: int) -> None:
        self.installing_progress[plugin_name] = progress
        for plugin in self.install_data:
            if plugin["name"] == plugin_name:
                plugin["progress"] = progress
                break
        if self._app_ref:
            self._app_ref.rich_display.refresh()

    def bind_app(self, app: Any) -> None:
        self._app_ref = app

import threading
from typing import Any, Dict, List, Optional, Set

from rich.console import Console

console = Console()


class AppState:
    def __init__(self, plugin_updater: Any, plugin_remover: Any) -> None:
        self.scroll_offset: int = 0
        self.current_selection: int = 0
        self.current_tab: str = "Home"
        self.mode: str = "normal"
        self.update_selected: int = 0
        self.update_data: List[Dict[str, Any]] = []
        self.update_progress: Dict[str, int] = {}
        self.checking_updates: bool = False
        self.remove_selected: int = 0
        self.marked_for_removal: Set[str] = set()
        self.removing_progress: Dict[str, int] = {}
        self.remove_data: List[Dict[str, Any]] = []
        self._app_ref: Optional[Any] = None
        self.install_selected: int = 0
        self.install_data: List[Dict[str, Any]] = []
        self.installing_progress: Dict[str, int] = {}
        self.plugin_remover = plugin_remover
        self.plugin_updater = plugin_updater

    def refresh_updates(self) -> None:
        if not self.checking_updates:
            self.checking_updates = True
            self.update_data = []
            self.update_progress = {}
            thread = threading.Thread(target=self._check_updates_async, daemon=True)
            thread.start()

    def refresh_remove_data(self) -> None:
        self.remove_data = self.plugin_remover.get_installed_plugins()

    def remove_uninstalled_plugins_from_updates(
        self, uninstalled_plugin_names: List[str]
    ) -> None:
        uninstalled_names_set = set(uninstalled_plugin_names)
        self.update_data = [
            plugin
            for plugin in self.update_data
            if plugin["name"] not in uninstalled_names_set
        ]
        for name in uninstalled_plugin_names:
            self.update_progress.pop(name, None)
        if self.update_selected >= len(self.update_data):
            self.update_selected = max(0, len(self.update_data) - 1)

    def _check_updates_async(self) -> None:
        try:
            updates = self.plugin_updater.check_for_updates()
            self.update_data = updates
        except Exception as e:
            self.update_data = []
            console.log(f"[ERROR] Error checking updates: {e}")
        finally:
            self.checking_updates = False
            if self._app_ref:
                self._app_ref.call_from_thread(self._app_ref.rich_display.refresh)

    def update_progress_callback(self, plugin_name: str, progress: int) -> None:
        self.update_progress[plugin_name] = progress
        for plugin in self.update_data:
            if plugin["name"] == plugin_name:
                plugin["progress"] = progress
                break
        if self._app_ref:
            self._app_ref.call_from_thread(self._app_ref.rich_display.refresh)

    def remove_progress_callback(self, plugin_name: str, progress: int) -> None:
        self.removing_progress[plugin_name] = progress
        if self._app_ref:
            self._app_ref.call_from_thread(self._app_ref.rich_display.refresh)

    def install_progress_callback(self, plugin_name: str, progress: int) -> None:
        self.installing_progress[plugin_name] = progress
        for plugin in self.install_data:
            if plugin["name"] == plugin_name:
                plugin["progress"] = progress
                break
        if self._app_ref:
            self._app_ref.call_from_thread(self._app_ref.rich_display.refresh)

    def bind_app(self, app: Any) -> None:
        self._app_ref = app

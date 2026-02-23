import asyncio
import os
import traceback
from typing import Any

from rich.console import Console
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding

from core import PluginInstaller, PluginRemover, PluginUpdater, PluginUpgrader

from .constants import PLUGINS_DIR, VISIBLE_ROWS
from .state import AppState
from .tabs.home import HomeTab
from .tabs.install import InstallTab
from .tabs.update import UpdateTab
from .utils import toggle_plugin
from .widgets.rich_display import RichDisplay

console = Console()


class PluginManagerApp(App):
    CSS = """RichDisplay { background: #1a1b26; width:100%; height:100%; }"""
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("H", "switch_to_home", "Home", show=False),
        Binding("I", "switch_to_install", "Install", show=False),
        Binding("U", "switch_to_update", "Updates", show=False),
        Binding("R", "switch_to_remove", "Remove", show=False),
        # Movement
        Binding("j", "move_down", "Down", show=False),
        Binding("k", "move_up", "Up", show=False),
        Binding("down", "move_down", "Down", show=False),
        Binding("up", "move_up", "Up", show=False),
        # Actions
        Binding("space", "toggle_plugin_or_mark", "Toggle/Mark", show=False),
        Binding("/", "enter_search_mode", "Search", show=False),
        Binding("escape", "exit_search_mode", "Exit Search", show=False),
        # Updates
        Binding("c", "check_updates", "Check Updates", show=False),
        Binding("ctrl+u", "update_all", "Update All", show=False),
        Binding("u", "update_marked", "Update Marked", show=False),
        # Removal
        Binding("r", "remove_marked", "Remove Marked", show=False),
        Binding("ctrl+r", "refresh_remove_list", "Refresh Remove list", show=False),
        # Installation
        Binding("i", "install_marked", "Install Marked", show=False),
        Binding("ctrl+a", "install_all", "Install All", show=False),
    ]

    def __init__(
        self,
        plugin_updater: PluginUpdater,
        plugin_upgrader: PluginUpgrader,
        plugin_remover: PluginRemover,
    ) -> None:
        super().__init__()
        self.plugin_updater = plugin_updater
        self.plugin_upgrader = plugin_upgrader
        self.plugin_remover = plugin_remover
        self.app_state = AppState(plugin_updater, plugin_remover)
        self.app_state.bind_app(self)
        self.rich_display: Any = None

    def compose(self) -> ComposeResult:
        self.rich_display = RichDisplay(self.app_state)
        yield self.rich_display

    def action_switch_to_home(self) -> None:
        self.app_state.current_tab = "Home"
        self.rich_display.refresh()

    def action_switch_to_install(self) -> None:
        self.app_state.current_tab = "Install"
        self.app_state.install_selected = 0
        install_tab = InstallTab()
        self.app_state.install_data = install_tab._get_installable_plugins(
            self.app_state
        )
        self.rich_display.refresh()

    def action_switch_to_update(self) -> None:
        self.app_state.current_tab = "Update"

        if not self.app_state.update_data and not self.app_state.checking_updates:
            _ = self.action_check_updates()

        self.rich_display.refresh()

    def action_switch_to_remove(self) -> None:
        self.app_state.current_tab = "Remove"

        if not self.app_state.remove_data:
            self.action_refresh_remove_list()

        self.rich_display.refresh()

    @work(exclusive=True)
    async def action_refresh_remove_list(self) -> None:
        if self.app_state.current_tab == "Remove":
            await self.app_state.refresh_remove_data()
            self.app_state.remove_selected = 0
            self.app_state.marked_for_removal.clear()
        self.rich_display.refresh()

    def action_move_down(self) -> None:
        if self.app_state.current_tab == "Home" and self.app_state.mode == "normal":
            display_list = HomeTab().get_display_list()
            if self.app_state.current_selection < len(display_list) - 1:
                self.app_state.current_selection += 1
                self._update_scroll_offset(display_list)
        elif self.app_state.current_tab == "Install":
            installable_plugins = getattr(self.app_state, "install_data", [])
            if (
                installable_plugins
                and self.app_state.install_selected < len(installable_plugins) - 1
            ):
                self.app_state.install_selected += 1
        elif self.app_state.current_tab == "Update":
            updates_with_updates = UpdateTab()._get_updates_with_updates(self.app_state)
            if (
                updates_with_updates
                and self.app_state.update_selected < len(updates_with_updates) - 1
            ):
                self.app_state.update_selected += 1
        elif self.app_state.current_tab == "Remove":
            if self.app_state.remove_selected < len(self.app_state.remove_data) - 1:
                self.app_state.remove_selected += 1
        self.rich_display.refresh()

    def action_move_up(self) -> None:
        if self.app_state.current_tab == "Home" and self.app_state.mode == "normal":
            if self.app_state.current_selection > 0:
                self.app_state.current_selection -= 1
                self._update_scroll_offset(HomeTab().get_display_list())
        elif self.app_state.current_tab == "Install":
            if self.app_state.install_selected > 0:
                self.app_state.install_selected -= 1
        elif self.app_state.current_tab == "Update":
            if self.app_state.update_selected > 0:
                self.app_state.update_selected -= 1
        elif self.app_state.current_tab == "Remove":
            if self.app_state.remove_selected > 0:
                self.app_state.remove_selected -= 1
        self.rich_display.refresh()

    def action_toggle_plugin_or_mark(self) -> None:
        if self.app_state.current_tab == "Home":
            toggle_plugin(self.app_state)
        elif self.app_state.current_tab == "Install":
            installable_plugins = getattr(self.app_state, "install_data", [])
            if installable_plugins and 0 <= self.app_state.install_selected < len(
                installable_plugins
            ):
                plugin = installable_plugins[self.app_state.install_selected]
                plugin["marked"] = not plugin.get("marked", False)
        elif self.app_state.current_tab == "Update":
            updates_with_updates = UpdateTab()._get_updates_with_updates(self.app_state)
            if updates_with_updates and 0 <= self.app_state.update_selected < len(
                updates_with_updates
            ):
                plugin = updates_with_updates[self.app_state.update_selected]
                plugin["marked"] = not plugin.get("marked", False)
        elif self.app_state.current_tab == "Remove":
            if 0 <= self.app_state.remove_selected < len(self.app_state.remove_data):
                plugin_name = self.app_state.remove_data[
                    self.app_state.remove_selected
                ]["name"]
                if plugin_name in self.app_state.marked_for_removal:
                    self.app_state.marked_for_removal.remove(plugin_name)
                else:
                    self.app_state.marked_for_removal.add(plugin_name)
        self.rich_display.refresh()

    @work(exclusive=True)
    async def action_check_updates(self) -> None:
        self.rich_display.refresh()
        await self.app_state.refresh_updates()

    @work(exclusive=True)
    async def install_plugins_in_background(
        self, plugins_to_install: list[dict]
    ) -> None:
        try:
            console.log(
                f"[blue]Background installation started for plugins: "
                f"{[p['name'] for p in plugins_to_install]}[/blue]"
            )

            installer = PluginInstaller(
                [p["_config"] for p in plugins_to_install],
                PLUGINS_DIR,
                os.path.expanduser("~/.config/tmux/"),
            )

            results: list[dict] = []
            installed_plugins: list[str] = []

            async def install_one(plugin_data: dict) -> tuple[str, dict | None]:
                plugin_name = plugin_data["name"]
                config = plugin_data["_config"]

                console.log(f"[blue]Starting installation for {plugin_name}[/blue]")

                def progress_callback(progress: int) -> None:
                    self.app_state.install_progress_callback(plugin_name, progress)

                try:
                    result = await installer.install_git_plugin(
                        config,
                        progress_callback,
                        force=False,
                    )

                    if result:
                        console.log(
                            f"[green]Successfully installed {plugin_name}[/green]"
                        )
                        self.app_state.install_progress_callback(plugin_name, 100)
                        return plugin_name, result
                    else:
                        console.log(f"[red]Failed to install {plugin_name}[/red]")
                        self.app_state.install_progress_callback(plugin_name, 0)
                        return plugin_name, None

                except Exception as e:
                    console.log(f"[red]Error installing {plugin_name}: {e}[/red]")
                    self.app_state.install_progress_callback(plugin_name, 0)
                    return plugin_name, None

            # Create tasks for all plugins
            tasks = [
                asyncio.create_task(install_one(plugin_data))
                for plugin_data in plugins_to_install
            ]

            # Wait for all to complete
            results_raw = await asyncio.gather(*tasks)

            # Process results
            for plugin_name, result in results_raw:
                if result:
                    results.append(result)
                    installed_plugins.append(plugin_name)

            # Write lock file once (batch update)
            if results:
                console.log("[blue]Updating lock file after installation[/blue]")
                installer.update_lock_file(results)

            # Remove installed plugins from install list
            if installed_plugins:
                console.log(
                    f"[green]Removing installed plugins from install list: "
                    f"{installed_plugins}[/green]"
                )

                self.app_state.install_data = [
                    p
                    for p in self.app_state.install_data
                    if p["name"] not in installed_plugins
                ]

                if self.app_state.install_selected >= len(self.app_state.install_data):
                    self.app_state.install_selected = max(
                        0, len(self.app_state.install_data) - 1
                    )

                self.notify(
                    f"Installed {len(installed_plugins)} plugin(s) successfully."
                )

            self.rich_display.refresh()

            console.log("[blue]Background installation worker completed[/blue]")

        except Exception as e:
            console.log(f"[red]Error in background installation: {e}[/red]")
            console.log(f"[red]Traceback: {traceback.format_exc()}[/red]")
            self.notify(
                f"Installation failed: {str(e)}",
                severity="error",
            )

    def action_install_marked(self) -> None:
        self.console.log("Ctrl+I pressed, installing all plugins...")
        if self.app_state.current_tab == "Install":
            installable_plugins = getattr(self.app_state, "install_data", [])
            marked_plugins = [p for p in installable_plugins if p.get("marked", False)]
            if marked_plugins:
                for plugin in marked_plugins:
                    plugin["progress"] = 0
                    self.app_state.installing_progress[plugin["name"]] = 0
                _ = self.install_plugins_in_background(marked_plugins)
                self.notify(f"Installing {len(marked_plugins)} marked plugin(s)...")
            else:
                self.notify(
                    "No plugins marked for installation. Use Space to mark plugins first."
                )
        self.rich_display.refresh()

    async def action_install_all(self) -> None:
        if self.app_state.current_tab == "Install":
            installable_plugins = getattr(self.app_state, "install_data", [])
            if installable_plugins:
                for plugin in installable_plugins:
                    plugin["progress"] = 0
                    self.app_state.installing_progress[plugin["name"]] = 0
                _ = self.install_plugins_in_background(installable_plugins)
                self.notify(f"Installing all {len(installable_plugins)} plugin(s)...")
        self.rich_display.refresh()

    @work(exclusive=True)
    async def upgrade_plugins_in_background(
        self, plugins_to_update: list[dict]
    ) -> None:
        try:
            console.log(
                f"[blue]Background upgrade started for: "
                f"{[p['name'] for p in plugins_to_update]}[/blue]"
            )

            results: list[dict] = []

            async def upgrade_one(plugin: dict) -> tuple[str, dict | None]:
                plugin_name = plugin["name"]

                console.log(f"[blue]Upgrading {plugin_name}[/blue]")

                def progress_cb(progress: int) -> None:
                    self.app_state.update_progress_callback(plugin_name, progress)

                try:
                    result = await self.plugin_upgrader.upgrade_plugin(
                        plugin,
                        progress_callback=progress_cb,
                    )

                    if result:
                        console.log(f"[green]Upgraded {plugin_name}[/green]")
                        return plugin_name, result
                    else:
                        console.log(f"[red]Failed upgrade {plugin_name}[/red]")
                        return plugin_name, None

                except Exception as e:
                    console.log(f"[red]Error upgrading {plugin_name}: {e}[/red]")
                    return plugin_name, None

            tasks = [
                asyncio.create_task(upgrade_one(plugin)) for plugin in plugins_to_update
            ]

            results_raw = await asyncio.gather(*tasks)

            for name, result in results_raw:
                if result:
                    results.append(result)

            # Update lock file once
            if results:
                console.log("[blue]Updating lock file after upgrade[/blue]")
                self.plugin_upgrader.update_lock_file(results)

            # Update UI state
            for plugin in plugins_to_update:
                if plugin.get("_internal", {}).get("update_available"):
                    plugin["_internal"]["update_available"] = False
                    plugin["current_version"] = plugin["new_version"]

            self.rich_display.refresh()

            console.log("[blue]Upgrade worker completed[/blue]")

        except Exception as e:
            console.log(f"[red]Upgrade worker failed: {e}[/red]")
            console.log(traceback.format_exc())
            self.notify(f"Upgrade failed: {e}", severity="error")

    def action_update_marked(self) -> None:
        if self.app_state.current_tab == "Update":
            marked_plugins = [
                p
                for p in self.app_state.update_data
                if p.get("marked", False)
                and p.get("_internal", {}).get("update_available", False)
            ]
            if marked_plugins:
                for plugin in marked_plugins:
                    plugin["progress"] = 0
                    self.app_state.update_progress[plugin["name"]] = 0
                _ = self.upgrade_plugins_in_background(marked_plugins)
                self.notify(f"Updating {len(marked_plugins)} marked plugin(s)...")
            else:
                self.notify("No plugins marked for update.")
            self.rich_display.refresh()

    def action_update_all(self) -> None:
        if self.app_state.current_tab == "Update":
            updates_with_updates = UpdateTab()._get_updates_with_updates(self.app_state)
            if updates_with_updates:
                for plugin in updates_with_updates:
                    plugin["progress"] = 0
                    self.app_state.update_progress[plugin["name"]] = 0
                    plugin["marked"] = True
                _ = self.upgrade_plugins_in_background(updates_with_updates)
                self.notify(f"Updating all {len(updates_with_updates)} plugin(s)...")
            else:
                self.notify("No updates available.")
            self.rich_display.refresh()

    def _update_scroll_offset(self, display_list: list[Any]) -> None:
        if (
            self.app_state.current_selection
            >= self.app_state.scroll_offset + VISIBLE_ROWS
        ):
            self.app_state.scroll_offset = (
                self.app_state.current_selection - VISIBLE_ROWS + 1
            )
        elif self.app_state.current_selection < self.app_state.scroll_offset:
            self.app_state.scroll_offset = self.app_state.current_selection

    @work(exclusive=True)
    async def remove_plugins_in_background(self, plugins_to_remove: list[str]) -> None:
        try:
            console.log(
                f"[blue]Background removal started for: {plugins_to_remove}[/blue]"
            )

            results: list[dict] = []
            removed_plugins: list[str] = []

            async def remove_one(plugin_name: str) -> tuple[str, dict | None]:
                console.log(f"[blue]Removing {plugin_name}[/blue]")

                def progress_cb(name: str, progress: int) -> None:
                    self.app_state.remove_progress_callback(name, progress)

                try:
                    result = await self.plugin_remover.remove_plugin(
                        plugin_name,
                        progress_callback=progress_cb,
                    )

                    if result:
                        console.log(f"[green]Removed {plugin_name}[/green]")
                        self.app_state.remove_progress_callback(plugin_name, 100)
                        return plugin_name, result
                    else:
                        console.log(f"[red]Failed {plugin_name}[/red]")
                        self.app_state.remove_progress_callback(plugin_name, 0)
                        return plugin_name, None

                except Exception as e:
                    console.log(f"[red]Error removing {plugin_name}: {e}[/red]")
                    self.app_state.remove_progress_callback(plugin_name, 0)
                    return plugin_name, None

            tasks = [
                asyncio.create_task(remove_one(name)) for name in plugins_to_remove
            ]

            results_raw = await asyncio.gather(*tasks)

            # Process results
            for name, result in results_raw:
                if result:
                    results.append(result)
                    removed_plugins.append(name)

            if results:
                console.log("[blue]Updating lock file after removal[/blue]")
                self.plugin_remover.update_lock_file(results)

            if removed_plugins:
                console.log(
                    f"[green]Updating UI after removal: {removed_plugins}[/green]"
                )

                self.app_state.remove_data = [
                    p
                    for p in self.app_state.remove_data
                    if p["name"] not in removed_plugins
                ]

                for name in removed_plugins:
                    self.app_state.marked_for_removal.discard(name)

                if self.app_state.remove_selected >= len(self.app_state.remove_data):
                    self.app_state.remove_selected = max(
                        0, len(self.app_state.remove_data) - 1
                    )

                self.notify(f"Removed {len(removed_plugins)} plugin(s) successfully.")

            self.rich_display.refresh()

            console.log("[blue]Removal worker completed[/blue]")

        except Exception as e:
            console.log(f"[red]Removal worker failed: {e}[/red]")
            console.log(traceback.format_exc())
            self.notify(f"Removal failed: {e}", severity="error")

    def action_remove_marked(self) -> None:
        if self.app_state.current_tab == "Remove":
            if self.app_state.marked_for_removal:
                marked_plugins = list(self.app_state.marked_for_removal)
                for plugin_name in marked_plugins:
                    self.app_state.removing_progress[plugin_name] = 0
                _ = self.remove_plugins_in_background(marked_plugins)
                self.notify(f"Removing {len(marked_plugins)} marked plugin(s)...")
            else:
                self.notify(
                    "No plugins marked for removal. Use Space to mark plugins first."
                )
        self.rich_display.refresh()

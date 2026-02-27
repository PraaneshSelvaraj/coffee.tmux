import os
from typing import Any

import yaml


class PluginLoader:
    def __init__(self, path: str) -> None:
        self.coffee_plugins_list_dir: str = path

    def load_plugins(self) -> list[dict[str, Any]]:
        plugins: list[dict[str, Any]] = []
        plugin_urls: set[str] = set()

        if not os.path.exists(self.coffee_plugins_list_dir):
            raise FileNotFoundError(
                f"Plugin directory not found: {self.coffee_plugins_list_dir}"
            )

        for filename in os.listdir(self.coffee_plugins_list_dir):
            if not filename.endswith((".yaml", ".yml")):
                continue

            file_path = os.path.join(self.coffee_plugins_list_dir, filename)

            with open(file_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}

            plugin = self._build_plugin_config(raw)

            if not self._is_valid_plugin(plugin):
                raise ValueError(f"Invalid plugin config in {file_path}")

            normalized_url = self._normalize_url(plugin["url"])

            if normalized_url in plugin_urls:
                raise ValueError(
                    f"Duplicate plugin URL detected for repository '{normalized_url}' (in {file_path})"
                )

            plugin_urls.add(normalized_url)
            plugin["url"] = normalized_url
            plugins.append(plugin)

        return plugins

    def _build_plugin_config(self, data: dict[str, Any]) -> dict[str, Any]:
        url = (data.get("url") or "").strip()

        name = (data.get("name") or "").strip()
        if not name and url:
            name = self._derive_name_from_url(url)

        return {
            "name": name,
            "url": url,
            "local": bool(data.get("local", False)),
            "source": data.get("source", []) or [],
            "tag": data.get("tag"),
            "skip_auto_update": bool(data.get("skip_auto_update", False)),
        }

    def _is_valid_plugin(self, plugin: dict[str, Any]) -> bool:
        url = plugin.get("url")

        return isinstance(url, str) and url.strip() != ""

    def _normalize_url(self, url: str) -> str:
        url = url.strip()

        if url.startswith("https://github.com/"):
            url = url[len("https://github.com/") :]

        if url.endswith(".git"):
            url = url.removesuffix(".git")

        return url.lower()

    def _derive_name_from_url(self, url: str) -> str:
        base = url.rstrip("/").split("/")[-1]
        return base.removesuffix(".git")

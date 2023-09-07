from __future__ import annotations

import importlib.metadata as metadata
import json
import os
import pathlib
import traceback

from .models.settings import GlobalSettings

from typing import TYPE_CHECKING, Any, Dict, List
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .models.click_commands import ClickGroup

#logger = structlog.get_logger()

class PluginManager(BaseModel):
    PLUGIN_DIR: pathlib.Path = pathlib.Path(os.path.expanduser("~/.aircmd"))

    plugins: Dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self.discover()

    def discover(self) -> None:
        self.plugins.clear()
        installed_plugins = self.get_installed_plugins()
        entry_points: metadata.EntryPoints | List[Any] = metadata.entry_points().get("aircmd.plugins", [])
        for entry_point in entry_points:
            plugin_name = entry_point.name
            if plugin_name not in installed_plugins:
                continue

            try:
                if isinstance(entry_point, metadata.EntryPoint):
                    plugin = entry_point.load()  # store the loaded plugin in a variable
            except Exception as e:
                print(f"Failed to load plugin {plugin_name}: {e}")
                print("Ensure that you are running aircmd in the root of your project and that your plugin is correctly configured")
                if GlobalSettings().DEBUG:
                    print(traceback.format_exc())
                else:
                    print("For detailed debugging information, run `AIRCMD_DEBUG=True aircmd`")
                continue

            self.plugins[plugin_name] = plugin  # store the loaded plugin instead of its name

    def refresh(self) -> None:
        self.discover()

    def get_installed_plugins(self) -> Any:
        self.PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
        plugin_file = self.PLUGIN_DIR / "plugins.json"
        if not plugin_file.is_file():
            with plugin_file.open("w") as f:
                json.dump([], f)
        with plugin_file.open("r") as f:
            content = f.read()
            if not content:
                return []
            return json.loads(content)

    def add_installed_plugin(self, plugin_name: str) -> None:
        installed_plugins = self.get_installed_plugins()
        installed_plugins.append(plugin_name)
        plugin_file = self.PLUGIN_DIR / "plugins.json"
        with plugin_file.open("w") as f:
            json.dump(installed_plugins, f)

    def remove_installed_plugin(self, plugin_name: str) -> None:
        installed_plugins = self.get_installed_plugins()
        if plugin_name in installed_plugins:
            installed_plugins.remove(plugin_name)
            plugin_file = self.PLUGIN_DIR / "plugins.json"
            with plugin_file.open("w") as f:
                json.dump(installed_plugins, f)
        else:
            print(f"Plugin {plugin_name} not found in installed plugins list.")

    def get_command_groups(self) -> List[ClickGroup]:  # change Group to ClickGroup
        command_groups = []
        for plugin_name, plugin in self.plugins.items():
            try:
                print(f"Plugin loaded: {plugin_name}")
                for group in plugin.groups.values():
                    command_groups.append(group)  
            except Exception as e:
                print(f"Failed to load plugin {plugin_name} with error: {e}")
                print("Ensure that you are running aircmd in the root of your project and that your plugin is correctly configured")
                if GlobalSettings().DEBUG:
                    print(traceback.format_exc())
                else:
                    print("For detailed debugging information, run `AIRCMD_DEBUG=True aircmd`")
        return command_groups

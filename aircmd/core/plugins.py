import os
import subprocess
import sys
import urllib
from typing import List, Optional

import requests

from ..models.base import GlobalContext
from ..models.click_commands import ClickCommandMetadata, ClickGroup
from ..models.click_params import ClickArgument, ClickOption
from ..models.click_utils import LazyPassDecorator
from ..models.settings import GlobalSettings

plugin_group = ClickGroup(group_name="plugin", group_help="Commands for managing plugins")

pass_global_context = LazyPassDecorator(GlobalContext, ensure=True)
pass_global_settings = LazyPassDecorator(GlobalSettings, ensure=True)


class ListCommand(ClickCommandMetadata):
    command_name: str = "list"
    command_help: str = "List installed plugins and search for available plugins"
    arguments: List[ClickArgument] = [ClickArgument(name="query", required=False)]

@plugin_group.command(ListCommand())
@pass_global_context
def list(ctx: GlobalContext, query: Optional[str] = None) -> None:
    """List installed plugins and search for available plugins"""
    plugin_index_url = "https://raw.githubusercontent.com/airbytehq/aircmd/main/plugin_index.json"
    installed_plugins = ctx.plugin_manager.plugins.values()
    print("Installed plugins:")
    for plugin in installed_plugins:
        print(f"{plugin.name}")

    response: requests.Response = requests.get(plugin_index_url)

    if response.status_code == 200:
        plugin_index = response.json()
        if query:
            plugin_index = [p for p in plugin_index if query.lower() in p["name"].lower()]

        print("\nAvailable plugins:")
        for plugin in plugin_index:
            if plugin in [p.name for p in installed_plugins]:
                status = "Installed" 
            else:
                status = "Available"
            print(plugin + f" ({status})")
                
    else:
        print("Failed to fetch the plugin index, showing only installed plugins.")


class InstallCommand(ClickCommandMetadata):
   command_name:str = "install"
   command_help: str = "Install a plugin. --local flag can be used to install from a local dir"
   arguments: List[ClickArgument] = [ClickArgument(name="name", required=True)]
   options: List[ClickOption] = [ClickOption(name="--local", required=False, help="Install from a local directory")]

@plugin_group.command(InstallCommand())
@pass_global_context
def install(ctx: GlobalContext, name: str, local: Optional[str]) -> None:
    """Install a plugin"""
    if not local:
        plugin_index_url = "https://raw.githubusercontent.com/airbytehq/aircmd/main/plugin_index.json"
        response: requests.Response = requests.get(plugin_index_url)
        if response.status_code == 200:
            plugin_index = response.json()
            matching_plugins = [p for p in plugin_index if p["name"] == name]
            if not matching_plugins:
                print(f"Plugin {name} not found in the plugin index.")
                return
            package_name = matching_plugins[0]["package_name"]
            repo_url = matching_plugins[0]["repo_url"]
        else:
            print("Failed to fetch the plugin index.")
            return
    else:
        package_name = local

    print(f"Installing plugin: {name}")
    try:
        if local:
            print(f"Installing from local directory: {local}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", package_name])
        else:
            if "github.com" in repo_url:
                if "github.com" in repo_url and "GITHUB_TOKEN" in os.environ:
                    url_parts = list(urllib.parse.urlsplit(repo_url))
                    url_parts[1] = f"{os.environ['GITHUB_TOKEN']}@{url_parts[1]}"
                    secure_repo_url = urllib.parse.urlunsplit(url_parts)
                    subprocess.check_call([sys.executable, "-m", "pip", "install", 'git+' + secure_repo_url])
                else:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", 'git+' + repo_url])
            else:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])

        print(f"Plugin {name} installed successfully.")
        ctx.plugin_manager.add_installed_plugin(name)
        ctx.plugin_manager.refresh()
    except subprocess.CalledProcessError as e:
        print(f"Failed to install plugin {name}: {e}")


class UninstallCommand(ClickCommandMetadata):
   command_name: str = "uninstall"
   command_help: str = "Uninstall a plugin"
   arguments: List[ClickArgument] = [ClickArgument(name='name', required=True)]

@plugin_group.command(UninstallCommand())
@pass_global_context
def uninstall(context: GlobalContext, name: str) -> None:
    """Uninstall a plugin"""
    try:
        print(f"Attempting to uninstall plugin: {name}")
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", name])
        if name in context.plugin_manager.get_installed_plugins():
            print(f"Plugin {name} uninstalled successfully.")
            context.plugin_manager.remove_installed_plugin(name)
            context.plugin_manager.refresh()
        else:
            print(f"Plugin {name} was not installed.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to uninstall plugin {name}: {e}")
        context.plugin_manager.refresh()


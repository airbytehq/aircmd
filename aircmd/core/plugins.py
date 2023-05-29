import subprocess
import sys
from typing import List, Optional

import requests
import structlog
from click import make_pass_decorator

from ..models import (ClickArgument, ClickCommandMetadata, ClickGroup,
                      ClickOption, GlobalContext)

plugin_group = ClickGroup(group_name="plugin")

logger = structlog.get_logger()

pass_global_context = make_pass_decorator(GlobalContext, ensure=True)


class ListCommand(ClickCommandMetadata):
    command_name: str = "list"
    command_help: str = "List installed plugins and search for available plugins"
    arguments: List[ClickArgument] = [ClickArgument(name="query", required=False)]

@plugin_group.command(ListCommand())
@pass_global_context
def list(ctx: GlobalContext, query: Optional[str] = None) -> None:
    """List installed plugins and search for available plugins"""
    plugin_index_url = "https://github.com/airbytehq/aircmd/plugin_index.json"
    installed_plugins = ctx.plugin_manager.plugins.keys()
    ("Installed plugins:")
    for plugin in installed_plugins:
        logger.info(f"  {plugin}")

    response = requests.get(plugin_index_url)

    if response.status_code == 200:
        plugin_index = response.json()
        if query:
            plugin_index = [p for p in plugin_index if query.lower() in p["name"].lower()]

        logger.info("\nAvailable plugins:")
        for plugin in plugin_index:
            status = "installed" if plugin["name"] in installed_plugins else "available"
            logger.info(f"  {plugin['name']} ({plugin['version']}): {plugin['description']} [{status}]")
    else:
        logger.warning("Failed to fetch the plugin index, showing only installed plugins.")


class InstallCommand(ClickCommandMetadata):
   command_name:str = "install"
   command_help: str = "Install a plugin. --local flag can be used to install from a local dir"
   arguments: List[ClickArgument] = [ClickArgument(name="name", required=True)]
   options: List[ClickOption] = [ClickOption(name="--local", required=False, help="Install from a local directory")]

@plugin_group.command(InstallCommand())
@pass_global_context
def install(ctx: GlobalContext, name: str, local: Optional[str]) -> None:
    """Install a plugin"""
    if not ctx.local:
        plugin_index_url = "https://raw.githubusercontent.com/airbytehq/aircmd/main/plugin_index.json"
        response = requests.get(plugin_index_url)
        if response.status_code == 200:
            plugin_index = response.json()
            matching_plugins = [p for p in plugin_index if p["name"] == name]
            if not matching_plugins:
                logger.error(f"Plugin {name} not found in the plugin index.")
                return
            package_name = matching_plugins[0]["package_name"]
            repo_url = matching_plugins[0]["repo_url"]
        else:
            logger.warning("Failed to fetch the plugin index.")
            return
    else:
        package_name = local

    logger.info(f"Installing plugin: {name}")
    try:
        if local:
            logger.info(f"Installing from local directory: {local}")
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

        logger.info(f"Plugin {name} installed successfully.")
        ctx.plugin_manager.add_installed_plugin(name)
        ctx.plugin_manager.refresh()
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install plugin {name}: {e}")


class UninstallCommand(ClickCommandMetadata):
   command_name: str = "uninstall"
   arguments: List[ClickArgument] = [ClickArgument(name='name', required=True)]

@plugin_group.command(UninstallCommand())
@pass_global_context
def uninstall(context: GlobalContext, name: str) -> None:
    """Uninstall a plugin"""
    try:
        logger.debug(f"Attempting to uninstall plugin: {name}")
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", name])
        if name in context.plugin_manager.get_installed_plugins():
            logger.info(f"Plugin {name} uninstalled successfully.")
            context.plugin_manager.remove_installed_plugin(name)
            context.plugin_manager.refresh()
        else:
            logger.warning(f"Plugin {name} was not installed.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to uninstall plugin {name}: {e}")
        context.plugin_manager.refresh()


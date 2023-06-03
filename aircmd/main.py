from __future__ import annotations

import sys

from dotenv import load_dotenv

from .core.artifact import core_group
from .core.plugins import plugin_group
from .models.base import GlobalContext
from .models.click_commands import ClickGroup
from .models.utils import make_pass_decorator

load_dotenv()


# Create a global context
gctx = GlobalContext()

# Create a Click context
global_context = make_pass_decorator(GlobalContext, ensure=True)

#logger = structlog.get_logger()
# create a decorator with click to pass the global context to commands

# Set up logging
# TODO: Make this more configurable
# Ideally we should have people able to configure this on 
# a per-plugin or per-method or per-command basis
# Running this method makes get_logger() return a structlog logger
#setup_default_logging()


def display_welcome_message() -> None:
    print('''
             █████╗ ██╗██████╗ ██████╗ ██╗   ██╗████████╗███████╗
            ██╔══██╗██║██╔══██╗██╔══██╗╚██╗ ██╔╝╚══██╔══╝██╔════╝
            ███████║██║██████╔╝██████╔╝ ╚████╔╝    ██║   █████╗  
            ██╔══██║██║██╔══██╗██╔══██╗  ╚██╔╝     ██║   ██╔══╝  
            ██║  ██║██║██║  ██║██████╔╝   ██║      ██║   ███████╗
            ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═════╝    ╚═╝      ╚═╝   ╚══════╝ 
        ''')

cli = ClickGroup(group_name=None, group_help="Aircmd: A CLI for Airbyte")

# Add core commands that live in `aircmd` itself (not plugins) to the top level entrypoint

cli.add_group(plugin_group) # commands to manage plugins
cli.add_group(core_group) # commands to manage building, testing, and publishing aircmd

def main() -> None:
    # only show the banner when running `aircmd` with no arguments
    if len(sys.argv) == 1:
        display_welcome_message()

    # Load plugin manager from the global context
    plugin_manager = gctx.plugin_manager

    # Get the command groups from the plugins
    plugin_command_groups = plugin_manager.get_command_groups()

    # Add each plugin command group to the top level cli
    for plugin_command_group in plugin_command_groups:
        cli.add_group(plugin_command_group)

    # Run the cli via its click entrypoint to parse arguments and delegate to the correct commands
    cli.click_group()


if __name__ == "__main__":
    main()




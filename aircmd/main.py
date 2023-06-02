from __future__ import annotations

import sys

import asyncclick as click

from .core.plugins import plugin_group
from .models.base import GlobalContext
from .models.utils import make_pass_decorator

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

# Here we leverage click directly to create the top level entrypoint
# and leverage click's argument parsing but otherwise we will use
# our custom pydantic models to define the commands and arguments
@click.group()
def cli() -> None:
    pass

# Add core commands that live in `aircmd` to the top level entrypoint
cli.add_command(plugin_group.click_group, name="plugin")

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
        cli.add_command(plugin_command_group.click_group)

    cli()
    #try:
        #await cli()
    #except Exception as e:
        #if str(e) != "0":
            #raise e



if __name__ == "__main__":
    main()




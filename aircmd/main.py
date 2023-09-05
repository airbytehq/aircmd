from __future__ import annotations

import sys
import traceback
import tracemalloc

import anyio
from asyncclick import Context
from dotenv import load_dotenv
from os import getenv

from .core.plugins import plugin_group
from .models.base import GlobalContext
from .models.click_commands import ClickGroup
from .models.click_utils import LazyPassDecorator

load_dotenv()

# Debug mode
AIRCMD_DEBUG: bool = bool(getenv("AIRCMD_DEBUG", False))

# Create a global context
gctx = GlobalContext(debug=AIRCMD_DEBUG)

# Create a Click context
global_context = LazyPassDecorator(GlobalContext, ensure=True)



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

cli.add_group(plugin_group)  # commands to manage plugins

def main() -> None:
    anyio.run(async_main)

async def async_main() -> None:
    try:
        
        # Store the current Click context in the GlobalContext object as a private attribute
        gctx.click_context = Context(cli.click_group)

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
        tracemalloc.start()

        await cli.click_group.main()
    except RuntimeWarning as e:                                                                                                                                                                                                                                                                               
         print(f"Caught a RuntimeWarning: {e}")                                                                                                                                                                                                                                                                
         traceback.print_exc()


if __name__ == "__main__":
    main()





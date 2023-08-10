from functools import wraps
from typing import Any, Callable, List, Type

from asyncclick import Argument, Command, Group, Option, Parameter

from .click_commands import TYPE_MAPPING, ClickCommand, ClickGroup
from .click_params import ClickArgument, ClickFlag, ClickOption, ClickParam


def add_parameter(params: List[Parameter], parameter_model: ClickParam) -> None:
    if isinstance(parameter_model, ClickArgument):
        click_argument = Argument([parameter_model.name], 
                               type=TYPE_MAPPING[parameter_model.type],
                                required=parameter_model.required)
    elif isinstance(parameter_model, ClickOption):
        # Add the shortcut only if it's not None
        opts = [parameter_model.name]
        if parameter_model.shortcut is not None:
            opts.append(parameter_model.shortcut)
        click_option = Option(opts,
                          type=TYPE_MAPPING[parameter_model.type], 
                          default=parameter_model.default,
                          help=parameter_model.help, 
                          required=parameter_model.required)
    elif isinstance(parameter_model, ClickFlag):
        click_flag = Option([parameter_model.name], 
                            type=bool, 
                            default=parameter_model.default,
                            is_flag=True, 
                            help=parameter_model.help)
    else:
        raise TypeError(f"Unsupported parameter type: {type(parameter_model)}")
    

    if isinstance(parameter_model, ClickArgument):
        params.append(click_argument)
    elif isinstance(parameter_model, ClickOption):
        params.append(click_option)
    elif isinstance(parameter_model, ClickFlag):
        params.append(click_flag)
    else:
        raise TypeError(f"Unsupported parameter type: {type(parameter_model)}")


def map_pyd_opt_to_click_option(option_model: ClickOption) -> Option:
    opts = [option_model.name]
    if option_model.shortcut is not None:
        opts.append(option_model.shortcut)
    click_option = Option(opts,
                          type=TYPE_MAPPING[option_model.type], 
                          default=option_model.default,
                          help=option_model.help, 
                          required=option_model.required)
    return click_option

def map_pyd_cmd_to_click_command(command_model: ClickCommand) -> Command:

    """Create a Click command for a command model and add it to a group."""
    params: List[Parameter] = []

    for parameter_model in command_model.arguments + command_model.options + command_model.flags:
        add_parameter(params, parameter_model)
    # Create the command
    return Command(name=command_model.command_name, params=params, callback=command_model.command_func,
                   help=command_model.command_help)


def map_pyd_grp_to_click_group(group_model: ClickGroup) -> Group:
    """Create Click commands for each command in a group."""
    # Create a Click group
    click_group = Group(name=group_model.group_name)
    # Add commands to the group
    for command_model in group_model.commands.values():
        click_command = map_pyd_cmd_to_click_command(command_model)
        click_group.add_command(click_command)

    for command_group in group_model.subgroups.values():
        click_command_group = map_pyd_grp_to_click_group(command_group)
        click_group.add_command(click_command_group)

    return click_group

class LazyPassDecorator:                                                                                                                                                                         
    def __init__(self, cls: Type[Any], *args: Any, **kwargs: Any) -> None:                                                                                                                       
        self.cls = cls                                                                                                                                                                           
        self.args = args                                                                                                                                                                         
        self.kwargs = kwargs                                                                                                                                                                     
                                                                                                                                                                                                
    def __call__(self, f: Callable[..., Any]) -> Callable[..., Any]:                                                                                                                             
        @wraps(f)                                                                                                                                                                                
        def decorated_function(*args: Any, **kwargs: Any) -> Any:                                                                                                                                
            # Check if the kwargs already contain the arguments being passed by the decorator
            decorator_kwargs = {k: v for k, v in self.kwargs.items() if k not in kwargs}
            # Create an instance of the class                                                                                                                                                    
            instance = self.cls(*self.args, **decorator_kwargs)                                                                                                                                       
            # Call the function with the instance as an argument                                                                                                                                 
            return f(instance, *args, **kwargs)                                                                                                                                                  
        return decorated_function



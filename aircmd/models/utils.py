from functools import wraps
from inspect import signature
from typing import Any, Callable, List, Optional

import pygit2
from asyncclick import Argument, Command, Group, Option, Parameter
from dagger import Container

from ..models.base import GlobalSettings, RunCondition
from ..models.click_commands import TYPE_MAPPING, ClickCommand, ClickGroup
from ..models.click_params import ClickArgument, ClickFlag, ClickOption, ClickParam


def onFail(id: Optional[str] = None) -> RunCondition:
    return RunCondition(condition_type="onFail", condition_value=id)

def onPass(id: Optional[str] = None) -> RunCondition:
    return RunCondition(condition_type="onPass", condition_value=id)

def onSkip(id: Optional[str] = None) -> RunCondition:
    return RunCondition(condition_type="onSkip", condition_value=id)



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

    return click_group



def make_pass_decorator(object_type: Any, ensure: bool=False) -> Callable[..., Any]:
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        sig = signature(f)
        params = sig.parameters
        # Check if function accepts object_type
        if any(True for param in params.values() if param.annotation is object_type):
            @wraps(f)
            def new_func(*args: tuple[Any], **kwargs:dict[str, Any]) -> Any:
                ctx = None
                # Find the context object among the arguments
                for arg in args:
                    if isinstance(arg, object_type):
                        ctx = arg
                        break

                if ctx is None:
                    if ensure:
                        ctx = object_type()
                    else:
                        raise RuntimeError(f"No object of type {object_type} found.")
                
                # If function has **kwargs, we can put the context there
                if params.get('kwargs', None) is not None and 'kwargs' not in kwargs:
                    kwargs['kwargs'] = ctx
                
                # Otherwise, add it to positional arguments
                else:
                    args = (*args, ctx)
                
                return f(*args, **kwargs)
            
            return new_func
        else:
            raise RuntimeError(f"Function {f.__name__} does not accept an argument of type {object_type}.")
    return decorator


def get_git_revision() -> str:
    repo = pygit2.Repository(".")
    commit_hash = repo.revparse_single("HEAD").short_id
    return commit_hash
'''
If both include and exclude are supplied, the load_settings function will first filter the environment variables based on the include list, and then it will    
further filter the resulting environment variables based on the exclude list.                                                                                   

Here's the order of operations:                                                                                                                                 

 1 If include is provided, only the environment variables with keys in the include list will be considered.                                                     
 2 If exclude is provided, any environment variables with keys in the exclude list will be removed from the filtered list obtained in step 1.                   
 3 The remaining environment variables will be loaded into the container.   
'''                                                                                                             
                                                                                                                                                                
def load_settings(settings: GlobalSettings, include: Optional[List[str]] = None, exclude: Optional[List[str]] = None) -> Callable[[Container], Container]:     
    def load_envs(ctr: Container) -> Container:                                                                                                                
        settings_dict = {key: value for key, value in settings.dict().items() if value is not None}                                                            
                                                                                                                                                            
        if include is not None:                                                                                                                                
            settings_dict = {key: settings_dict[key] for key in include if key in settings_dict}                                                               
                                                                                                                                                            
        if exclude is not None:                                                                                                                                
            settings_dict = {key: value for key, value in settings_dict.items() if key not in exclude}                                                         
                                                                                                                                                            
        for key, value in settings_dict.items():
            env_key = key.upper()
            ctr = ctr.with_env_variable(env_key, str(value))
                                                                                                                                                            
        return ctr                                                                                                                                             
                                                                                                                                                        
    return load_envs     











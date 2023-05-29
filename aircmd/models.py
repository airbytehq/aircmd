from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from inspect import signature
from typing import Any, Dict, List, Optional, Type

import click
import dagger
from click import ClickException, Command, Group
from dagger import Connection
from pydantic import BaseModel
from pydantic.main import ModelMetaclass

from .plugin_manager import PluginManager


class Singleton(ModelMetaclass):
    _instances:dict[Singleton, Any] = {}

    def __call__(cls: Singleton, *args: tuple[Any], **kwargs: dict[str, Any]) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class ParameterType(str, Enum):
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"

class ClickParam(BaseModel):
    name: str
    type: ParameterType = ParameterType.STRING
    default: Optional[str] = None
    required: bool = False
    help: Optional[str] = None

class ClickArgument(ClickParam):
    pass

class ClickOption(ClickParam):
    shortcut: Optional[str] = None

class ClickFlag(ClickParam):
    type: ParameterType = ParameterType.BOOL
    default: bool = False

class ClickCommandMetadata(BaseModel):
    command_name: str
    command_help: Optional[str] = None

class ClickCommand(ClickCommandMetadata):
    arguments: List[ClickArgument] = []
    options: List[ClickOption] = []
    flags: List[ClickFlag] = []
    command_func: Any = None  # The function that gets called when the command is invoked

    @property
    def click_command(self):
        if not hasattr(self, "_click_command"):
            self._click_command = map_pyd_cmd_to_click_command(self)
        return self._click_command

class ClickGroupMetadata(BaseModel):
    group_name: Optional[str] = None
    group_help: Optional[str] = None

class ClickGroup(ClickGroupMetadata):
    commands: Dict[str, ClickCommand] = {}
    subgroups: Dict[str, Type[ClickGroup]] = {}  # Added this line


    def command(self, command_metadata: ClickCommandMetadata):
        # Instantiate without arguments 
        # Click needs to know about the command before it is invoked
        # so we create a command instance that describes the command
        # including the name, but without the actual runtime arguments
        command_instance = ClickCommand(**command_metadata.model_dump())
        self.commands[command_instance.command_name] = command_instance  # Update commands dict immediately

        def decorator(func):
            # This is called when the command is actually invoked
            # We can now create a real command instance
            # and perform Pydantic validation on the arguments
            command_instance.command_func = func

            def wrapper(*args, **kwargs):
                try:
                    # Validate command instance against actual function arguments
                    command_instance = ClickCommand(**{**command_metadata.model_dump(), **kwargs})
                    self.commands[command_instance.command_name] = command_instance
                except ValidationError as err:
                    raise ClickException(str(err))  
            return wrapper
        
        return decorator

    @staticmethod
    def group(group_name: str):
        def decorator(func):
            group = ClickGroup(name=group_name)
            decorated_func = group(func)
            return decorated_func
        return decorator
    
    def add_group(self, subgroup: Type[ClickGroup]):  # Added this method
        if subgroup.group_name in self.subgroups:
            raise ValueError(f"A subgroup with the name '{subgroup.group_name}' already exists in this group.")
        self.subgroups[subgroup.group_name] = subgroup
    
    @property
    def click_group(self):
        click_group = Group(name=self.group_name)
        for command_model in self.commands.values():
            click_command = map_pyd_cmd_to_click_command(command_model)
            click_group.add_command(click_command)
        for subgroup in self.subgroups.values():  # Add this loop
            click_subgroup = map_pyd_grp_to_click_group(subgroup)
            click_group.add_command(click_subgroup)
        return click_group


def make_pass_decorator(object_type, ensure=False):
    def decorator(f):
        sig = signature(f)
        params = sig.parameters
        # Check if function accepts object_type
        if any(True for param in params.values() if param.annotation is object_type):
            @wraps(f)
            def new_func(*args, **kwargs):
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


@dataclass(frozen=True)
class GlobalContext(BaseModel, metaclass=Singleton):
    plugin_manager: PluginManager
    log_level: str # TODO: We should move this into a mutable LogContext
    debug: bool # if we want to allow configuration on a per-command basis
    local: bool = ("CI" not in os.environ)
    class Config:
        arbitrary_types_allowed = True

    # This syntax is needed over the dataclass syntax for setting the default value
    # because make_pass_decorator relies on the __init__ method
    # to supply default values for the context object
    # Otherwise, dataclass syntax is preferred
    def __init__(self, plugin_manager: Optional[PluginManager] = None, 
                 log_level: Optional[str] = None, debug = None, **data: Any):
        if plugin_manager is None:
            plugin_manager = PluginManager()
        if log_level is None:
            log_level = "WARNING"
        if debug is None:
            debug = False
        super().__init__(plugin_manager=plugin_manager, log_level=log_level, 
                         debug=debug, **data)
    #repo: str # TBD: Make this a repo object

@dataclass(frozen=True)
class PipelineContext(BaseModel, metaclass=Singleton):
    dagger_config: dagger.Config
    dagger_connection: Connection

    def __init__(self, config: Optional[dagger.Config] = None, **data: Any):
        if config is None:
            config = dagger.Config()
        super().__init__(config=config, **data)

    class Config:
        arbitrary_types_allowed = True


class Plugin(BaseModel, ABC):
    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True

    name: str
    groups: Dict[str, Type[ClickGroup]] = {}

    @abstractmethod
    def add_group(self, group: Type[ClickGroup]):
        if group.group_name in self.groups:
            raise ValueError(f"A group with the name '{group.group_name}' already exists in this plugin.")
        self.groups[group.group_name] = group

    @abstractmethod
    def get_group(self, name: str) -> Type[ClickGroup]:
        return self.groups.get(name, None)

class DeveloperPlugin(Plugin, ABC):
    class Config:
        populate_by_name = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_group(self, group: Type[ClickGroup]):
        super().add_group(group)

    def get_group(self, name: str) -> Type[ClickGroup]:
        return super().get_group(name)


class ApplicationPlugin(DeveloperPlugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validate_commands()

    def validate_commands(self):
        required_commands = ['deploy', 'up']
        for command in required_commands:
            if command not in self.commands:
                raise ValueError(f"ApplicationPlugin must have a command named '{command}'")


class OperatorPlugin(Plugin, ABC):
    # todo: stub this out a bit more once we know more
    # about how an operator plugin should be structured
    pass
    
class Pipeline(BaseModel):
    # todo: stub this out after chatting with Augustin and Ben
    pipeline_context: PipelineContext
    global_context: GlobalContext

    pipelines: list[Pipeline] = []
    pass




TYPE_MAPPING: Dict[str, Any] = {
    "int": int,
    "float": float,
    "bool": bool,
    "string": str,
}


def add_parameter(params, parameter_model):
    if isinstance(parameter_model, ClickArgument):
        click_param = click.Argument([parameter_model.name], type=TYPE_MAPPING[parameter_model.type],
                                     required=parameter_model.required)
    elif isinstance(parameter_model, ClickOption):
        # Add the shortcut only if it's not None
        opts = [parameter_model.name]
        if parameter_model.shortcut is not None:
            opts.append(parameter_model.shortcut)
        click_param = click.Option(opts,
                                   type=TYPE_MAPPING[parameter_model.type], default=parameter_model.default,
                                   help=parameter_model.help, required=parameter_model.required)
    elif isinstance(parameter_model, ClickFlag):
        click_param = click.Option([parameter_model.name], type=bool, default=parameter_model.default,
                                   is_flag=True, help=parameter_model.help)
    else:
        raise TypeError(f"Unsupported parameter type: {type(parameter_model)}")
    

    params.append(click_param)


def map_pyd_cmd_to_click_command(command_model: ClickCommand) -> Command:
    """Create a Click command for a command model and add it to a group."""
    params = []

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




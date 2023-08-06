from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from asyncclick import ClickException, Command, Group
from pydantic import BaseModel, ValidationError

from .click_params import ClickArgument, ClickFlag, ClickOption

__all__ = ["ClickArgument", "ClickCommandMetadata", "ClickCommand", "ClickGroupMetadata", "ClickGroup"]

if TYPE_CHECKING:
    from .click_utils import map_pyd_cmd_to_click_command

TYPE_MAPPING: Dict[str, Any] = {
    "int": int,
    "float": float,
    "bool": bool,
    "string": str,
}

class ClickCommandMetadata(BaseModel):
    command_name: str
    command_help: str

    #@field_validator('command_name')
    def validate_command_name(cls, v: str) -> str:
        if not v or not v.islower() or not v.isalnum() or len(v) > 20:
            raise ValueError("Command name must be all lowercase, contain no special characters, and not exceed 20 characters in length.")
        return v

    #@field_validator('command_help')
    def validate_command_help(cls, v: str) -> str:
        if not v or len(v) > 100:
            raise ValueError("Command help cannot be empty and must not exceed 100 characters in length.")
        if not v[0].isupper() or v[-1] == '.':
            raise ValueError("Command help must be a sentence that begins with a capital letter and does not end in a period.")
        return v 

class ClickCommand(ClickCommandMetadata):
    arguments: List[ClickArgument] = []
    options: List[ClickOption] = []
    flags: List[ClickFlag] = []
    command_func: Any = None
    # The function that gets called when the command is invoked
    # Note that typing this created issues so we leave it Any for now

    @property
    def click_command(self) -> Command:
        if not hasattr(self, "_click_command"):
            self._click_command = map_pyd_cmd_to_click_command(self)
        return self._click_command

class ClickGroupMetadata(BaseModel):
    group_name: Optional[str] = None
    group_help: str

    #@field_validator('group_name')
    def validate_group_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v == "":
            raise ValueError("Group name cannot be empty string when it's not None.")
        if v and not v.islower():
            raise ValueError("Group name must be all lowercase")
        if v and not v.isalnum():
            raise ValueError("Group name must contain no special characters")
        if v and len(v) > 20:
            raise ValueError("Group name must not exceed 20 characters in length")
        return v

    #@field_validator('group_help')
    def validate_group_help(cls, v: str) -> str:
        if len(v) > 100:
            raise ValueError("Group help must not exceed 100 characters in length.")
        if not v or v == "":
            raise ValueError("Group help cannot be empty.")
        if not v[0].isupper() or v[-1] == '.':
            raise ValueError("Group help must be a sentence that begins with a capital letter and does not end in a period.")
        return v

class ClickGroup(ClickGroupMetadata):
    commands: Dict[str, ClickCommand] = {}
    subgroups: Dict[str, 'ClickGroup'] = {}
    options: List[ClickOption] = []

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self.group_name = data.get("group_name") or None
        self.group_help = data.get("group_help", "")
        self.commands = data.get("commands", {})
        self.subgroups = data.get("subgroups", {})

    def command(self, command_metadata: ClickCommandMetadata) -> Callable[..., Any]:
        # Instantiate without arguments 
        # Click needs to know about the command before it is invoked
        # so we create a command instance that describes the command
        # including the name, but without the actual runtime arguments
        command_instance = ClickCommand(**command_metadata.dict())
        self.commands[command_instance.command_name] = command_instance  # Update commands dict immediately

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            # This is called when the command is actually invoked
            # We can now create a real command instance
            # and perform Pydantic validation on the arguments
            command_instance.command_func = func
            def wrapper(*args: tuple[Any], **kwargs: dict[str, Any]) -> Any:
                # Remove the global option from kwargs before validation
                kwargs.pop("global_option", None)
                try:
                    # Validate command instance against actual function arguments
                    command_instance = ClickCommand(**{**command_metadata.dict(), **kwargs})
                    self.commands[command_instance.command_name] = command_instance
                except ValidationError as err:
                    raise ClickException(str(err))
                # handle the case where we invoke the command from python, not through click
                if command_instance.command_func is None:                                                                                                                                                                                                                                                                                                                                                                             
                    command_instance.command_func = func                                                                                                                                                                                                                                                                                                                                                                             
                return command_instance.command_func(*args, **kwargs)  

            return wrapper
        return decorator

    
    @staticmethod
    def group(group_name: str, group_help: str) -> Callable[..., Any]:
        def decorator(func: Callable[..., Any]) -> ClickGroup:
            group = ClickGroup(group_name=group_name, group_help=group_help)
            return group
        return decorator
    
    def add_group(self, subgroup: 'ClickGroup') -> 'ClickGroup':
        if not subgroup.group_name:
            raise ValueError("Subgroup name cannot be empty or None.")
        if subgroup.group_name in self.subgroups:
            raise ValueError(f"A subgroup with the name '{subgroup.group_name}' already exists in this group.")
        self.subgroups[subgroup.group_name] = subgroup
        return self
    
    @property
    def click_group(self) -> Group:
        from .click_utils import (
            map_pyd_cmd_to_click_command,
            map_pyd_grp_to_click_group,
            map_pyd_opt_to_click_option,
        )
        click_group = Group(name=self.group_name)
        for command_model in self.commands.values():
            click_command = map_pyd_cmd_to_click_command(command_model)
            click_group.add_command(click_command)
        for subgroup in self.subgroups.values():
            click_subgroup = map_pyd_grp_to_click_group(subgroup)
            click_group.add_command(click_subgroup)
        for option in self.options:
            click_option = map_pyd_opt_to_click_option(option)
            click_group.params.append(click_option)
        return click_group




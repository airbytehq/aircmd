from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from asyncclick import ClickException, Command, Group
from pydantic import BaseModel, ValidationError

from .click_params import ClickArgument, ClickFlag, ClickOption

if TYPE_CHECKING:
    from .utils import map_pyd_cmd_to_click_command

TYPE_MAPPING: Dict[str, Any] = {
    "int": int,
    "float": float,
    "bool": bool,
    "string": str,
}


class ClickCommandMetadata(BaseModel):
    command_name: str
    command_help: str

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

class ClickGroup(ClickGroupMetadata):
    commands: Dict[str, ClickCommand] = {}
    subgroups: Dict[str, 'ClickGroup'] = {} 

    def command(self, command_metadata: ClickCommandMetadata) -> Callable[..., Any]:
        # Instantiate without arguments 
        # Click needs to know about the command before it is invoked
        # so we create a command instance that describes the command
        # including the name, but without the actual runtime arguments
        command_instance = ClickCommand(**command_metadata.model_dump())
        self.commands[command_instance.command_name] = command_instance  # Update commands dict immediately

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            # This is called when the command is actually invoked
            # We can now create a real command instance
            # and perform Pydantic validation on the arguments
            command_instance.command_func = func

            def wrapper(*args: tuple[Any], **kwargs: dict[str, Any]) -> None:
                try:
                    # Validate command instance against actual function arguments
                    command_instance = ClickCommand(**{**command_metadata.model_dump(), **kwargs})
                    self.commands[command_instance.command_name] = command_instance
                except ValidationError as err:
                    raise ClickException(str(err))  
        
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
        from .utils import map_pyd_cmd_to_click_command, map_pyd_grp_to_click_group
        click_group = Group(name=self.group_name)
        for command_model in self.commands.values():
            click_command = map_pyd_cmd_to_click_command(command_model)
            click_group.add_command(click_command)
        for subgroup in self.subgroups.values():  # Add this loop
            click_subgroup = map_pyd_grp_to_click_group(subgroup)
            click_group.add_command(click_subgroup)
        return click_group



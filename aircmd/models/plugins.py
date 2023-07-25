import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from .click_commands import ClickGroup


class Plugin(BaseModel, ABC):
    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True

    name: str
    base_dirs: List[str]
    groups: Dict[Optional[str], ClickGroup] = {}

    @abstractmethod
    def add_group(self, group: ClickGroup) -> None:
        if group.group_name in self.groups:
            raise ValueError(f"A group with the name '{group.group_name}' already exists in this plugin.")
        self.groups[group.group_name] = group


class DeveloperPlugin(Plugin, ABC):
    class Config:
        populate_by_name = True
    
    def __init__(self, *args:tuple[Any], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def add_group(self, group: ClickGroup) -> None:
        super().add_group(group)

    def get_relative_path(self) -> str:
        for base_dir in self.base_dirs:
            if os.getcwd().endswith(base_dir):
                return os.getcwd()[len(base_dir):]
        return ''

class ApplicationPlugin(DeveloperPlugin):

    def __init__(self, *args: tuple[Any], **kwargs: Dict[str, Any]) -> None:
        super().__init__(*args, **kwargs)




class OperatorPlugin(Plugin, ABC):
    # todo: stub this out a bit more once we know more
    # about how an operator plugin should be structured
    pass
    
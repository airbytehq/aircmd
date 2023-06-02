from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ParameterType(str, Enum):
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"

class ClickParam(BaseModel):
    name: str
    type: ParameterType = ParameterType.STRING
    default: Optional[bool] = None
    required: bool = False
    help: Optional[str] = None

class ClickArgument(ClickParam):
    pass

class ClickOption(ClickParam):
    shortcut: Optional[str] = None

class ClickFlag(ClickParam):
    type: ParameterType = ParameterType.BOOL
    default: bool = False  

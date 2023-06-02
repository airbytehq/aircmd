import sys
from typing import Any, Optional

import dagger
from pydantic import BaseModel, Field
from pydantic.main import ModelMetaclass
from pydantic_settings import BaseSettings

from ..plugin_manager import PluginManager


class Singleton(ModelMetaclass):
    _instances: dict['Singleton', Any] = {}

    def __call__(cls: 'Singleton',
                  *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

    
class GlobalSettings(BaseSettings):
    GITHUB_TOKEN: Optional[str] = Field(None, env="GITHUB_TOKEN")
    CI: bool = Field(False, env="CI")
    LOG_LEVEL: str = Field("WARNING", env="LOG_LEVEL")

class PipelineContext(BaseModel, metaclass=Singleton):
    dagger_config: dagger.Config
    dagger_connection: dagger.Connection

    def __init__(self, config: Optional[dagger.Config] = None,  
                 connection: Optional[dagger.Connection] = None, 
                 **data: Any):
        if config is None:
            config = dagger.Config(log_output=sys.stdout)
        if connection is None:
            # Replace with your logic to create a Connection instance
            connection = dagger.Connection(config = config)
        super().__init__(dagger_config=config, dagger_connection=connection, **data)

    class Config:
        arbitrary_types_allowed = True

class GlobalContext(BaseModel, metaclass=Singleton):
    plugin_manager: PluginManager
    pipeline_context: Optional[PipelineContext] = None
    class Config:
        arbitrary_types_allowed = True

    # This syntax is needed over the dataclass syntax for setting the default value
    # because make_pass_decorator relies on the __init__ method
    # to supply default values for the context object
    # Otherwise, dataclass syntax is preferred
    def __init__(self, plugin_manager: Optional[PluginManager] = None, **data: Any):
        if plugin_manager is None:
            plugin_manager = PluginManager()
        super().__init__(plugin_manager=plugin_manager, **data)

import os
import platform
import subprocess
import sys
from typing import Any, Optional, Type

import dagger
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from ..plugin_manager import PluginManager


class Singleton:
    _instances: dict[Type['Singleton'], Any] = {}

    def __new__(cls: Type['Singleton'], *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super().__new__(cls)
        return cls._instances[cls]

    
# Immutable. Use this for application configuration. Created at bootstrap.


class GlobalSettings(BaseSettings):
    GITHUB_TOKEN: Optional[str] = Field(None, env="GITHUB_TOKEN")
    CI: bool = Field(False, env="CI")
    LOG_LEVEL: str = Field("WARNING", env="LOG_LEVEL")
    PLATFORM: str = platform.system()
    POETRY_CACHE_DIR: str = Field(
        default_factory=lambda: (
            f"{os.path.expanduser('~')}/Library/Caches/pypoetry" if platform.system() == "Darwin"
            else f"{os.path.expanduser('~')}/AppData/Local/pypoetry/Cache" if platform.system() == "Windows"
            else f"{os.path.expanduser('~')}/.cache/pypoetry"
        ),
        env="POETRY_CACHE_DIR"
    )
    PIP_CACHE_DIR: str = Field(                                                                                                                                          
         default_factory=lambda: (                                                                                                                                        
             f"{os.path.expanduser('~')}/Library/Caches/pip" if platform.system() == "Darwin"                                                                             
             else f"{os.path.expanduser('~')}/AppData/Local/pip/Cache" if platform.system() == "Windows"                                                                  
             else f"{os.path.expanduser('~')}/.cache/pip"                                                                                                                 
         ),                                                                                                                                                               
         env="PIP_CACHE_DIR"                                                                                                                                              
     ) 
    # Add new secrets as fields
    SECRET_1: str = Field(..., env="SECRET_1")
    SECRET_2: str = Field(..., env="SECRET_2")

    class Config:                                                                                                                                                        
         arbitrary_types_allowed = True                                                                                                                                   
         env_file = '.env' 

    @classmethod
    def load_secrets_from_file(cls, secrets_file: str) -> None:
        """Decrypt the secrets file using SOPS and load it into environment variables."""
        try:
            decrypted_secrets = subprocess.check_output(["sops", "-d", secrets_file])
            with open(".env", "wb") as f:
                f.write(decrypted_secrets)
            load_dotenv(".env")
            os.remove(".env")
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Error decrypting secrets file: {e}")
        except FileNotFoundError:
            raise ValueError("SOPS command not found. Please install SOPS to use this feature.")

# Mutable. Store pipeline state here. Created at runtime
class PipelineContext(BaseModel, Singleton):
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

# Mutaable. Store global application state here. Created at runtime
class GlobalContext(BaseModel,Singleton):
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
        super().__init__(plugin_manager=plugin_manager, **data)

import platform
import sys
from typing import Any, Callable, List, Optional, Type, Union

import dagger
import platformdirs
from asyncclick import Context, get_current_context
from pydantic import BaseModel, BaseSettings, Field, PrivateAttr

from ..plugin_manager import PluginManager


class Singleton:
    _instances: dict[Type['Singleton'], Any] = {}

    def __new__(cls: Type['Singleton'], *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super().__new__(cls)
        return cls._instances[cls]

    
# Immutable. Use this for application configuration. Created at bootstrap.
class GlobalSettings(BaseSettings, Singleton):
    GITHUB_TOKEN: Optional[str] = Field(None, env="GITHUB_TOKEN")
    CI: bool = Field(False, env="CI")
    LOG_LEVEL: str = Field("WARNING", env="LOG_LEVEL")
    PLATFORM: str = platform.system()
    POETRY_CACHE_DIR: str = Field(
        default_factory=lambda: platformdirs.user_cache_dir("pypoetry"),
        env="POETRY_CACHE_DIR"
    )
    MYPY_CACHE_DIR: str = Field("~/.cache/.mypy_cache", env="MYPY_CACHE_DIR")
    DEFAULT_PYTHON_EXCLUDE: List[str] = Field(["**/.venv", "**/__pycache__"], env="DEFAULT_PYTHON_EXCLUDE")
    DEFAULT_EXCLUDED_FILES: List[str] = Field(
        [
            ".git",
            "**/build",
            "**/.venv",
            "**/secrets",
            "**/__pycache__",
            "**/*.egg-info",
            "**/.vscode",
            "**/.pytest_cache",
            "**/.eggs",
            "**/.mypy_cache",
            "**/.DS_Store",
        ],
        env="DEFAULT_EXCLUDED_FILES"
    )
    DOCKER_VERSION:str = Field("20.10.23", env="DOCKER_VERSION")
    DOCKER_DIND_IMAGE: str = Field("docker:20-dind", env="DOCKER_DIND_IMAGE")
    DOCKER_CLI_IMAGE: str = Field("docker:20-cli", env="DOCKER_CLI_IMAGE")
    GRADLE_CACHE_PATH: str = Field("/root/.gradle/caches", env="GRADLE_CACHE_PATH")
    GRADLE_BUILD_CACHE_PATH: str = Field(f"{GRADLE_CACHE_PATH}/build-cache-1", env="GRADLE_BUILD_CACHE_PATH")
    GRADLE_READ_ONLY_DEPENDENCY_CACHE_PATH: str = Field("/root/gradle_dependency_cache", env="GRADLE_READ_ONLY_DEPENDENCY_CACHE_PATH")

    SECRET_DOCKER_HUB_USERNAME: Optional[str] = Field(None, env="SECRET_DOCKER_HUB_USERNAME")
    SECRET_DOCKER_HUB_PASSWORD: Optional[str] = Field(None, env="SECRET_DOCKER_HUB_PASSWORD")
    
    PIP_CACHE_DIR: str = Field(
        default_factory=lambda: platformdirs.user_cache_dir("pip"),
        env="PIP_CACHE_DIR"
    )

    class Config:                                                                                                                                                        
         arbitrary_types_allowed = True                                                                                                                                   
         env_file = '.env' 


class PipelineResult(BaseModel):
    id: Optional[str] = None
    status: str
    data: Any
    class Config:
        arbitrary_types_allowed=True

class Pipeline(BaseModel):
    name: str
    steps: List[Union['Pipeline', Callable[..., Any], List[Union['Pipeline', Callable[..., Any],]]]]
    client: dagger.Client

    def __init__(self, name: str, steps: Optional[List[Union['Pipeline', Callable[..., Any], List[Union['Pipeline', Callable[..., Any],]]]]] = None, **data: Any):
        if steps is None:
            steps = []
        super().__init__(name=name, steps=steps, **data)
    class Config:
        arbitrary_types_allowed=True


# this is a bit of a hack to get around how prefect resolves parameters
# basically without this, prefect will attempt to access the context
# before we create it in main.py in order to resolve it as a parameter
# wrapping it in a function like this prevents that from happening
def get_context():                                                                                                                                       
    return get_current_context()   

class PipelineContext(BaseModel, Singleton):
    dockerd_service: Optional[dagger.Container] = Field(default=None)
    _dagger_client: Optional[dagger.Client] = PrivateAttr(default=None)
    _click_context: Callable[[], Context] = PrivateAttr(default_factory=lambda: get_context)                                                                                                                                                                                                                                                                                                                  
                                                                                                                                                                                                                                                                        
    class Config:
        arbitrary_types_allowed=True

    
    def get_dagger_client(self) -> dagger.Client:
        if not self._dagger_client:
            connection = dagger.Connection(dagger.Config(log_output=sys.stdout))
            self._dagger_client = self._click_context().with_resource(connection)  # type: ignore
        return self._dagger_client  # type: ignore

class GlobalContext(BaseModel, Singleton):
    plugin_manager: PluginManager
    pipeline_context: Optional[PipelineContext] = Field(default=None)
    click_context: Optional[Context] = Field(default=None)

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, plugin_manager: Optional[PluginManager] = None, _click_context: Optional[Context] = None, **data: Any):
        if plugin_manager is None:
            plugin_manager = PluginManager()
        super().__init__(plugin_manager=plugin_manager, _click_context=_click_context, **data)

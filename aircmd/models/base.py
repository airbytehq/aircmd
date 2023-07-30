import asyncio
import platform
import sys
from typing import Any, Callable, List, Optional, Type, Union

import dagger
import platformdirs
from asyncclick import Context, get_current_context
from dagger.api.gen import Client, Container
from prefect.context import (
    FlowRunContext,
    SettingsContext,
    TagsContext,
    TaskRunContext,
    get_settings_context,
    tags,
)
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
    GRADLE_CACHE_PATH: str = Field("/root/.gradle", env="GRADLE_CACHE_PATH")
    GRADLE_BUILD_CACHE_PATH: str = Field(f"{GRADLE_CACHE_PATH}/build-cache-1", env="GRADLE_BUILD_CACHE_PATH")
    GRADLE_READ_ONLY_DEPENDENCY_CACHE_PATH: str = Field("/root/gradle_dependency_cache", env="GRADLE_READ_ONLY_DEPENDENCY_CACHE_PATH")

    PREFECT_API_URL: str = Field("http://127.0.0.1:4200/api", env="PREFECT_API_URL")
    PREFECT_COMMA_DELIMITED_USER_TAGS: str = Field("", env="PREFECT_COMMA_DELIMITED_USER_TAGS")
    PREFECT_COMMA_DELIMITED_SYSTEM_TAGS: str = Field("CI:False", env="PREFECT_COMMA_DELIMITED_SYSTEM_TAGS")

    SECRET_DOCKER_HUB_USERNAME: Optional[str] = Field(None, env="SECRET_DOCKER_HUB_USERNAME")
    SECRET_DOCKER_HUB_PASSWORD: Optional[str] = Field(None, env="SECRET_DOCKER_HUB_PASSWORD")
    
    PIP_CACHE_DIR: str = Field(
        default_factory=lambda: platformdirs.user_cache_dir("pip"),
        env="PIP_CACHE_DIR"
    )

    class Config:                                                                                                                                                        
         arbitrary_types_allowed = True                                                                                                                                   
         env_file = '.env' 

# this is a bit of a hack to get around how prefect resolves parameters
# basically without this, prefect will attempt to access the context
# before we create it in main.py in order to resolve it as a parameter
# wrapping it in a function like this prevents that from happening
def get_context():                                                                                                                                       
    return get_current_context()   

class PipelineContext(BaseModel, Singleton):
    dockerd_service: Optional[Container] = Field(default=None)
    _dagger_client: Optional[Client] = PrivateAttr(default=None)
    _click_context: Callable[[], Context] = PrivateAttr(default_factory=lambda: get_context)
    _main_event_loop: asyncio.AbstractEventLoop = PrivateAttr(default_factory=asyncio.get_event_loop)

    class Config:
        arbitrary_types_allowed=True

    def __init__(self, **data):
        super().__init__(**data)
        self.set_global_prefect_tag_context()
    
    async def get_dagger_client(self, client: Optional[Client] = None, pipeline_name: Optional[str] = None) -> Client:
        if not self._dagger_client:
            connection = dagger.Connection(dagger.Config(log_output=sys.stdout))
            self._dagger_client = await self._click_context().with_async_resource(connection)  # Added 'await' here
        client = self._dagger_client
        assert client, "Error initializing Dagger client"
        return client.pipeline(pipeline_name) if pipeline_name else client
    
    def set_global_prefect_tag_context(self) -> Optional[TagsContext]:
        if not TagsContext.get().current_tags:
            system_tags = GlobalSettings().PREFECT_COMMA_DELIMITED_SYSTEM_TAGS.split(",")
            user_tags = GlobalSettings().PREFECT_COMMA_DELIMITED_USER_TAGS.split(",")
            all_tags = system_tags + user_tags
            self._click_context().with_resource(tags(*all_tags))  # type: ignore
        return None  # type: ignore
    
    @property
    def prefect_tags_context(self) -> TagsContext:
        return TagsContext.get()

    @property
    def prefect_settings_context(self) -> SettingsContext:
        return get_settings_context()

    @property
    def prefect_flow_run_context(self) -> FlowRunContext:
        flow_run_context = FlowRunContext.get()
        if flow_run_context is None:
            raise ValueError("FlowRunContext is not available.")
        return flow_run_context

    @property
    def prefect_task_run_context(self) -> Union[TaskRunContext, None]:
        task_run_context = TaskRunContext.get()
        if task_run_context is None:
            raise ValueError("TaskRunContext is not available.")
        return task_run_context


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

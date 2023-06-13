import logging
import platform
import sys
from typing import Any, Coroutine, List, Optional, Type

import anyio
import dagger
import platformdirs
from asyncclick import Context, get_current_context
from pydantic import BaseModel, Field, PrivateAttr
from pydantic_settings import BaseSettings

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


'''
In the case of modeling CI pipelines, the child-knows-parent approach seems more suitable for the 
following reasons:                                                                                

 1 Analyzing individual pipeline runs: When you want to analyze a specific pipeline run, you might
   need to compare it with its parent or ancestor runs to understand the differences or           
   improvements. In this case, having a reference to the parent pipeline makes it easier to       
   traverse up the pipeline hierarchy.                                                            
 2 Dependency tracking: In some CI systems, a pipeline run might depend on the successful         
   completion of its parent or ancestor runs. With the child-knows-parent approach, you can easily
   check the status of the parent pipelines and determine if the current pipeline run should      
   proceed or not.                                                                                
 3 Debugging and troubleshooting: When a pipeline run fails, you might need to investigate the    
   cause of the failure by looking at the parent or ancestor runs. The child-knows-parent approach
   allows you to easily navigate up the pipeline hierarchy to find the relevant information.      

While it's true that some use cases might require traversing the pipeline hierarchy from the root 
to the leaves, these cases are less common in CI systems. The child-knows-parent approach provides
more flexibility and ease of use for the typical operations performed on CI pipelines.        

'''
class Pipeline(BaseModel):
    name: str
    parent_pipeline: Optional['Pipeline']
    dagger_client: dagger.Client

    class Config:
        arbitrary_types_allowed=True

    @classmethod
    async def create(cls, name: str, parent_pipeline: Optional['Pipeline'] = None) -> 'Pipeline':
        if parent_pipeline is None:
            # This is a top-level pipeline. Get the Dagger client from the current PipelineContext.
            dagger_client = await PipelineContext().get_dagger_client()
        else:
            # This is a nested pipeline. Get the Dagger client from the parent pipeline.
            dagger_client = parent_pipeline.dagger_client

        # Create the pipeline using the appropriate Dagger client.
       
        dagger_client = dagger_client.pipeline(name)
        return cls(name=name, parent_pipeline=parent_pipeline, dagger_client=dagger_client)


class PipelineContext(BaseModel, Singleton):
    _current_level: int = 0
    logger: logging.Logger
    current_running_tasks: int = 0
    max_concurrency: int = 0
    max_concurrency_per_level: dict[int, int] = Field(default_factory=dict)
    concurrency_lock: anyio.Lock = anyio.Lock()
    _dagger_client: Optional[dagger.Client] = PrivateAttr(default=None)
    _click_context: Context = PrivateAttr(default_factory=get_current_context)


    class Config:
        arbitrary_types_allowed=True

    
    async def get_dagger_client(self) -> dagger.Client:
        if not self._dagger_client:
            connection = dagger.Connection(dagger.Config(log_output=sys.stdout))
            self._dagger_client = await self._click_context.with_async_resource(connection)  # type: ignore
        return self._dagger_client  # type: ignore


    async def update_concurrency(self, delta: int, level: int) -> None:
        async with self.concurrency_lock:
            self.current_running_tasks += delta
            current_level_concurrency = self.max_concurrency_per_level.get(level, 0) + delta
            self.max_concurrency_per_level[level] = max(self.max_concurrency_per_level.get(level, 0), current_level_concurrency)
            self.max_concurrency = max(self.max_concurrency_per_level.values())


    async def run_pipelines(self, pipelines: List[Coroutine[Any, Any, Any]], concurrency: int) -> None:
        semaphore = anyio.Semaphore(concurrency)

        async def run_pipeline_with_semaphore(pipeline: Coroutine[Any, Any, Any]) -> None:
            async with semaphore:
                await self.update_concurrency(1, self._current_level)
                await pipeline
                await self.update_concurrency(-1, self._current_level)


        self._current_level += 1
        async with anyio.create_task_group() as tg:
            for pipeline in pipelines:
                tg.start_soon(run_pipeline_with_semaphore, pipeline)
        self._current_level -= 1
        print("All tasks completed")
        print(f"Maximum concurrency observed: {self.max_concurrency}")

    def __init__(self, **data: Any):
        logger = logging.getLogger("PipelineContext")
        super().__init__(logger=logger, **data)

# Mutaable. Store global application state here. Created at runtime

class GlobalContext(BaseModel, Singleton):
    plugin_manager: PluginManager
    pipeline_context: Optional[PipelineContext] = None
    _click_context: Optional[Context] = None

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



# Remove the pipeline decorator

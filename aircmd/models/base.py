import platform
import sys
from typing import Any, Callable, Dict, List, Optional, Type, Union

import anyio
import dagger
import platformdirs
from asyncclick import Context, get_current_context
from pydantic import BaseModel, Field, PrivateAttr
from pydantic_settings import BaseSettings

from ..plugin_manager import PluginManager
from .utils import RunCondition


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
    data: dagger.Container

    class Config:
        arbitrary_types_allowed=True

class Pipeline(BaseModel):
    name: str
    steps: List[Union['Pipeline', Callable[..., Any], 'ConditionalPipeline', List[Union['Pipeline', Callable[..., Any], 'ConditionalPipeline']]]]
    client: dagger.Client

    def __init__(self, name: str, steps: Optional[List[Union['Pipeline', Callable[..., Any], 'ConditionalPipeline', List[Union['Pipeline', Callable[..., Any], 'ConditionalPipeline']]]]] = None, **data: Any):
        if steps is None:
            steps = []
        super().__init__(name=name, steps=steps, **data)
    class Config:
        arbitrary_types_allowed=True



class ConditionalPipeline(Pipeline):                                                                                                                                                                                                                                                                              
    run_condition: RunCondition    

class PipelineContext(BaseModel, Singleton):
    _current_level: int = 0
    current_running_tasks: int = 0
    max_concurrency: int = 0
    max_concurrency_per_level: dict[int, int] = Field(default_factory=dict)
    concurrency_lock: anyio.Lock = anyio.Lock()
    dockerd_service: Optional[dagger.Container] = Field(default=None)
    _dagger_client: Optional[dagger.Client] = PrivateAttr(default=None)
    _click_context: Context = PrivateAttr(default_factory=get_current_context)

    async def execute_pipeline(self, pipeline: Pipeline, results: Optional[Dict[str, PipelineResult]] = None) -> None:                                                                                                                                                                                                                                                                           
     if results is None:                                                                                                                                                                                                                                                                                                                                                                      
         results = {}                                                                                                                                                                                                                                                                                                                                                                         
                                                                                                                                                                                                                                                                                                                                                                                              
     for index, step in enumerate(pipeline.steps):                                                                                                                                                                                                                                                                                                                                            
         if isinstance(step, list):                                                                                                                                                                                                                                                                                                                                                           
             concurrent_results = await anyio.gather(*[self.execute_pipeline(child_pipeline, results) for child_pipeline in step])                                                                                                                                                                                                                                                            
             results[pipeline.name] = PipelineResult(status="success", data=concurrent_results)                                                                                                                                                                                                                                                                                               
         elif isinstance(step, Pipeline):                                                                                                                                                                                                                                                                                                                                                     
             child_client = pipeline.client.pipeline(step.name) if pipeline.client else None                                                                                                                                                                                                                                                                                                  
             child_pipeline = step.copy(update={"client": child_client})                                                                                                                                                                                                                                                                                                                      
             if index > 0 and isinstance(pipeline.steps[index - 1], Pipeline):                                                                                                                                                                                                                                                                                                                
                 previous_pipeline = pipeline.steps[index - 1]                                                                                                                                                                                                                                                                                                                                
                 previous_result = results.get(previous_pipeline.name)                                                                                                                                                                                                                                                                                                                        
                 child_pipeline.steps[0] = child_pipeline.steps[0], previous_result                                                                                                                                                                                                                                                                                                           
             await self.execute_pipeline(child_pipeline, results)                                                                                                                                                                                                                                                                                                                             
         else:                                                                                                                                                                                                                                                                                                                                                                                
             task, previous_result = step if isinstance(step, tuple) else (step, results.get(pipeline.name))                                                                                                                                                                                                                                                                                  
             result = await task(pipeline, previous_result)                                                                                                                                                                                                                                                                                                                                   
             results[pipeline.name] = result                                                                                                                                                                                                                                                                                                                                    
                                                                                                                                                                                                                                                                        

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

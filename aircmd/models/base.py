import sys
from typing import Any, Callable, Optional, Union

import dagger
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
from pydantic import BaseModel, Field, PrivateAttr

from ..plugin_manager import PluginManager
from .settings import GlobalSettings
from .singleton import Singleton


# this is a bit of a hack to get around how prefect resolves parameters
# basically without this, prefect will attempt to access the context
# before we create it in main.py in order to resolve it as a parameter
# wrapping it in a function like this prevents that from happening
def get_context() -> Context:                                                                                                                                       
    return get_current_context()   

class PipelineContext(BaseModel, Singleton):
    global_settings: GlobalSettings
    dockerd_service: Optional[Container] = Field(default=None)
    _dagger_client: Optional[Client] = PrivateAttr(default=None)
    _click_context: Callable[[], Context] = PrivateAttr(default_factory=lambda: get_context)

    class Config:
        arbitrary_types_allowed=True

    def __init__(self, global_settings: GlobalSettings, **data: dict[str, Any]):
        """
        Initialize the PipelineContext instance.

        This method checks the _initialized flag for the PipelineContext class in the Singleton base class.
        If the flag is False, the initialization logic is executed and the flag is set to True.
        If the flag is True, the initialization logic is skipped.

        This ensures that the initialization logic is only executed once, even if the PipelineContext instance is retrieved multiple times.
        This can be useful if the initialization logic is expensive (e.g., it involves network requests or database queries).
        """
        if not Singleton._initialized[PipelineContext]:
            super().__init__(global_settings=global_settings, **data)
            self.set_global_prefect_tag_context()
            Singleton._initialized[PipelineContext] = True
    
    import asyncio

    _dagger_client_lock: asyncio.Lock = PrivateAttr(default_factory=asyncio.Lock)

    async def get_dagger_client(self, client: Optional[Client] = None, pipeline_name: Optional[str] = None) -> Client:
        if not self._dagger_client:
            async with self._dagger_client_lock:
                if not self._dagger_client:
                    connection = dagger.Connection(dagger.Config(log_output=sys.stdout))
                    self._dagger_client = await self._click_context().with_async_resource(connection) # type: ignore
        client = self._dagger_client
        assert client, "Error initializing Dagger client"
        return client.pipeline(pipeline_name) if pipeline_name else client
    
    def set_global_prefect_tag_context(self) -> Optional[TagsContext]:
        if not TagsContext.get().current_tags:
            system_tags = self.global_settings.PREFECT_COMMA_DELIMITED_SYSTEM_TAGS.split(",")
            user_tags = self.global_settings.PREFECT_COMMA_DELIMITED_USER_TAGS.split(",")
            all_tags = system_tags + user_tags
            self._click_context().with_resource(tags(*all_tags))  # type: ignore
        return None 
    
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
    debug: bool = Field(default=False)

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, plugin_manager: Optional[PluginManager] = None, _click_context: Optional[Context] = None, debug: bool = False, **data: Any):
        if plugin_manager is None:
            plugin_manager = PluginManager(debug=debug)
        super().__init__(plugin_manager=plugin_manager, _click_context=_click_context, debug=debug, **data)

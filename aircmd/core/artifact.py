
from typing import Optional

from ..actions.environments import with_poetry
from ..models.base import GlobalSettings, Pipeline, PipelineContext
from ..models.click_commands import ClickCommandMetadata, ClickGroup
from ..models.utils import make_pass_decorator

pass_pipeline_context = make_pass_decorator(PipelineContext, ensure=True)
pass_global_settings = make_pass_decorator(GlobalSettings, ensure=True)

core_group = ClickGroup(group_name="core", group_help="Commands for developing aircmd")

class BuildCommand(ClickCommandMetadata):
    command_name: str = "build"
    command_help: str = "Builds aircmd"

async def build_task(parent_pipeline: Optional[Pipeline] = None) -> None:
    pipeline = await Pipeline.create("build", parent_pipeline=parent_pipeline)
    await with_poetry(pipeline).exec(["ls"]).stdout()

    #output = await ctr.stdout()
    #print(output[:300])
    return None


class CICommand(ClickCommandMetadata):
    command_name: str = "ci"
    command_help: str = "Run CI for aircmd"

@core_group.command(BuildCommand())
@pass_pipeline_context
async def build(ctx: PipelineContext) -> None:
    await ctx.run_pipelines([build_task()], concurrency=1)

@core_group.command(CICommand())
@pass_pipeline_context
async def ci(ctx: PipelineContext) -> None:
    """Run CI for aircmd"""
    # Creates the 'ci' pipeline as a standalone pipeline.
    ci_pipeline = await Pipeline.create("ci")
    await ctx.run_pipelines([build_task(ci_pipeline)], concurrency=1)

from typing import List

from ..models.base import PipelineContext
from ..models.click_commands import ClickArgument, ClickCommandMetadata, ClickGroup
from ..models.utils import make_pass_decorator

pass_pipeline_context = make_pass_decorator(PipelineContext, ensure=True)

plugin_group = ClickGroup(group_name="core", group_help="Commands for developing aircmd")

class BuildCommand(ClickCommandMetadata):
    command_name: str = "build"
    command_help: str = "Build aircmd"

@plugin_group.command(BuildCommand())
@pass_pipeline_context
async def build(ctx: PipelineContext) -> None:
    """Build aircmd"""
    async with ctx.dagger_connection as client:



class TestCommand(ClickCommandMetadata):
    command_name: str = "test"
    command_help: str = "Run tests for aircmd"
    arguments: List[ClickArgument] = [ClickArgument(name="query", required=False)]


class PublishCommand(ClickCommandMetadata):
    command_name: str = "publish"
    command_help: str = "Publish aircmd to PyPI"
    arguments: List[ClickArgument] = [ClickArgument(name="query", required=False)]


class CICommand(ClickCommandMetadata):
    command_name: str = "ci"
    command_help: str = "Run CI for aircmd"
    arguments: List[ClickArgument] = [ClickArgument(name="query", required=False)]

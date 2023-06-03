from typing import List

import dagger

from ..models.base import GlobalSettings, PipelineContext
from ..models.click_commands import ClickArgument, ClickCommandMetadata, ClickGroup
from ..models.utils import make_pass_decorator

pass_pipeline_context = make_pass_decorator(PipelineContext, ensure=True)
pass_global_settings = make_pass_decorator(GlobalSettings, ensure=True)

core_group = ClickGroup(group_name="core", group_help="Commands for developing aircmd")

class BuildCommand(ClickCommandMetadata):
    command_name: str = "build"
    command_help: str = "Build aircmd"

@core_group.command(BuildCommand())
@pass_pipeline_context
async def build(ctx: PipelineContext, settings: GlobalSettings) -> None:
    """Build aircmd"""
    async with ctx.dagger_connection as client:
        runner = (
            client.container(platform=dagger.Platform("linux/amd64"))
            .from_("python:3.11-buster")
            .with_directory("/app", client.host().directory(".", include=["./pyproject.toml", "./poetry.lock"]))
            .with_workdir("/app")
            .with_exec(["poetry", "install"]) # cache the installation of dependencies so we don't rerun every time we change src
            .with_directory("/app", client.host().directory(".", include=["./actions", "./aircmd", "./pyproject.toml", "./poetry.lock"]))
            .with_exec(["poetry", "run", "mypy", "."])
            .with_exec(["poetry", "run", "ruff", "."])
            .with_exec(["poetry", "build"])
        )
        await runner.stdout()



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

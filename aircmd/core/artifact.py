

from dagger import CacheVolume

from ..actions.environments import with_poetry
from ..models.base import (GlobalSettings, Pipeline, PipelineContext,
                           PipelineResult)
from ..models.click_commands import ClickCommandMetadata, ClickGroup
from ..models.utils import make_pass_decorator

pass_pipeline_context = make_pass_decorator(PipelineContext, ensure=True)
pass_global_settings = make_pass_decorator(GlobalSettings, ensure=True)

core_group = ClickGroup(group_name="core", group_help="Commands for developing aircmd")

class BuildCommand(ClickCommandMetadata):
    command_name: str = "build"
    command_help: str = "Builds aircmd"

async def build_task(pipeline: Pipeline, previous_result: PipelineResult) -> PipelineResult:
    client = pipeline.client
    mypy_cache: CacheVolume = client.cache_volume("mypy_cache")
    result = (with_poetry(client)
            .with_directory("/src", client.host().directory(".", include=["./pyproject.toml", "./poetry.lock"]))
            .with_workdir("/src")
            .with_exec(["poetry", "install"])
            .with_directory("/src", client.host().directory(".", include=["./aircmd", "./pyproject.toml", "./poetry.lock"]))
            .with_mounted_cache("/src/.mypy_cache", mypy_cache)
            #.with_exec(["poetry", "run", "mypy", "."])
            #.with_exec(["poetry", "run", "ruff", "."])
            .with_exec(["poetry", "build"])
    )
    await result.stdout()
    pipeline_result = PipelineResult(status="success", data=result)
    return pipeline_result

async def test_task(pipeline: Pipeline, build_result: PipelineResult) -> PipelineResult:
    client = pipeline.client
    mypy_cache: CacheVolume = client.cache_volume("mypy_cache")
    result = (with_poetry(client)
            .with_directory("/src", client.host().directory(".", include=["./tests", "./pyproject.toml", "./poetry.lock"]))
            .with_workdir("/src")
            .with_mounted_cache("/src/.mypy_cache", mypy_cache)
            .with_directory("/src/dist", build_result.data.directory("/src/dist"))  # Mount the wheel directory
            .with_exec(["poetry", "install", "--only", "test"])  # Install the dependencies using Poetry
            .with_exec(["sh", "-c", "poetry run pip install $(find /src/dist -name 'aircmd-*.whl')"])  # Install the wheel file using Poetry
            .with_exec(["poetry", "run", "pytest"])  # Run the tests using Poetry
    )
    await result.stdout()
    pipeline_result = PipelineResult(status="success", data=result)
    return pipeline_result


class CICommand(ClickCommandMetadata):
    command_name: str = "ci"
    command_help: str = "Run CI for aircmd"

@core_group.command(BuildCommand())
@pass_pipeline_context
async def build(ctx: PipelineContext) -> None:
    dagger_client = await ctx.get_dagger_client()
    build_pipeline = Pipeline("build", steps=[build_task], client=dagger_client.pipeline("build"))
    await ctx.execute_pipeline(build_pipeline)


@core_group.command(CICommand())
@pass_pipeline_context
async def ci(ctx: PipelineContext) -> None:
    top_level_client = await ctx.get_dagger_client()

    ci_pipeline = Pipeline("ci", steps=[], client=top_level_client)
    build_pipeline = Pipeline("build", steps=[build_task], client=ci_pipeline.client.pipeline("build"))
    test_pipeline = Pipeline("test", steps=[test_task], client=ci_pipeline.client.pipeline("test"))
    ci_pipeline.steps = [build_pipeline, test_pipeline]

    await ctx.execute_pipeline(ci_pipeline)  
    """Run CI for aircmd"""                                                                                               

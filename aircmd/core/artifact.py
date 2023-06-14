

from dagger import CacheVolume, Client

from ..actions.environments import with_poetry
from ..models.base import GlobalSettings, PipelineContext, PipelineResult
from ..models.click_commands import ClickCommandMetadata, ClickGroup
from ..models.utils import make_pass_decorator

pass_pipeline_context = make_pass_decorator(PipelineContext, ensure=True)
pass_global_settings = make_pass_decorator(GlobalSettings, ensure=True)

core_group = ClickGroup(group_name="core", group_help="Commands for developing aircmd")

class BuildCommand(ClickCommandMetadata):
    command_name: str = "build"
    command_help: str = "Builds aircmd"

async def build_task(client: Client) -> PipelineResult:
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

async def test_task(build_result: PipelineResult, client: Client) -> PipelineResult:
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
    build_pipeline_client = dagger_client.pipeline("build")
    await build_task(client=build_pipeline_client)

class TestCommand(ClickCommandMetadata):
    command_name: str = "test"
    command_help: str = "Tests aircmd"

@core_group.command(CICommand())
@pass_pipeline_context
async def ci(ctx: PipelineContext) -> None:
    ci_client = (await ctx.get_dagger_client()).pipeline("ci")
    build_pipeline_client = ci_client.pipeline("build")
    build_result = await build_task(client=build_pipeline_client)

    test_pipeline_client = ci_client.pipeline("test")
    await test_task(build_result=build_result, client=test_pipeline_client)
    """Run CI for aircmd"""                                                                                               

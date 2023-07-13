

from typing import Awaitable, Optional

from dagger import CacheVolume, Client, Container
from prefect import flow, task

from ..actions.environments import with_poetry
from ..models.base import GlobalSettings, PipelineContext
from ..models.click_commands import ClickCommandMetadata, ClickGroup
from ..models.utils import make_pass_decorator

pass_pipeline_context = make_pass_decorator(PipelineContext, ensure=True)
pass_global_settings = make_pass_decorator(GlobalSettings, ensure=True)

core_group = ClickGroup(group_name="core", group_help="Commands for developing aircmd")



@task
async def build_task(client: Client) -> Container:
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
    return result.sync()

@task
async def test_task(client: Client, build_result: Container) -> Container:
    mypy_cache: CacheVolume = client.cache_volume("mypy_cache")
    result = (with_poetry(client)
            .with_directory("/src", client.host().directory(".", include=["./tests", "./pyproject.toml", "./poetry.lock"]))
            .with_workdir("/src")
            .with_mounted_cache("/src/.mypy_cache", mypy_cache)
            .with_directory("/src/dist", build_result.directory("/src/dist"))  # Mount the wheel directory
            .with_exec(["poetry", "install", "--only", "test"])  # Install the dependencies using Poetry
            .with_exec(["sh", "-c", "poetry run pip install $(find /src/dist -name 'aircmd-*.whl')"])  # Install the wheel file using Poetry
            .with_exec(["poetry", "run", "pytest"])  # Run the tests using Poetry
    )
    return result.sync()


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
async def build(ctx: PipelineContext, client: Optional[Client] = None) -> Awaitable[Container]:
    build_client = client.pipeline(BuildCommand().command_name) if client else ctx.get_dagger_client().pipeline(BuildCommand().command_name) 
    build_result = await build_task.submit(build_client)
    return build_result.result()

@core_group.command(TestCommand())
@pass_pipeline_context
@flow(validate_parameters=False)
async def test(ctx: PipelineContext, client: Optional[Client] = None) -> Awaitable[Container]:
    test_client = client.pipeline(TestCommand().command_name) if client else ctx.get_dagger_client().pipeline(TestCommand().command_name) 
    build_result = await build(client=test_client)
    test_result = await test_task.submit(test_client, await build_result)
    return test_result.result()

@core_group.command(CICommand())
@pass_pipeline_context
@flow(validate_parameters=False)
async def ci(ctx: PipelineContext, client: Optional[Client] = None) -> Awaitable[Container]:
    ci_client = client.pipeline(CICommand().command_name) if client else ctx.get_dagger_client().pipeline(CICommand().command_name)
    test_result: Container = await test(client=ci_client)
    return test_result


    """Run CI for aircmd"""                                                                                               

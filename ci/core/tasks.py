from dagger import CacheVolume, Client, Container
from prefect import task

from aircmd.actions.environments import with_poetry
from aircmd.models.settings import GlobalSettings


@task
async def build_task(client: Client, settings: GlobalSettings) -> Container:
    mypy_cache: CacheVolume = client.cache_volume("mypy_cache")
    result = (with_poetry(client)
            .with_directory("/src", client.host().directory(".", include=["./pyproject.toml", "./poetry.lock", "./ci", "./aircmd"]))
            .with_workdir("/src")
            .with_exec(["poetry", "install"])
            .with_mounted_cache("/src/.mypy_cache", mypy_cache)
            .with_exec(["poetry", "run", "mypy", "."])
            .with_exec(["poetry", "run", "ruff", "."])
            .with_exec(["poetry", "build"])
    )
    await result.sync()
    return result

@task
async def test_task(client: Client, settings: GlobalSettings, build_result: Container) -> Container:
    mypy_cache: CacheVolume = client.cache_volume("mypy_cache")
    result = (with_poetry(client)
            .with_directory("/src", client.host().directory(".", include=["./tests", "./pyproject.toml", "./poetry.lock", "./ci", "./aircmd"]))
            .with_workdir("/src")
            .with_mounted_cache("/src/.mypy_cache", mypy_cache)
            .with_directory("/src/dist", build_result.directory("/src/dist"))  # Mount the wheel directory
            .with_exec(["poetry", "install", "--only", "test"])  # Install the dependencies using Poetry
            .with_exec(["sh", "-c", "poetry run pip install $(find /src/dist -name 'aircmd-*.whl')"])  # Install the wheel file using Poetry
            .with_exec(["poetry", "run", "pytest"])  # Run the tests using Poetry
    )
    await result.sync()
    return result

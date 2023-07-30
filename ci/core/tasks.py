


import asyncio

import anyio
from dagger import CacheVolume, Client, Container
from prefect import task

from aircmd.actions.environments import with_poetry


@task
async def build_task(client: Client) -> Container:
    print("BUILD TASKS")
    print(anyio.get_current_task())
    print(anyio.get_running_tasks())
    print("Current event loop in build task", id(asyncio.get_running_loop()))
    mypy_cache: CacheVolume = client.cache_volume("mypy_cache")
    result = (with_poetry(client)
            .with_directory("/src", client.host().directory(".", include=["./pyproject.toml", "./poetry.lock", "./ci", "./aircmd"]))
            .with_workdir("/src")
            .with_exec(["poetry", "install"])
            .with_mounted_cache("/src/.mypy_cache", mypy_cache)
            #.with_exec(["poetry", "run", "mypy", "."])
            #.with_exec(["poetry", "run", "ruff", "."])
            .with_exec(["poetry", "build"])
    )
    return result.sync()

@task
async def test_task(client: Client, build_result: Container) -> Container:
    print("TEST TASKS")
    print(anyio.get_current_task())
    print(anyio.get_running_tasks())
    print("Current event loop in test task", id(asyncio.get_running_loop()))
    build_result = await build_result
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
    await result.sync()
    return result

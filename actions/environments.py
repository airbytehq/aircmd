from dagger import CacheVolume, Container, Platform

from ..aircmd.models.base import PipelineContext


def with_python_base(context: PipelineContext, python_image_name: str = "python:3.11-slim") -> Container:
    """Build a Python container with a cache volume for pip cache.

    Args:
        context (PipelineContext): The current test context, providing a dagger client and a repository directory.
        python_image_name (str, optional): The python image to use to build the python base environment. Defaults to "python:3.9-slim".

    Raises:
        ValueError: Raised if the python_image_name is not a python image.

    Returns:
        Container: The python base environment container.
    """
    if not python_image_name.startswith("python:3"):
        raise ValueError("You have to use a python image to build the python base environment")
    pip_cache: CacheVolume = context.dagger_client.cache_volume("pip_cache")

    base_container = (
        context.dagger_client.container(platform=Platform("linux/amd64"))
        .from_(python_image_name)
        .with_mounted_cache("/root/.cache/pip", pip_cache)
        .with_mounted_cache("")
        .with_exec(["pip", "install", "--upgrade", "pip"])
        .with_exec(["pip", "install", "poetry"])
    )

    return base_container

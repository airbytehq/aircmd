from typing import Callable, List, Optional

from dagger import Client, Container, Directory, QueryError

from ..models.settings import GlobalSettings


def get_repo_dir(client: Client, settings: GlobalSettings, subdir: str = ".", exclude: Optional[List[str]] = None, include: Optional[List[str]] = None) -> Directory:

    """Get a directory from the current repository.

    If running in the CI:
    The directory is extracted from the git branch.

    If running locally:
    The directory is extracted from your host file system.
    A couple of files or directories that could corrupt builds are exclude by default (check DEFAULT_EXCLUDED_FILES).

    Args:
        subdir (str, optional): Path to the subdirectory to get. Defaults to "." to get the full repository.
        exclude ([List[str], optional): List of files or directories to exclude from the directory. Defaults to None.
        include ([List[str], optional): List of files or directories to include in the directory. Defaults to None.

    Returns:
        Directory: The selected repo directory.
    """
    if exclude is None:
        exclude = settings.DEFAULT_EXCLUDED_FILES
    else:
        exclude += settings.DEFAULT_EXCLUDED_FILES
        exclude = list(set(exclude))
    if subdir != ".":
        subdir = f"{subdir}/" if not subdir.endswith("/") else subdir
        exclude = [f.replace(subdir, "") for f in exclude if subdir in f]
    return client.host().directory(subdir, exclude=exclude, include=include)

async def get_file_contents(container: Container, path: str) -> Optional[str]:
    """Retrieve a container file contents.

    Args:
        container (Container): The container hosting the file you want to read.
        path (str): Path, in the container, to the file you want to read.

    Returns:
        Optional[str]: The file content if the file exists in the container, None otherwise.
    """
    try:
        return await container.file(path).contents()
    except QueryError as e:
        if "no such file or directory" not in str(e):
            # this is the hacky bit of the stopgap because
            # this error could come from a network issue
            raise
    return None

def sync_from_gradle_cache_to_homedir(cache_volume_location: str, gradle_home_dir: str) -> Callable[[Container], Container]:
    def sync_cache(ctr: Container) -> Container:
        ctr = ctr.with_exec(["ls", "-la", cache_volume_location])
        ctr = ctr.with_exec(["rsync", "-az", cache_volume_location, gradle_home_dir])
        return ctr
    return sync_cache

def sync_to_gradle_cache_from_homedir(cache_volume_location: str, gradle_home_dir: str) -> Callable[[Container], Container]:
    def sync_cache(ctr: Container) -> Container:
        ctr = ctr.with_exec(["rsync", "-az", "--delete", gradle_home_dir, cache_volume_location])
        return ctr
    return sync_cache

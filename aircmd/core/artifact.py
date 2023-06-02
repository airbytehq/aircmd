from typing import List

from ..models.click_commands import ClickArgument, ClickCommandMetadata


class BuildCommand(ClickCommandMetadata):
    command_name: str = "build"
    command_help: str = "Build aircmd"
    arguments: List[ClickArgument] = [ClickArgument(name="query", required=False)]

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

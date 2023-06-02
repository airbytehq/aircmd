import pytest
from pydantic import ValidationError

from aircmd.models.click_commands import ClickCommand, ClickCommandMetadata, ClickGroup


def test_click_command_creation() -> None:
    # Test valid input
    valid_metadata = ClickCommandMetadata(command_name="test", command_help="Test command")
    valid_command = ClickCommand(**valid_metadata.model_dump())
    assert valid_command.command_name == "test"
    assert valid_command.command_help == "Test command"

    # Test invalid input using a loop
    invalid_cases = [
        {"command_name": "", "command_help": "Empty string"},
        {"command_name": "space in name", "command_help": "Space in name"},
        {"command_name": "Capital", "command_help": "Capital letter in name"},
        {"command_name": "verylongcommandthatisgreaterthan20chars", "command_help": "Long command name"},
        {"command_name": "emptyhelp", "command_help": ""},
        {"command_name": "longhelp", "command_help": "A very long command help that happens to be longer than 100 characters. A very long command help that happens to be longer than 100 characters"},
    ]

    for case in invalid_cases:
        with pytest.raises(ValidationError):
            ClickCommandMetadata(**case)

def test_click_group_creation() -> None:
    # Test valid input
    valid_group = ClickGroup(group_name="test", group_help="Test group")
    assert valid_group.group_name == "test"
    assert valid_group.group_help == "Test group"

    # Test invalid input using a loop
    invalid_cases = [
        {"group_name": "", "group_help": "Empty string"},
        {"group_name": "space in name", "group_help": "Space in name"},
        {"group_name": "Capital", "group_help": "Capital letter in name"},
        {"group_name": "verylonggroupthatisgreaterthan20chars", "group_help": "Long group name"},
        {"group_name": "emptyhelp", "group_help": ""},
        {"group_name": "longhelp", "group_help": "A very long group help that happens to be longer than 100 characters. A very long group help that happens to be longer than 100 characters"},
    ]

    for case in invalid_cases:
        with pytest.raises(ValidationError):
            ClickGroup(**case)
        

def test_add_command_to_group() -> None:
    group = ClickGroup(group_name="test", group_help="Test group")
    command_metadata = ClickCommandMetadata(command_name="test", command_help="Test command")
    command = ClickCommand(**command_metadata.model_dump())

    group.commands[command.command_name] = command
    assert len(group.commands) == 1
    assert group.commands["test"] == command

def test_add_subgroup_to_group() -> None:
    parent_group = ClickGroup(group_name="parent", group_help="Parent group")
    child_group = ClickGroup(group_name="child", group_help="Child group")

    parent_group.add_group(child_group)
    assert len(parent_group.subgroups) == 1
    assert parent_group.subgroups["child"] == child_group

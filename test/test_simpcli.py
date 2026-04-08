"""Tests for the package simpcli."""

from __future__ import annotations

import sys
from collections import deque
from typing import TYPE_CHECKING
from typing import Any

import pytest

from simpcli import ARGPARSE_EXIT
from simpcli import ARGUMENT_ERROR
from simpcli import FAILURE
from simpcli import NO_COMMAND_ERROR
from simpcli import SUCCESS
from simpcli import Command
from simpcli import Manager
from simpcli import NoDefault
from simpcli import Parameter
from simpcli import Result

if TYPE_CHECKING:  # pragma: no cover
    from _pytest.monkeypatch import MonkeyPatch


class TestNoDefault:
    """Tests for simpcli.NoDefault."""

    def test_new(self) -> None:
        """Test for NoDefault.__new__()."""
        obj1: NoDefault = NoDefault()
        obj2: NoDefault = NoDefault()

        assert isinstance(obj1, NoDefault)
        assert isinstance(obj2, NoDefault)
        assert obj1 is obj2

    def test_repr(self) -> None:
        """Test for NoDefault.__repr__()."""
        obj: NoDefault = NoDefault()

        repr_str: str = repr(obj)

        assert isinstance(repr_str, str)
        assert repr_str == "NoDefault"

    def test_remove_defaults(self) -> None:
        """Test for NoDefault.remove_defaults()."""
        obj: dict[str, Any] = {"a": 1, "b": NoDefault(), "c": 3, "d": 4, "e": NoDefault()}

        result: dict[str, Any] = NoDefault.remove_defaults(**obj)

        assert result == {"a": 1, "c": 3, "d": 4}
        assert all(v is not NoDefault() for v in result.values())


class TestManager:
    """Tests for simpcli.Manager."""

    manager_name: str = "program"
    manager_version: str = "0.0.0"

    @pytest.fixture
    def manager(self) -> Manager:
        """Fixture to create a Manager object."""
        return Manager(prog=self.manager_name, version=self.manager_version)

    def test_init(self, manager: Manager) -> None:
        """Test for Manager.__init__()."""
        assert manager.prog == self.manager_name
        assert manager.version == self.manager_version
        assert manager.kwargs == {}
        assert manager.commands == {}

    def test_global_parameter(self, manager: Manager) -> None:
        """Test for Manager.global_parameter()."""
        manager.global_parameter("--flag", action="store_true", help="help")

        assert len(manager.global_parameters) == 1

        parameter: Parameter = manager.global_parameters[0]

        assert isinstance(parameter, Parameter)
        assert parameter.args == ["--flag"]
        assert parameter.kwargs == {"action": "store_true", "help": "help"}

        @manager.command()
        def command(flag: bool) -> Result:  # noqa: FBT001
            return SUCCESS if flag else FAILURE

        assert manager.run("--flag", "command") == SUCCESS
        assert manager.run("command") == FAILURE

    class TestCommand:
        """Test for Manager.command()."""

        def test_basic(self, manager: Manager) -> None:
            """Test for Manager.command()."""

            @manager.command()
            def command() -> Result:
                return SUCCESS

            result: Result = command()
            assert result == SUCCESS

            command_obj: Command = manager.commands[command.__name__]

            assert isinstance(command_obj, Command)
            assert not hasattr(command, "parameters")
            assert command_obj.func is command
            assert command_obj.kwargs == {}
            assert command_obj.parameters == []

        def test_kwargs(self, manager: Manager) -> None:
            """Test for Manager.command() with kwargs."""

            @manager.command(description="description")
            def command() -> Result:
                return SUCCESS

            command_obj: Command = manager.commands[command.__name__]

            assert isinstance(command_obj, Command)
            assert not hasattr(command, "parameters")
            assert command_obj.func is command
            assert command_obj.kwargs == {"description": "description"}
            assert command_obj.parameters == []

        def test_parameters(self, manager: Manager) -> None:
            """Test for Manager.command() with parameters."""

            @manager.command()
            @manager.parameter("param", description="description")
            def command(param: int) -> Result:
                return param

            command_obj: Command = manager.commands[command.__name__]

            assert isinstance(command_obj, Command)
            assert not hasattr(command, "parameters")
            assert command_obj.func is command
            assert command_obj.kwargs == {}
            assert command_obj.parameters == [
                Parameter(args=["param"], kwargs={"description": "description"}),
            ]

    class TestParameter:
        """Test for Manager.parameter()."""

        def test_basic(self, manager: Manager) -> None:
            """Test for Manager.parameter()."""

            @manager.parameter("param")
            def command(param: int) -> Result:  # noqa: ARG001
                return SUCCESS

            assert hasattr(command, "parameters")
            assert isinstance(command.parameters, deque)

            parameter: Parameter = command.parameters[0]

            assert isinstance(parameter, Parameter)
            assert parameter.args == ["param"]
            assert parameter.kwargs == {}

        def test_args(self, manager: Manager) -> None:
            """Test for Manager.parameter() with multiple args."""

            @manager.parameter("-f", "--flag")
            def command(flag: bool) -> Result:  # noqa: ARG001, FBT001
                return SUCCESS

            parameter: Parameter = command.parameters[0]  # ty:ignore[unresolved-attribute]

            assert isinstance(parameter, Parameter)
            assert parameter.args == ["-f", "--flag"]
            assert parameter.kwargs == {}

        def test_kwargs(self, manager: Manager) -> None:
            """Test for Manager.parameter() with kwargs."""

            @manager.parameter("param", description="description")
            def command(param: int) -> Result:  # noqa: ARG001
                return SUCCESS

            parameter: Parameter = command.parameters[0]  # ty:ignore[unresolved-attribute]

            assert isinstance(parameter, Parameter)
            assert parameter.args == ["param"]
            assert parameter.kwargs == {"description": "description"}

    class TestRun:
        """Test for Manager.run()."""

        def test_basic(self, manager: Manager) -> None:
            """Test for Manager.run() with basic commands."""

            @manager.command()
            @manager.parameter("param")
            def command(param: int) -> Result:  # noqa: ARG001
                return SUCCESS

            result: Result = manager.run("--verbose", "command", 1)

            assert result == SUCCESS

        def test_exit(self, manager: Manager) -> None:
            """Test for Manager.run() when argparse exits."""

            @manager.command()
            def command() -> Result:
                return SUCCESS

            result: Result = manager.run("--help", "command")

            assert result == ARGPARSE_EXIT

        def test_none(self, manager: Manager) -> None:
            """Test for Manager.run() with no command."""

            @manager.command()
            def command() -> Result:
                return SUCCESS

            result: Result = manager.run()

            assert result == NO_COMMAND_ERROR

        def test_unknown(self, manager: Manager) -> None:
            """Test for Manager.run() with an unknown command."""

            @manager.command()
            def command() -> Result:
                return SUCCESS

            result: Result = manager.run("unknown")

            assert result == ARGUMENT_ERROR

        def test_failed(self, manager: Manager) -> None:
            """Test for Manager.run() with an unknown command."""

            @manager.command()
            def command() -> Result:
                raise ValueError

            result: Result = manager.run("command")

            assert result == -1

    def test_handle_main(self, monkeypatch: MonkeyPatch, manager: Manager) -> None:
        """Test for Manager.handle_main()."""
        monkeypatch.setattr(sys, "argv", [sys.argv[0], "command"])

        @manager.command()
        def command() -> Result:
            return SUCCESS

        with pytest.raises(SystemExit):
            manager.handle_main()


if __name__ == "__main__":
    pytest.main()

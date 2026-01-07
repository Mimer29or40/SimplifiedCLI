"""Tests for the package simpcli."""

from __future__ import annotations

import logging
import sys
from collections import deque
from logging import FileHandler
from logging import Logger
from logging.handlers import RotatingFileHandler
from logging.handlers import TimedRotatingFileHandler
from typing import TYPE_CHECKING
from typing import Any

import pytest

import simpcli
from simpcli import ARGUMENT_ERROR
from simpcli import NO_COMMAND_ERROR
from simpcli import Command
from simpcli import Manager
from simpcli import NoDefault
from simpcli import Parameter
from simpcli import Result
from simpcli import get_logger
from simpcli import set_logger_file

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Generator
    from logging import Handler
    from pathlib import Path

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


class TestGetLogger:
    """Tests for simpcli.get_logger()."""

    def test_standard(self) -> None:
        """Test for simpcli.get_logger() with standard input."""
        name: str = "test_logger"

        obj: Logger = get_logger(name)

        assert isinstance(obj, Logger)
        assert obj.name == name
        assert obj.parent is simpcli.logger

    def test_parent(self) -> None:
        """Test for simpcli.get_logger() with parent logger name input."""
        name: str = "simpcli"

        obj: Logger = get_logger(name)

        assert isinstance(obj, Logger)
        assert obj is simpcli.logger


class TestSetLoggerFile:
    """Tests for simpcli.set_logger_file()."""

    @pytest.fixture
    def context(self) -> Generator[None]:
        """Fixture to set up simpcli.logger for testing."""
        simpcli.logger.handlers = [simpcli.logger_handler]
        yield
        simpcli.logger.handlers = [simpcli.logger_handler]

    def test_no_parameters(self) -> None:
        """Test for simpcli.set_logger_file() with no parameters."""
        with pytest.raises(ValueError, match=r"Must supply either 'file' or 'handler'"):
            set_logger_file()

    @pytest.mark.usefixtures("context")
    def test_file(self, tmp_path: Path) -> None:
        """Test for simpcli.set_logger_file() with file parameter."""
        file: Path = tmp_path / "logs/test_file.log"

        set_logger_file(file)

        assert file.parent.exists()
        assert len(simpcli.logger.handlers) == 2  # noqa: PLR2004

        logger_handler: Handler = simpcli.logger.handlers[1]

        assert isinstance(logger_handler, TimedRotatingFileHandler)
        assert logger_handler.level == logging.INFO
        assert logger_handler.formatter == simpcli.logger_formatter

    @pytest.mark.usefixtures("context")
    def test_handler(self, tmp_path: Path) -> None:
        """Test for simpcli.set_logger_file() with handler parameter."""
        file: Path = tmp_path / "test_file.log"

        handler: FileHandler = RotatingFileHandler(file)

        set_logger_file(handler=handler)

        assert len(simpcli.logger.handlers) == 2  # noqa: PLR2004

        logger_handler: Handler = simpcli.logger.handlers[1]

        assert logger_handler is handler

    def test_both_parameters(self, tmp_path: Path) -> None:
        """Test for simpcli.set_logger_file() with both parameters."""
        file: Path = tmp_path / "test_file.log"
        handler: FileHandler = RotatingFileHandler(file)

        with pytest.raises(ValueError, match=r"'file' and 'handler' are mutually exclusive"):
            set_logger_file(file, handler=handler)


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
        manager.global_parameter("--flag", description="description")

        assert len(manager.global_parameters) == 1

        parameter: Parameter = manager.global_parameters[0]

        assert isinstance(parameter, Parameter)
        assert parameter.args == ["--flag"]
        assert parameter.kwargs == {"description": "description"}

    class TestCommand:
        """Test for Manager.command()."""

        def test_basic(self, manager: Manager) -> None:
            """Test for Manager.command()."""

            @manager.command()
            def command() -> Result:
                return 0

            result: Result = command()
            assert result == 0

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
                return 0

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
                return 0

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
                return 0

            parameter: Parameter = command.parameters[0]

            assert isinstance(parameter, Parameter)
            assert parameter.args == ["-f", "--flag"]
            assert parameter.kwargs == {}

        def test_kwargs(self, manager: Manager) -> None:
            """Test for Manager.parameter() with kwargs."""

            @manager.parameter("param", description="description")
            def command(param: int) -> Result:  # noqa: ARG001
                return 0

            parameter: Parameter = command.parameters[0]

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
                return 0

            result: Result = manager.run("--verbose", "command", 1)

            assert result == 0

        def test_none(self, manager: Manager) -> None:
            """Test for Manager.run() with no command."""

            @manager.command()
            def command() -> Result:
                return 0

            result: Result = manager.run()

            assert result == NO_COMMAND_ERROR

        def test_unknown(self, manager: Manager) -> None:
            """Test for Manager.run() with an unknown command."""

            @manager.command()
            def command() -> Result:
                return 0

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
            return 0

        with pytest.raises(SystemExit):
            manager.handle_main()


if __name__ == "__main__":
    pytest.main()

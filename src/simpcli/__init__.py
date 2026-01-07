"""A simplified command line interface using argparse."""

from __future__ import annotations

import logging
import sys
from argparse import ArgumentError
from argparse import ArgumentParser
from collections import deque
from dataclasses import dataclass
from logging.handlers import TimedRotatingFileHandler
from typing import TYPE_CHECKING
from typing import NoReturn
from typing import Protocol
from typing import override

if TYPE_CHECKING:  # pragma: no cover
    # noinspection PyProtectedMember
    from argparse import _SubParsersAction
    from collections.abc import Callable
    from collections.abc import Mapping
    from collections.abc import Sequence
    from logging import FileHandler
    from logging import Formatter
    from logging import Handler
    from logging import Logger
    from pathlib import Path
    from typing import Any
    from typing import Self


__all__: list[str] = [
    "ARGUMENT_ERROR",
    "NO_COMMAND_ERROR",
    "NO_DEFAULT",
    "Command",
    "Manager",
    "NoCommandError",
    "NoDefault",
    "Parameter",
    "Result",
    "get_logger",
    "logger",
    "logger_formatter",
    "logger_handler",
    "set_logger_file",
]

type Result = int | str


class CommandFunc(Protocol):
    __name__: str
    parameters: Sequence[Parameter]

    def __call__(self, *args: Any, **kwargs: Any) -> Result:  # pragma: no cover  # noqa: ANN401
        pass


logger_formatter: Formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

logger_handler: Handler = logging.StreamHandler(sys.stdout)
logger_handler.setFormatter(logger_formatter)
logger_handler.setLevel(logging.INFO)

logger: Logger = logging.getLogger(__name__)
logger.propagate = False
logger.setLevel(logging.DEBUG)
logger.handlers = [logger_handler]


class NoDefault:
    """Singleton to declare that a parameter has no default values."""

    __instance__: NoDefault | None = None

    def __new__(cls) -> Self:
        """Create the singleton instance or return it."""
        if cls.__instance__ is None:
            cls.__instance__ = super().__new__(cls)
        return cls.__instance__

    @override
    def __repr__(self) -> str:
        return "NoDefault"

    @classmethod
    def remove_defaults(cls, **kwargs: Any) -> dict[str, Any]:  # noqa: ANN401
        """Remove NoDefault from kwargs."""
        no_default: NoDefault = NoDefault()
        return {k: v for k, v in kwargs.items() if v is not no_default}


NO_DEFAULT: NoDefault = NoDefault()
ARGUMENT_ERROR: int = 10
NO_COMMAND_ERROR: int = 11


def get_logger(name: str) -> Logger:
    """Get a logger whose parent is simpcli.logger.

    :param name: The name of the logger, usually __name__.
    :return: The logger.
    """
    if name == __name__:
        return logger

    new_logger: Logger = logging.getLogger(name)
    new_logger.parent = logger
    return new_logger


def set_logger_file(file: Path | None = None, /, *, handler: FileHandler | None = None) -> None:
    """Set the log FileHandler at the file provided or to the FileHandler provided."""
    file_handler: FileHandler
    if file is None:
        if handler is None:
            message: str = "Must supply either 'file' or 'handler'"
            raise ValueError(message)
        file_handler = handler
    elif handler is None:
        file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = TimedRotatingFileHandler(file, when="D", backupCount=7)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logger_formatter)
    else:
        message: str = "'file' and 'handler' are mutually exclusive"
        raise ValueError(message)

    logger.handlers = [logger_handler, file_handler]


class NoCommandError(Exception):
    """Exception raised when no command is provided."""

    def __init__(self, message: str = "No command provided") -> None:  # noqa: D107
        super().__init__(message)


@dataclass(frozen=True)
class Command:
    """A runnable command."""

    kwargs: Mapping[str, Any]
    parameters: Sequence[Parameter]
    func: CommandFunc


@dataclass(frozen=True)
class Parameter:
    """A parameter for a command."""

    args: Sequence[str]
    kwargs: Mapping[str, Any]


@dataclass(init=False, frozen=True, kw_only=True)
class Manager:
    """Manages the command line interface."""

    prog: str
    version: str | None
    kwargs: Mapping[str, Any]

    global_parameters: list[Parameter]
    commands: dict[str, Command]

    def __init__(self, prog: str, version: str | None = None, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize the manager."""
        object.__setattr__(self, "prog", prog)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "kwargs", kwargs)

        object.__setattr__(self, "global_parameters", [])
        object.__setattr__(self, "commands", {})

    def global_parameter(self, name_or_flag: str, *name_or_flags: str, **kwargs: Any) -> None:  # noqa: ANN401
        """Add a global parameter to the manager."""
        args: list[str] = [name_or_flag, *name_or_flags]

        self.global_parameters.append(Parameter(args, kwargs))

    def command[C: CommandFunc](self, **kwargs: Any) -> Callable[[C], C]:  # noqa: ANN401
        """Designate the function as a command."""

        def decorator(func: C) -> C:
            # TODO(Ryan): inspect.signature(func, annotation_format=Format.FORWARD_REF)
            parameters: Sequence[Parameter] = []
            if hasattr(func, "parameters"):
                parameters: Sequence[Parameter] = list(func.parameters)
                delattr(func, "parameters")
            self.commands[func.__name__] = Command(func=func, kwargs=kwargs, parameters=parameters)

            return func

        return decorator

    @staticmethod
    def parameter[C: CommandFunc](
        name_or_flag: str,
        *name_or_flags: str,
        **kwargs: Any,  # noqa: ANN401
    ) -> Callable[[C], C]:
        """Add additional configuration to a command parameter."""
        args: list[str] = [name_or_flag, *name_or_flags]

        def decorator(func: C) -> C:
            parameters: deque[Parameter] = getattr(func, "parameters", deque())
            parameters.appendleft(Parameter(args, kwargs))
            func.parameters = parameters
            return func

        return decorator

    def run(self, *args: Any) -> Result:  # noqa: ANN401
        """Run the command line interface.

        :param args: The raw arguments to pass to the command.
        :return: The result of the command.
        """
        result: Result
        try:
            parser: ArgumentParser = self.create_parser()

            cleaned_args: list[str] = list(map(str, args))
            parsed_args: dict[str, Any] = dict(vars(parser.parse_args(cleaned_args)))

            result = self.__handle_command(parsed_args)
        except ArgumentError as e:
            # Raised when ArgumentParser fails to parse the arguments.
            logger.exception("Argparse error:", exc_info=e)
            result = ARGUMENT_ERROR
        except NoCommandError as e:
            # Raised when no command is provided.
            logger.exception("No command error:", exc_info=e)
            result = NO_COMMAND_ERROR
        except BaseException as e:
            logger.exception("Unhandled Exception:", exc_info=e)
            result = -1

        return result

    def handle_main(self) -> NoReturn:
        """Handle main."""
        args: list[str] = sys.argv[1:]
        result: Result = self.run(*args)
        sys.exit(result)

    def create_parser(self) -> ArgumentParser:
        """Create the ArgumentParser instance."""
        prog: str = f"{self.prog}.exe" if getattr(sys, "frozen", False) else f"{self.prog}.py"
        kwargs: dict[str, Any] = dict(self.kwargs)
        kwargs.setdefault("exit_on_error", False)
        parser: ArgumentParser = ArgumentParser(prog=prog, **kwargs)

        parser.add_argument("--verbose", action="store_true")
        if self.version is not None:
            parser.add_argument("-v", "--version", action="version", version=self.version)

        parameter: Parameter
        for parameter in self.global_parameters:
            parser.add_argument(*parameter.args, **parameter.kwargs)

        # User Defined Commands
        command_parser: _SubParsersAction = parser.add_subparsers(
            dest="command",
            metavar="command",
        )

        command_name: str | None
        command: Command
        for command_name, command in self.commands.items():
            command_kwargs: dict[str, Any] = dict(command.kwargs)
            command_kwargs.setdefault("description", command.func.__doc__)

            user_command_parser: ArgumentParser = command_parser.add_parser(
                command_name,
                **command_kwargs,
            )
            parameter: Parameter
            for parameter in command.parameters:
                user_command_parser.add_argument(*parameter.args, **parameter.kwargs)

        return parser

    def __handle_command(self, parsed_args: dict[str, Any]) -> Result:
        if parsed_args.pop("verbose", False):
            logger_handler.setLevel(logging.DEBUG)

        command_name: str = parsed_args.pop("command")
        command: Command | None = self.commands.get(command_name, None)
        if command is None:
            raise NoCommandError

        return command.func(**parsed_args)

"""A simplified command line interface using argparse."""

import inspect
import logging
import sys
from annotationlib import Format
from dataclasses import dataclass
from dataclasses import field
from logging.handlers import TimedRotatingFileHandler
from typing import TYPE_CHECKING
from typing import NoReturn

if TYPE_CHECKING:  # pragma: no cover
    from inspect import Signature
    from logging import FileHandler
    from logging import Formatter
    from logging import Handler
    from logging import Logger
    from pathlib import Path
    from typing import Any


__all__: list[str] = [
    "Manager",
    "Result",
    "get_logger",
    "logger",
    "logger_formatter",
    "logger_handler",
    "set_logger_file",
]

type Result = int | str

logger_formatter: Formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

logger_handler: Handler = logging.StreamHandler(sys.stdout)
logger_handler.setFormatter(logger_formatter)
logger_handler.setLevel(logging.INFO)

logger: Logger = logging.getLogger(__name__)
logger.propagate = False
logger.setLevel(logging.DEBUG)
logger.handlers = [logger_handler]


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
    """Set the log FileHandler at the file provided."""
    file_handler: FileHandler
    if file is None:
        if handler is None:
            message: str = "Must supply either a file or a handler."
            raise ValueError(message)
        file_handler = handler
    elif handler is None:
        file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = TimedRotatingFileHandler(file, when="D", backupCount=7)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logger_formatter)
    else:
        file_handler = handler

    logger.handlers = [logger_handler, file_handler]


@dataclass(frozen=True)
class Manager:
    """Manages the command line interface."""

    commands: dict[str, object] = field(default_factory=dict, init=False)

    def parameter[T](self, func: T) -> T:
        """Add additional configuration to a command parameter."""
        return func

    def command[T](self, func: T) -> T:
        """Designate the function as a command..

        :param func: The function to use as a command.
        :return: The function.
        """
        signature: Signature = inspect.signature(func, annotation_format=Format.FORWARDREF)
        return func

    def run(self, *args: Any) -> Result:  # noqa: ANN401
        """Run the command line interface.

        :param args: The raw arguments to pass to the command.
        :return: The result of the command.
        """
        cleaned_args: list[str] = list(map(str, args))

        result: Result = 0
        try:
            pass
        except SystemExit:  # pragma: no cover
            # Raised when ArgumentParser fails to parse the arguments.
            result = 10
        except BaseException as e:
            logger.exception("Unhandled Exception:", exc_info=e)
            result = -1

        return result

    def handle_main(self) -> NoReturn:
        """Handle main."""
        args: list[str] = sys.argv[1:]
        result: Result = self.run(*args)
        sys.exit(result)

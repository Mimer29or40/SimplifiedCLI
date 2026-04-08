"""Basic example."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from simpcli import Manager

if TYPE_CHECKING:  # pragma: no cover
    from logging import Logger

    from simpcli import Result

__version__: str = "0.0.1"

logger: Logger = logging.getLogger()


manager: Manager = Manager(prog=__name__, version=__version__)


@manager.command()
def no_args() -> Result:
    """Command with no arguments."""
    logger.info("no_args")
    return 0


@manager.command()
@manager.parameter("one", type=str)
@manager.parameter("two", type=int)
def positional_args(one: str, two: int) -> Result:
    """Command with positional arguments."""
    logger.info("positional_args %s %s", one, two)
    return 0


@manager.command()
@manager.parameter("param", type=str)
@manager.parameter("-f", "--flag", action="store_true", type=bool)
def optional_args(param: str, flag: bool = False) -> Result:  # noqa: FBT001, FBT002
    """Command with optional arguments."""
    logger.info("flags %s %s", param, flag)
    return 0


if __name__ == "__main__":
    manager.handle_main()

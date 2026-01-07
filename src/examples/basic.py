"""Basic example."""

from __future__ import annotations

from typing import TYPE_CHECKING

from simpcli import Manager
from simpcli import get_logger

if TYPE_CHECKING:  # pragma: no cover
    from logging import Logger

    from simpcli import Result

__version__: str = "0.0.1"

logger: Logger = get_logger(__name__)


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


if __name__ == "__main__":
    manager.handle_main()

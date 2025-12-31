"""Basic example."""

from typing import TYPE_CHECKING

from simpcli import Manager

if TYPE_CHECKING:  # pragma: no cover
    from simpcli import Result

manager: Manager = Manager()


@manager.command
def no_args() -> Result:
    """Command with no arguments."""
    return 0


@manager.command
@manager.parameter("one")
@manager.parameter
def positional_args(one: str, two: int) -> Result:
    """Command with positional arguments."""
    return 0


if __name__ == "__main__":
    manager.handle_main()

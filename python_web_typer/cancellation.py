"""
Cooperative cancellation of running actions (the GUI "Stop" button).

Every pause of the actions goes through `cancellable_sleep`, which raises
`Cancelled` as soon as a cancel is requested, even in the middle of a long wait.
"""

import threading

__all__ = ["Cancelled", "request_cancel", "reset_cancel", "cancellable_sleep"]

_cancel = threading.Event()


class Cancelled(BaseException):
    """
    Raised inside an action after `request_cancel()`.

    A BaseException (like KeyboardInterrupt) so the `except Exception` safety
    nets of the task runner don't swallow it and carry on with the next task.
    """


def request_cancel() -> None:
    _cancel.set()


def reset_cancel() -> None:
    _cancel.clear()


def cancellable_sleep(seconds: float) -> None:
    if _cancel.wait(max(0.0, seconds)):
        raise Cancelled()

"""
Cooperative cancellation of running actions (the GUI "Stop" button).

Every pause of the actions goes through `cancellable_sleep`, which raises
`Cancelled` as soon as a cancel is requested, even in the middle of a long wait.

It is also where actions are held while the operator solves a CAPTCHA
(`hold_actions` / `release_actions`, driven by the DOM observer): the action
goes on with its next step once released.
"""

import logging
import threading
import time

__all__ = [
    "Cancelled",
    "HoldTimeout",
    "request_cancel",
    "reset_cancel",
    "is_cancel_requested",
    "hold_actions",
    "release_actions",
    "wait_if_held",
    "cancellable_sleep",
]

logger = logging.getLogger(__name__)

_cancel = threading.Event()
_released = threading.Event()
_released.set()
# Reminder in the logs while an action stays held
_HOLD_REMINDER_EVERY = 60


class Cancelled(BaseException):
    """
    Raised inside an action after `request_cancel()`.

    A BaseException (like KeyboardInterrupt) so the `except Exception` safety
    nets of the task runner don't swallow it and carry on with the next task.
    """


class HoldTimeout(Exception):
    """
    A CAPTCHA / verification wasn't solved within config.HUMAN_CHECK_HOLD_TIMEOUT
    (or is an automatic check that never lets the browser through). Ends the
    current action; the next one (other platform) runs.
    """


def request_cancel() -> None:
    _cancel.set()


def reset_cancel() -> None:
    _cancel.clear()
    _released.set()


def is_cancel_requested() -> bool:
    return _cancel.is_set()


def hold_actions(reason: str) -> None:
    """Running actions stop at their next pause until `release_actions()`."""
    if _released.is_set():
        logger.warning("Holding: %s. Solve it in the browser, the action goes on afterwards", reason)
    _released.clear()


def release_actions() -> None:
    if not _released.is_set():
        logger.info("Released, resuming")
    _released.set()


def wait_if_held() -> float:
    """
    Blocks while actions are held. Returns the seconds spent held.

    Raises:
        Cancelled: stop requested meanwhile.
        HoldTimeout: still held after config.HUMAN_CHECK_HOLD_TIMEOUT. The hold is
            released, so the next action isn't caught by the same check.
    """
    if _released.is_set():
        return 0.0
    from .config import HUMAN_CHECK_HOLD_TIMEOUT  # config is heavier, only needed here

    start = time.monotonic()
    reminder = start + _HOLD_REMINDER_EVERY
    while not _released.wait(0.5):
        if _cancel.is_set():
            raise Cancelled()
        now = time.monotonic()
        if now - start >= HUMAN_CHECK_HOLD_TIMEOUT:
            _released.set()
            raise HoldTimeout(f"CAPTCHA / verification not solved within {HUMAN_CHECK_HOLD_TIMEOUT}s")
        if now >= reminder:
            logger.info("Still waiting for the CAPTCHA / verification to be solved in the browser")
            reminder = now + _HOLD_REMINDER_EVERY
    return time.monotonic() - start


def cancellable_sleep(seconds: float) -> None:
    if _cancel.wait(max(0.0, seconds)):
        raise Cancelled()
    wait_if_held()

import logging
import platform
import subprocess
from typing import Iterable

__all__ = ["is_file_selector_open", "bring_window_to_front"]

logger = logging.getLogger(__name__)

current_platform = platform.system()


def _unsupported_platform() -> NotImplementedError:
    return NotImplementedError(f"Window selection is not supported on {current_platform}")


def is_file_selector_open(target_window_titles: Iterable[str]):
    """
    Returns the first window whose title contains one of `target_window_titles`
    (case-insensitive): a pygetwindow Window on Windows, a `wmctrl -l` line on Linux.
    """
    targets = [t.lower() for t in target_window_titles]

    if current_platform == "Windows":
        import pygetwindow as gw

        for window in gw.getAllWindows():
            title = window.title.lower()
            if any(target in title for target in targets):
                return window
        return None

    if current_platform == "Linux":
        try:
            output = subprocess.check_output(["wmctrl", "-l"], text=True)
        except (OSError, subprocess.CalledProcessError) as e:
            logger.error("Linux window detection failed (is wmctrl installed?): %s", e)
            return None
        for line in output.splitlines():
            lowered = line.lower()
            if any(target in lowered for target in targets):
                return line
        return None

    raise _unsupported_platform()


def bring_window_to_front(window) -> None:
    if not window:
        return

    if current_platform == "Windows":
        window.activate()
        window.maximize()  # Optional, ensure visibility
        return

    if current_platform == "Linux":
        window_id = window.split()[0]
        try:
            subprocess.run(["wmctrl", "-i", "-a", window_id], check=True)
        except (OSError, subprocess.CalledProcessError) as e:
            logger.error("Failed to bring window to front on Linux: %s", e)
        return

    raise _unsupported_platform()

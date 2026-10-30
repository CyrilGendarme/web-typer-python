import logging
import time
from typing import Optional

import pyautogui

from .simulate_actions_base import press_keys_platform_dependent, type_text
from .windows_selection import bring_window_to_front, is_file_selector_open

__all__ = [
    "TARGET_WINDOW_TITLES",
    "type_in_directory_field",
    "type_in_filename_field",
    "select_file_window",
]

logger = logging.getLogger(__name__)

TARGET_WINDOW_TITLES = ("Open", "Save As", "Select File", "File Upload", "Ouvrir")


def type_in_directory_field(folder_path: str) -> None:
    press_keys_platform_dependent({"win": ["ctrl", "l"], "linux": ["shift", "tab"]})
    type_text(folder_path)
    pyautogui.press("enter")


def type_in_filename_field(filename: str) -> None:
    press_keys_platform_dependent({"win": ["alt", "n"], "linux": ["shift", "tab"]})
    type_text(filename)
    pyautogui.press("enter")


def select_file_window(
    directory_path: str,
    filename: str,
    timeout: Optional[float] = 60,
    poll_interval: float = 0.5,
) -> bool:
    """
    Waits for a native file selector window, then types the directory and filename into it.

    Returns:
        bool: True if a file was selected, False if no selector appeared within `timeout`
        (None = wait forever).
    """
    logger.info("Waiting for file selector window to open...")
    deadline = None if timeout is None else time.monotonic() + timeout

    while deadline is None or time.monotonic() < deadline:
        window = is_file_selector_open(TARGET_WINDOW_TITLES)

        if window:
            logger.info(
                "Detected file selector window: %s",
                window if isinstance(window, str) else window.title,
            )
            bring_window_to_front(window)

            type_in_directory_field(directory_path)
            type_in_filename_field(filename)

            logger.info("File selected successfully!")
            return True

        time.sleep(poll_interval)

    logger.error("No file selector window appeared within %ss", timeout)
    return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    select_file_window(
        "C:\\Users\\User\\Desktop\\reels\\AiGen\\BELGAE\\1_something\\final",
        "nova_1_We_took_someone’s_seat_on_the_airplane___10_minecraft_1080x1920.mp4",
    )

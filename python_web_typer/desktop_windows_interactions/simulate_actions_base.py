import logging
import platform

import keyboard
import pyautogui

__all__ = ["type_text", "press_keys_platform_dependent"]

logger = logging.getLogger(__name__)

current_platform = platform.system()

_PLATFORM_HOTKEY_KEYS = {"Windows": "win", "Linux": "linux"}


def type_text(text: str) -> None:
    # keyboard.write handles per-character emission (and non-ASCII) itself
    keyboard.write(text)


def press_keys_platform_dependent(hotkeys: dict) -> None:
    """
    Args:
        hotkeys (dict): Dictionary with two keys: 'win' and 'linux'.
                        Each maps to a list representing the hotkey sequence.
                        Example: { 'win': ['ctrl', 'l'], 'linux': ['shift', 'tab'] }
    """
    keys = hotkeys.get(_PLATFORM_HOTKEY_KEYS.get(current_platform, ""))

    if keys:
        pyautogui.hotkey(*keys)
    else:
        logger.warning("No hotkeys defined for %s", current_platform)

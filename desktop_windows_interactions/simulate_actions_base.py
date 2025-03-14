import keyboard
import pyautogui
import time
import platform

current_platform = platform.system()


def type_text(text):
    for char in text:
        keyboard.write(char)
        time.sleep(0.035)


def press_keys_platform_dependent(hotkeys: dict):
    """
    Args:
        hotkeys (dict): Dictionary with two keys: 'win' and 'linux'.
                        Each maps to a list representing the hotkey sequence.
                        Example: { 'win': ['ctrl', 'l'], 'linux': ['shift', 'tab'] }
    """
    keys = None

    if current_platform == "Windows":
        keys = hotkeys.get("win")
    elif current_platform == "Linux":
        keys = hotkeys.get("linux")

    if keys:
        pyautogui.hotkey(*keys)
        time.sleep(0.3)
    else:
        print(f"[WARNING] No hotkeys defined for {current_platform}")

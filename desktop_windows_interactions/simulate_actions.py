import pyautogui
import os
import sys
import time

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

from desktop_windows_interactions.simulate_actions_base import (
    press_keys_platform_dependent,
    type_text,
)
from desktop_windows_interactions.windows_selection import (
    is_file_selector_open,
    bring_window_to_front,
)


def type_in_directory_field(folder_path):
    press_keys_platform_dependent({"win": ["ctrl", "l"], "linux": ["shift", "tab"]})
    type_text(folder_path)
    pyautogui.press("enter")
    # time.sleep(1)


def type_in_filename_field(filename):
    press_keys_platform_dependent({"win": ["alt", "n"], "linux": ["shift", "tab"]})
    type_text(filename)
    pyautogui.press("enter")
    # time.sleep(1)


def select_file_window(directory_path: str, filename: str):

    TARGET_WINDOW_TITLES = ["Open", "Save As", "Select File", "File Upload", "Ouvrir"]

    print("Waiting for file selector window to open...")

    while True:
        window = is_file_selector_open(TARGET_WINDOW_TITLES)

        if window:
            print(
                f"Detected file selector window: {window if isinstance(window, str) else window.title}"
            )
            bring_window_to_front(window)

            # time.sleep(0.5)

            type_in_directory_field(directory_path)
            type_in_filename_field(filename)

            print("File selected successfully!")
            break

        time.sleep(1)


if __name__ == "__main__":
    select_file_window(
        "C:\\Users\\User\\Desktop\\reels\\AiGen\\BELGAE\\1_something\\final",
        "nova_1_We_took_someone’s_seat_on_the_airplane___10_minecraft_1080x1920.mp4",
    )

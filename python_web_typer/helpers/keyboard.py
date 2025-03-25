from enum import Enum
import platform
import subprocess


class KeyboardLayout(Enum):
    US_ENGLISH = 0x0409
    UK_ENGLISH = 0x0809
    FRENCH = 0x040C
    FR_BE = 0x080C
    GERMAN = 0x0407
    ITALIAN = 0x0410
    SPANISH = 0x0C0A
    DUTCH = 0x0413
    PORTUGUESE = 0x0816
    RUSSIAN = 0x0419
    JAPANESE = 0x0411
    CHINESE_SIMPLIFIED = 0x0804
    CHINESE_TRADITIONAL = 0x0404
    ARABIC = 0x0401
    HEBREW = 0x040D

    @classmethod
    def from_layout_code(cls, code):
        for layout in cls:
            if layout.value == code:
                return layout
        return None


def get_keyboard_layout():
    current_platform = platform.system()

    if current_platform == "Windows":
        try:
            import win32api

            layout = win32api.GetKeyboardLayout(0)

            masked_layout = layout & 0xFFFF

            layout_enum = KeyboardLayout.from_layout_code(masked_layout)

            if layout_enum:
                return layout_enum.name.replace(
                    "_", " "
                ).title()  # Or return layout_enum if you prefer
            else:
                return f"Other (0x{masked_layout:X})"

        except ImportError:
            print("pywin32 is not installed. Unable to detect Windows keyboard layout.")
            return None

    elif current_platform == "Linux":
        try:
            layout = (
                subprocess.check_output("setxkbmap -query | grep layout", shell=True)
                .decode()
                .strip()
                .split(":")[1]
                .strip()
            )
            if layout == "be":
                return KeyboardLayout.FR_BE.name.replace("_", " ").title()
            else:
                return layout  # Could map more Linux layouts to enums if needed
        except subprocess.CalledProcessError:
            print("Unable to detect Linux keyboard layout using setxkbmap.")
            return None

    elif current_platform == "Darwin":  # macOS
        try:
            layout = (
                subprocess.check_output(
                    "defaults read -g AppleKeyboardUIMode", shell=True
                )
                .decode()
                .strip()
            )
            return layout
        except subprocess.CalledProcessError:
            print("Unable to detect macOS keyboard layout.")
            return None

    else:
        print(f"Unsupported OS: {current_platform}")
        return None

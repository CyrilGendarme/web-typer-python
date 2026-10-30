import logging
import platform
import subprocess
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


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
    def from_layout_code(cls, code: int) -> Optional["KeyboardLayout"]:
        try:
            return cls(code)
        except ValueError:
            return None


_LINUX_LAYOUTS = {"be": KeyboardLayout.FR_BE}


def _layout_display_name(layout: KeyboardLayout) -> str:
    return layout.name.replace("_", " ").title()


def get_keyboard_layout() -> Optional[str]:
    """Returns a human-readable name of the active keyboard layout, or None if undetectable."""
    current_platform = platform.system()

    if current_platform == "Windows":
        try:
            import win32api
        except ImportError:
            logger.warning("pywin32 is not installed. Unable to detect Windows keyboard layout.")
            return None

        masked_layout = win32api.GetKeyboardLayout(0) & 0xFFFF
        layout_enum = KeyboardLayout.from_layout_code(masked_layout)
        if layout_enum:
            return _layout_display_name(layout_enum)
        return f"Other (0x{masked_layout:X})"

    if current_platform == "Linux":
        try:
            output = subprocess.check_output(["setxkbmap", "-query"], text=True)
        except (OSError, subprocess.CalledProcessError):
            logger.warning("Unable to detect Linux keyboard layout using setxkbmap.")
            return None
        for line in output.splitlines():
            key, _, value = line.partition(":")
            if key.strip() == "layout":
                layout = value.strip()
                # Could map more Linux layouts to enums if needed
                if layout in _LINUX_LAYOUTS:
                    return _layout_display_name(_LINUX_LAYOUTS[layout])
                return layout
        return None

    if current_platform == "Darwin":
        try:
            # e.g. "com.apple.keylayout.Belgian"
            source_id = subprocess.check_output(
                [
                    "defaults",
                    "read",
                    "com.apple.HIToolbox",
                    "AppleCurrentKeyboardLayoutInputSourceID",
                ],
                text=True,
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            logger.warning("Unable to detect macOS keyboard layout.")
            return None
        return source_id.rsplit(".", 1)[-1]

    logger.warning("Unsupported OS: %s", current_platform)
    return None

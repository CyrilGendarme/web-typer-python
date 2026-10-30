"""Detection of the browsers installed on this machine (Linux, Windows, macOS)."""

import logging
import os
import platform
import shutil
from enum import Enum
from typing import Dict, Iterable, List, NamedTuple, Optional

from ..config import BROWSER_PRIORITY

__all__ = [
    "Browser",
    "InstalledBrowser",
    "find_browser_binary",
    "detect_available_browsers",
    "pick_browser",
]

logger = logging.getLogger(__name__)

current_platform = platform.system()


class Browser(Enum):
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    CHROME = "chrome"
    EDGE = "edge"

    @property
    def is_chromium_based(self) -> bool:
        return self is not Browser.FIREFOX


class InstalledBrowser(NamedTuple):
    browser: Browser
    binary: str

    @property
    def is_snap(self) -> bool:
        """Snap packages (Ubuntu) are confined and need special handling."""
        return self.binary.startswith("/snap/")


def _win_paths(*relative_paths: str) -> List[str]:
    roots = ("%ProgramFiles%", "%ProgramFiles(x86)%", "%LocalAppData%")
    return [
        os.path.expandvars(os.path.join(root, rel))
        for rel in relative_paths
        for root in roots
    ]


# Executable names (looked up in PATH) or absolute paths, per browser and OS
_CANDIDATES: Dict[Browser, Dict[str, List[str]]] = {
    Browser.CHROMIUM: {
        "Linux": ["chromium", "chromium-browser"],
        "Windows": _win_paths(r"Chromium\Application\chrome.exe"),
        "Darwin": ["/Applications/Chromium.app/Contents/MacOS/Chromium"],
    },
    Browser.FIREFOX: {
        "Linux": ["firefox", "firefox-esr"],
        "Windows": _win_paths(r"Mozilla Firefox\firefox.exe"),
        "Darwin": ["/Applications/Firefox.app/Contents/MacOS/firefox"],
    },
    Browser.CHROME: {
        "Linux": ["google-chrome", "google-chrome-stable"],
        "Windows": _win_paths(r"Google\Chrome\Application\chrome.exe"),
        "Darwin": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"],
    },
    Browser.EDGE: {
        "Linux": ["microsoft-edge", "microsoft-edge-stable"],
        "Windows": _win_paths(r"Microsoft\Edge\Application\msedge.exe"),
        "Darwin": ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"],
    },
}


def _resolve_snap_wrapper(path: str) -> str:
    """
    Ubuntu ships /usr/bin/firefox, /usr/bin/chromium-browser... as shell scripts
    that exec the snap. Return the snap binary so snap specifics get applied.
    """
    snap_binary = f"/snap/bin/{os.path.basename(path)}"
    if current_platform != "Linux" or not os.path.exists(snap_binary):
        return path
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
    except OSError:
        return path
    if head.startswith(b"#!") and b"/snap/bin/" in head:
        return snap_binary
    return path


def find_browser_binary(browser: Browser) -> Optional[str]:
    """Returns the executable path of `browser`, or None if it isn't installed."""
    for candidate in _CANDIDATES[browser].get(current_platform, []):
        path = shutil.which(candidate) or (
            candidate if os.path.isfile(candidate) else None
        )
        if path:
            return _resolve_snap_wrapper(path)
    return None


def _as_browsers(priority: Iterable) -> List[Browser]:
    return [b if isinstance(b, Browser) else Browser(b) for b in priority]


def detect_available_browsers(
    priority: Iterable = BROWSER_PRIORITY,
) -> List[InstalledBrowser]:
    """Lists the installed browsers, ordered by `priority`."""
    found = []
    for browser in _as_browsers(priority):
        binary = find_browser_binary(browser)
        if binary:
            found.append(InstalledBrowser(browser, binary))
    return found


def pick_browser(
    priority: Iterable = BROWSER_PRIORITY,
    chromium_based_only: bool = False,
) -> Optional[InstalledBrowser]:
    """Returns the first installed browser in `priority` order."""
    for installed in detect_available_browsers(priority):
        if chromium_based_only and not installed.browser.is_chromium_based:
            continue
        logger.info("Using %s (%s)", installed.browser.value, installed.binary)
        return installed

    logger.error("No supported browser found among %s", list(priority))
    return None

import logging
import os
import subprocess
import time
import urllib.request
from typing import Iterable, Optional

import psutil
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chromium.options import ChromiumOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.remote.webdriver import WebDriver

from ..config import BROWSER_PRIORITY, BROWSER_PROFILES_DIR
from .browsers import Browser, InstalledBrowser, pick_browser

__all__ = [
    "USE_DEFAULT_PROFILE",
    "get_webdriver",
    "get_headless_webdriver",
    "attach_to_open_chrome",
    "launch_chrome_with_debugging",
    "close_driver_and_chrome_by_port",
]

logger = logging.getLogger(__name__)

# Sentinel: use the dedicated per-browser profile from config
USE_DEFAULT_PROFILE = "default"


# ---------------------------
# Quiet settings: no automation banner, no pop-ups
# ---------------------------

# Chromium-family UI nags that get in the way of an operator watching the run
_QUIET_CHROMIUM_ARGS = (
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-search-engine-choice-screen",
    "--disable-notifications",
    "--password-store=basic",  # no OS keyring unlock prompt on Linux
)

_QUIET_CHROMIUM_PREFS = {
    # "Save password?" / "Change your password" bubbles
    "credentials_enable_service": False,
    "profile.password_manager_enabled": False,
    "profile.password_manager_leak_detection": False,
    "autofill.profile_enabled": False,
    "autofill.credit_card_enabled": False,
    # "Translate this page?" bubble
    "translate.enabled": False,
    # Site permission prompts (notifications, geolocation)
    "profile.default_content_setting_values.notifications": 2,
    "profile.default_content_setting_values.geolocation": 2,
}

# Firefox always shows a robot icon / striped URL bar under automation (not
# removable), but the pop-ups below are.
_QUIET_FIREFOX_PREFS = {
    "signon.rememberSignons": False,
    "extensions.formautofill.addresses.enabled": False,
    "extensions.formautofill.creditCards.enabled": False,
    "browser.translations.automaticallyPopup": False,
    "browser.shell.checkDefaultBrowser": False,
    "browser.aboutwelcome.enabled": False,
    "datareporting.policy.dataSubmissionPolicyBypassNotification": True,
    "permissions.default.desktop-notification": 2,
    "permissions.default.geo": 2,
}

# Snap packages (Ubuntu) can't access hidden dirs in $HOME and ship their own driver
_SNAP_DRIVERS = {
    Browser.CHROMIUM: ("/snap/bin/chromium.chromedriver",),
    Browser.FIREFOX: ("/snap/bin/geckodriver", "/snap/bin/firefox.geckodriver"),
}


def _profile_dir(installed: InstalledBrowser, user_data_dir: Optional[str]) -> Optional[str]:
    if user_data_dir != USE_DEFAULT_PROFILE:
        return user_data_dir
    if installed.is_snap:
        snap_name = os.path.basename(installed.binary)
        return os.path.join(
            os.path.expanduser("~"), "snap", snap_name, "common", "python_web_typer-profile"
        )
    return os.path.join(BROWSER_PROFILES_DIR, installed.browser.value)


def _snap_driver(installed: InstalledBrowser) -> Optional[str]:
    if not installed.is_snap:
        return None
    return next((p for p in _SNAP_DRIVERS.get(installed.browser, ()) if os.path.exists(p)), None)


def _chromium_options(
    installed: InstalledBrowser, headless: bool, profile_dir: Optional[str]
) -> ChromiumOptions:
    options = EdgeOptions() if installed.browser is Browser.EDGE else ChromeOptions()
    options.binary_location = installed.binary
    if headless:
        options.add_argument("--headless=new")

    # Removes the "<browser> is being controlled by automated test software" bar
    options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )
    options.add_argument("--disable-blink-features=AutomationControlled")

    for arg in _QUIET_CHROMIUM_ARGS:
        options.add_argument(arg)
    options.add_experimental_option("prefs", _QUIET_CHROMIUM_PREFS)

    if profile_dir:
        options.add_argument(f"--user-data-dir={profile_dir}")
    return options


def _firefox_options(
    installed: InstalledBrowser, headless: bool, profile_dir: Optional[str]
) -> FirefoxOptions:
    options = FirefoxOptions()
    options.binary_location = installed.binary
    if headless:
        options.add_argument("-headless")

    for name, value in _QUIET_FIREFOX_PREFS.items():
        options.set_preference(name, value)

    if profile_dir:
        options.add_argument("-profile")
        options.add_argument(profile_dir)
    return options


# ---------------------------
# Driver creation
# ---------------------------


def get_webdriver(
    browser: Optional[Browser] = None,
    headless: bool = False,
    user_data_dir: Optional[str] = USE_DEFAULT_PROFILE,
    priority: Iterable = BROWSER_PRIORITY,
) -> WebDriver:
    """
    Starts a WebDriver on the first installed browser in `priority` order
    (config.BROWSER_PRIORITY), without automation banner and pop-ups.

    Args:
        browser: Force a specific browser instead of auto-detection.
        headless: Run without a window.
        user_data_dir: Persistent profile folder (keeps logins and cookies between
            runs). USE_DEFAULT_PROFILE = one dedicated folder per browser,
            None = throwaway profile. A profile can only be used by one browser
            instance at a time.
        priority: Browser order for auto-detection.

    Raises:
        RuntimeError: If no supported browser is installed.
    """
    installed = pick_browser([browser] if browser else priority)
    if installed is None:
        raise RuntimeError("No supported browser installed (chromium, firefox, chrome, edge)")

    profile_dir = _profile_dir(installed, user_data_dir)
    if profile_dir:
        os.makedirs(profile_dir, exist_ok=True)

    driver_path = _snap_driver(installed)

    if installed.browser is Browser.FIREFOX:
        return webdriver.Firefox(
            options=_firefox_options(installed, headless, profile_dir),
            service=FirefoxService(executable_path=driver_path) if driver_path else None,
        )

    options = _chromium_options(installed, headless, profile_dir)
    if installed.browser is Browser.EDGE:
        return webdriver.Edge(options=options)
    return webdriver.Chrome(
        options=options,
        service=ChromeService(executable_path=driver_path) if driver_path else None,
    )


def get_headless_webdriver() -> WebDriver:
    """Backward-compatible alias, now actually headless."""
    return get_webdriver(headless=True)


# ---------------------------
# Attach to a manually launched Chromium-family browser
# ---------------------------


def attach_to_open_chrome(
    debugger_address: str = "127.0.0.1:9222",
) -> Optional[webdriver.Chrome]:
    """
    Attach Selenium WebDriver to an already open Chromium/Chrome window.

    A browser started by `launch_chrome_with_debugging` (or by hand) shows no
    automation infobar at all, since the driver didn't launch it.
    """
    options = ChromeOptions()
    options.debugger_address = debugger_address  # Connect to the running browser

    try:
        driver = webdriver.Chrome(options=options)
        logger.info("Successfully attached to the existing browser window.")
        return driver
    except WebDriverException as e:
        logger.error("Error attaching to browser: %s", e)
        return None


def _wait_for_debug_port(debug_port: int, timeout: float) -> bool:
    url = f"http://127.0.0.1:{debug_port}/json/version"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def launch_chrome_with_debugging(
    chrome_path: Optional[str] = None,
    user_data_dir: Optional[str] = USE_DEFAULT_PROFILE,
    debug_port: int = 9222,
    startup_timeout: float = 15,
) -> Optional[subprocess.Popen]:
    """
    Launches a Chromium-family browser with remote debugging enabled and waits
    until it accepts connections. Without `chrome_path`, the first installed
    Chromium-based browser in config.BROWSER_PRIORITY is used (Firefox skipped).

    Use with `attach_to_open_chrome`. Prefs (password/translate bubbles) can't be
    passed on the command line: turn them off once in the browser settings,
    they persist in the profile.
    """
    if chrome_path:
        installed = InstalledBrowser(Browser.CHROMIUM, chrome_path)
    else:
        installed = pick_browser(chromium_based_only=True)
        if installed is None:
            return None

    profile_dir = _profile_dir(installed, user_data_dir)
    args = [installed.binary, f"--remote-debugging-port={debug_port}", *_QUIET_CHROMIUM_ARGS]
    if profile_dir:
        os.makedirs(profile_dir, exist_ok=True)
        args.append(f"--user-data-dir={profile_dir}")

    try:
        process = subprocess.Popen(args)
    except OSError as e:
        logger.error("Failed to launch browser: %s", e)
        return None

    if _wait_for_debug_port(debug_port, startup_timeout):
        logger.info("Launched %s with remote debugging on port %d", installed.binary, debug_port)
    else:
        logger.warning(
            "Debug port %d not reachable after %ss", debug_port, startup_timeout
        )
    return process


def _find_pid_listening_on(port: int) -> Optional[int]:
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr and conn.laddr.port == port and conn.status == "LISTEN":
                return conn.pid
    except psutil.AccessDenied:
        # macOS requires root for system-wide listing, fall back to per-process scan
        for proc in psutil.process_iter():
            try:
                if any(c.laddr.port == port for c in proc.net_connections("inet")):
                    return proc.pid
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    return None


def close_driver_and_chrome_by_port(driver, debug_port: int = 9222) -> None:
    """Closes Selenium WebDriver and kills the browser process using the specified debug port."""

    if driver:
        try:
            driver.quit()
            logger.info("WebDriver session closed.")
        except WebDriverException as e:
            logger.warning("Error while closing WebDriver: %s", e)

    pid = _find_pid_listening_on(debug_port)
    if pid is None:
        return

    try:
        proc = psutil.Process(pid)
        logger.info("Killing process %d (%s) using port %d", pid, proc.name(), debug_port)
        proc.terminate()  # Try graceful shutdown
        try:
            proc.wait(timeout=5)
        except psutil.TimeoutExpired:
            proc.kill()  # Force kill if terminate didn't work
            logger.info("Process %d force killed.", pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        logger.warning("Error killing process on port %d: %s", debug_port, e)

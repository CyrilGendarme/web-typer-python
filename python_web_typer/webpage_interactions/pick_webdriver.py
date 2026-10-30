import logging
import os
import subprocess
import time
import urllib.request
from typing import Optional

import psutil
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options

__all__ = [
    "get_chrome_webdriver",
    "get_headless_webdriver",
    "attach_to_open_chrome",
    "launch_chrome_with_debugging",
    "close_driver_and_chrome_by_port",
]

logger = logging.getLogger(__name__)


def get_chrome_webdriver(headless: bool = False) -> webdriver.Chrome:
    """
    Launch a Chrome WebDriver with the automation banner removed.

    Chrome's real user agent is kept on purpose: a hardcoded, outdated UA is a
    stronger bot signal than the default one.
    """
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--disable-blink-features=AutomationControlled")

    return webdriver.Chrome(options=options)


def get_headless_webdriver() -> webdriver.Chrome:
    """Backward-compatible alias, now actually headless."""
    return get_chrome_webdriver(headless=True)


def attach_to_open_chrome(
    debugger_address: str = "127.0.0.1:9222",
) -> Optional[webdriver.Chrome]:
    """Attach Selenium WebDriver to an already open Chrome window."""
    options = Options()
    options.debugger_address = debugger_address  # Connect to the running browser

    try:
        driver = webdriver.Chrome(options=options)
        logger.info("Successfully attached to the existing Chrome window.")
        return driver
    except WebDriverException as e:
        logger.error("Error attaching to Chrome: %s", e)
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
    chrome_path: str = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    user_data_dir: str = "C:\\selenium\\ChromeProfile",
    debug_port: int = 9222,
    startup_timeout: float = 15,
) -> Optional[subprocess.Popen]:
    """Launches Chrome with remote debugging enabled and waits until it accepts connections."""

    os.makedirs(user_data_dir, exist_ok=True)

    try:
        process = subprocess.Popen(
            [
                chrome_path,
                f"--remote-debugging-port={debug_port}",
                f"--user-data-dir={user_data_dir}",
            ]
        )
    except OSError as e:
        logger.error("Failed to launch Chrome: %s", e)
        return None

    if _wait_for_debug_port(debug_port, startup_timeout):
        logger.info("Launched Chrome with remote debugging on port %d", debug_port)
    else:
        logger.warning(
            "Chrome debug port %d not reachable after %ss", debug_port, startup_timeout
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
    """Closes Selenium WebDriver and kills the Chrome process using the specified debug port."""

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

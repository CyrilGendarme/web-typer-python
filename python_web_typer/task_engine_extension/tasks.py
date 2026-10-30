import logging
import time

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

from ..webpage_interactions.pick_webpage_element import (
    ElementSelectorMethod,
    pick_element,
)
from ..webpage_interactions.simulate_click import simulate_click
from ..webpage_interactions.simulate_typing import simulate_typing

__all__ = [
    "click_element",
    "type_into_element",
    "drag_and_drop_file",
    "sleep",
    "type_keys",
    "access_url",
    "scroll_to_bottom",
    "select_file_through_window",
    "wait_for_captcha_task",
]

logger = logging.getLogger(__name__)


#
#
# Here are the core functions
#
def click_element(
    driver: WebDriver, method: ElementSelectorMethod, identifier: str, nth: int = 0
) -> bool:
    """
    Clicks on a webpage element based on the specified selection method.

    Args:
        driver (WebDriver): Selenium WebDriver instance.
        method (ElementSelectorMethod): The method used to locate the element (Enum value).
        identifier (str): The actual value for the selected method (ID, class, CSS selector, etc.).
        nth (int, optional): Index of the element if multiple exist (default is 0).

    Returns:
        bool: True if the element was found and clicked.
    """
    element = pick_element(driver, method, identifier, nth)
    if not element:
        logger.error("Could not find element %s using %s", identifier, method.name)
        return False
    return simulate_click(driver, element)


# core
def type_into_element(
    driver: WebDriver,
    method: ElementSelectorMethod,
    identifier: str,
    text: str,
    nth: int = 0,
) -> bool:
    """
    Finds a webpage element and types the given text into it.

    Args:
        driver (WebDriver): Selenium WebDriver instance.
        method (ElementSelectorMethod): The method used to locate the element (Enum value).
        identifier (str): The actual value for the selected method (ID, class, CSS selector, etc.).
        text (str): The text to be typed into the selected element.
        nth (int, optional): Index of the element if multiple exist (default is 0).

    Returns:
        bool: True if the element was found and typed into.
    """
    element = pick_element(driver, method, identifier, nth)
    if not element:
        logger.error("Could not find element %s using %s", identifier, method.name)
        return False
    simulate_typing(driver, element, text)
    return True


# core
def drag_and_drop_file(
    driver: WebDriver,
    method_file_input: ElementSelectorMethod,
    method_drop_zone: ElementSelectorMethod,
    file_input_selector: str,
    drop_zone_selector: str,
    file_path: str,
    nth_file_input: int = 0,
    nth_drop_zone: int = 0,
) -> bool:
    """
    Simulates dragging and dropping a file into a drop zone.

    Args:
        driver (WebDriver): Selenium WebDriver instance.
        method_file_input (ElementSelectorMethod): Method to locate the file input.
        method_drop_zone (ElementSelectorMethod): Method to locate the drop zone.
        file_input_selector (str): Selector for the hidden file input.
        drop_zone_selector (str): Selector for the drop zone.
        file_path (str): Absolute path of the file to be uploaded.
        nth_file_input (int, optional): Index of file input if multiple exist (default: 0).
        nth_drop_zone (int, optional): Index of drop zone if multiple exist (default: 0).
    """

    file_input = pick_element(
        driver, method_file_input, file_input_selector, nth_file_input
    )
    if not file_input:
        logger.error(
            "File input element not found using %s - %s",
            method_file_input.name,
            file_input_selector,
        )
        return False

    # Send file to hidden input
    file_input.send_keys(file_path)

    # The drop zone is optional: only look for it briefly, the upload already happened
    drop_zone = pick_element(
        driver, method_drop_zone, drop_zone_selector, nth_drop_zone, wait_time=2
    )
    if not drop_zone:
        logger.warning(
            "Drop zone not found using %s - %s, using direct file input upload only",
            method_drop_zone.name,
            drop_zone_selector,
        )
        return True

    # Attempt a visual drag-and-drop
    try:
        ActionChains(driver).click_and_hold(file_input).move_to_element(
            drop_zone
        ).release().perform()
        logger.debug("Drag-and-drop simulation executed.")
    except WebDriverException as e:
        logger.warning("Drag-and-drop action failed: %s", e)

    return True


# core
def sleep(delay: float) -> None:
    time.sleep(delay)


# core
def type_keys(
    driver: WebDriver,
    method: ElementSelectorMethod,
    identifier: str,
    key: str,
    nth: int = 0,
) -> bool:
    """
    Simulates pressing a keyboard key on a webpage element.

    Args:
        driver (WebDriver): Selenium WebDriver instance.
        method (ElementSelectorMethod): Method to locate the element.
        identifier (str): The selector of the element.
        key (str): The key to press (use Keys.ENTER, Keys.TAB, etc.).
        nth (int, optional): Index if multiple elements match (default: 0).
    """
    element = pick_element(driver, method, identifier, nth)
    if not element:
        logger.error("Could not find element %s using %s", identifier, method.name)
        return False

    try:
        element.send_keys(key)
        return True
    except WebDriverException as e:
        logger.error("Error pressing key %r on element %s: %s", key, identifier, e)
        return False


# core
def access_url(driver: WebDriver, url: str) -> bool:
    """Navigates the WebDriver to the specified URL."""
    try:
        driver.get(url)
        return True
    except WebDriverException as e:
        logger.error("Error accessing URL %r: %s", url, e)
        return False


# Picks the element that actually scrolls (LinkedIn & co. use nested panes) once,
# caches it on window, then scrolls it. Returns [scrollTop, scrollHeight].
_SCROLL_TO_BOTTOM_JS = """
let target = window.__pwtScrollTarget;
if (!target || !target.isConnected) {
    target = document.scrollingElement || document.documentElement;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
    for (let el = walker.nextNode(); el; el = walker.nextNode()) {
        if (el.scrollHeight <= el.clientHeight + 20 || el.scrollHeight <= target.scrollHeight) continue;
        const overflowY = getComputedStyle(el).overflowY;
        if (overflowY === 'auto' || overflowY === 'scroll') target = el;
    }
    window.__pwtScrollTarget = target;
}
target.scrollTop = target.scrollHeight;
if (target !== document.scrollingElement) window.scrollTo(0, document.body.scrollHeight);
return [target.scrollTop, target.scrollHeight];
"""


# core
def scroll_to_bottom(
    driver: WebDriver,
    pause: float = 0.5,
    stable_rounds: int = 2,
    max_rounds: int = 200,
    page_load_timeout: float = 10,
) -> None:
    """
    Scrolls the main scrollable container until its height stops growing.

    Args:
        pause: Seconds to wait after each scroll for lazy content to load.
        stable_rounds: Consecutive unchanged readings required to stop.
        max_rounds: Hard cap so infinite feeds don't scroll forever.
        page_load_timeout: Max seconds to wait for document.readyState == 'complete'.
    """
    try:
        WebDriverWait(driver, page_load_timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except TimeoutException:
        logger.warning("Page not fully loaded after %ss, scrolling anyway", page_load_timeout)

    last_position = None
    unchanged = 0
    for _ in range(max_rounds):
        position = driver.execute_script(_SCROLL_TO_BOTTOM_JS)
        time.sleep(pause)

        unchanged = unchanged + 1 if position == last_position else 0
        if unchanged >= stable_rounds:
            return
        last_position = position

    logger.info("scroll_to_bottom stopped after max_rounds=%d", max_rounds)


#
#
# Desktop / UI tasks: imported lazily so the Selenium-only path doesn't
# need pyautogui, keyboard or PyQt6 (nor a display) to be importable.
#
def select_file_through_window(directory_path: str, filename: str) -> None:
    from ..desktop_windows_interactions.simulate_actions import select_file_window

    select_file_window(directory_path, filename)


def wait_for_captcha_task() -> bool:
    from ..ui.captcha_wait import wait_for_captcha

    return wait_for_captcha()

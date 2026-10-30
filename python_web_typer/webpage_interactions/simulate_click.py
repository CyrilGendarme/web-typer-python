import logging

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

__all__ = ["simulate_click"]

logger = logging.getLogger(__name__)


def _click_with_mouse_events(driver: WebDriver, element: WebElement) -> None:
    ActionChains(driver).move_to_element(element).click_and_hold().release().perform()


def _click_with_focus(driver: WebDriver, element: WebElement) -> None:
    driver.execute_script("arguments[0].focus();", element)
    element.click()


def _click_with_javascript(driver: WebDriver, element: WebElement) -> None:
    driver.execute_script("arguments[0].click();", element)


# Ordered from most to least human-like
_CLICK_STRATEGIES = (
    ("mouse events", _click_with_mouse_events),
    ("focus + click", _click_with_focus),
    ("JavaScript click", _click_with_javascript),
)


def simulate_click(
    driver: WebDriver,
    element: WebElement,
    shall_scroll: bool = True,
    wait_time: float = 10,
) -> bool:
    """Simulates user interaction by dispatching click-related events."""

    # Center the element so sticky headers/footers don't intercept the click
    if shall_scroll:
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
            element,
        )

    try:
        WebDriverWait(driver, wait_time).until(EC.element_to_be_clickable(element))
    except TimeoutException:
        logger.warning("Element not clickable after %ss, trying anyway", wait_time)

    for name, strategy in _CLICK_STRATEGIES:
        try:
            strategy(driver, element)
            return True
        except WebDriverException as e:
            logger.debug("Click via %s failed: %s", name, e)

    logger.error("All click attempts have failed")
    return False

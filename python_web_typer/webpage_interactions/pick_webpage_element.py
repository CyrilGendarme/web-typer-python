import logging
from enum import Enum, auto
from typing import List, Optional, Tuple

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.support.ui import WebDriverWait

from ..config import DEFAULT_ELEMENT_WAIT_TIME

__all__ = [
    "SELECTOR_DELIMITER",
    "ElementSelectorMethod",
    "pick_elements",
    "pick_element",
    "is_element_present",
    "get_label_for_input",
]

logger = logging.getLogger(__name__)

SELECTOR_DELIMITER = "|||"


class ElementSelectorMethod(Enum):
    ID = auto()
    CLASS_NAME = auto()
    CSS_SELECTOR = auto()
    NAME = auto()
    TAG_WITH_ATTRIBUTE = auto()
    TAG_WITH_CLASS_CONTAINS = auto()
    TAG_WITH_ATTRIBUTE_CONTAINS = auto()


# ---------------------------
# Selector builders
# ---------------------------


def _build_css_from_tag_attribute(identifier: str) -> str:
    """identifier format: tag|||attribute[|||value]"""
    parts = identifier.split(SELECTOR_DELIMITER)
    tag, attribute = parts[:2]

    if len(parts) == 3:
        return f'{tag}[{attribute}="{parts[2]}"]'
    return f"{tag}[{attribute}]"


def _build_css_from_tag_class_contains(identifier: str) -> str:
    """identifier format: tag|||class_substring"""
    tag, class_substring = identifier.split(SELECTOR_DELIMITER, 1)
    return f'{tag}[class*="{class_substring}"]'


def _build_xpath_from_tag_attribute_contains(identifier: str) -> str:
    """identifier format: tag|||attribute|||substring"""
    tag, attribute, value_part = identifier.split(SELECTOR_DELIMITER, 2)
    return f'.//{tag}[contains(@{attribute}, "{value_part}")]'


_SELECTOR_RESOLVERS = {
    ElementSelectorMethod.ID: lambda i: (By.ID, i),
    ElementSelectorMethod.CLASS_NAME: lambda i: (By.CLASS_NAME, i),
    ElementSelectorMethod.CSS_SELECTOR: lambda i: (By.CSS_SELECTOR, i),
    ElementSelectorMethod.NAME: lambda i: (By.NAME, i),
    ElementSelectorMethod.TAG_WITH_ATTRIBUTE: lambda i: (
        By.CSS_SELECTOR,
        _build_css_from_tag_attribute(i),
    ),
    ElementSelectorMethod.TAG_WITH_CLASS_CONTAINS: lambda i: (
        By.CSS_SELECTOR,
        _build_css_from_tag_class_contains(i),
    ),
    ElementSelectorMethod.TAG_WITH_ATTRIBUTE_CONTAINS: lambda i: (
        By.XPATH,
        _build_xpath_from_tag_attribute_contains(i),
    ),
}


def _resolve_selector(method: ElementSelectorMethod, identifier: str) -> Tuple[str, str]:
    try:
        return _SELECTOR_RESOLVERS[method](identifier)
    except KeyError:
        raise ValueError(f"Unsupported selector method: {method}") from None


# ---------------------------
# Core element pickers
# ---------------------------


def pick_elements(
    driver: WebDriver,
    method: ElementSelectorMethod,
    identifier: str,
    wait_time: float = 0,  # seconds to wait for at least 1 element
) -> List[WebElement]:
    """
    Picks all elements matching the selector.
    If wait_time > 0, it waits until at least one element is present.
    """
    by, selector = _resolve_selector(method, identifier)

    try:
        if wait_time > 0:
            return WebDriverWait(driver, wait_time).until(
                lambda d: d.find_elements(by, selector) or False
            )
        return driver.find_elements(by, selector)
    except TimeoutException:
        logger.debug("[pick_elements] No match for %s=%r", method.name, identifier)
    except WebDriverException as e:
        logger.warning("[pick_elements] %s=%r: %s", method.name, identifier, e)
    return []


def pick_element(
    driver: WebDriver,
    method: ElementSelectorMethod,
    identifier: str,
    nth: int = 0,
    wait_time: float = DEFAULT_ELEMENT_WAIT_TIME,  # seconds to wait for element
) -> Optional[WebElement]:
    """
    Picks the nth element matching the selector.
    If wait_time > 0, it will wait until the nth element is present.
    """
    by, selector = _resolve_selector(method, identifier)

    def find_nth(d: WebDriver):
        elements = d.find_elements(by, selector)
        return elements[nth] if 0 <= nth < len(elements) else False

    try:
        if wait_time > 0:
            return WebDriverWait(driver, wait_time).until(find_nth)
        return find_nth(driver) or None
    except TimeoutException:
        logger.warning(
            "[pick_element] %s=%r (nth=%d) not found within %ss",
            method.name,
            identifier,
            nth,
            wait_time,
        )
    except WebDriverException as e:
        logger.warning("[pick_element] %s=%r: %s", method.name, identifier, e)
    return None


# ---------------------------
# Utility helpers
# ---------------------------


def is_element_present(
    driver: WebDriver,
    method: ElementSelectorMethod,
    identifier: str,
    nth: int = 0,
    wait_time: float = 0,
) -> bool:
    return pick_element(driver, method, identifier, nth, wait_time) is not None


def get_label_for_input(
    driver: WebDriver,
    input_element: WebElement,
) -> Optional[WebElement]:
    try:
        input_id = input_element.get_attribute("id")
        if not input_id:
            return None

        return driver.find_element(By.CSS_SELECTOR, f'label[for="{input_id}"]')

    except WebDriverException as e:
        logger.debug("[get_label_for_input] %s", e)
        return None

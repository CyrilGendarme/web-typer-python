from enum import Enum, auto
from typing import List, Optional, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

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
    parts = identifier.split(SELECTOR_DELIMITER)
    tag, attribute = parts[:2]

    if len(parts) == 3:
        return f'{tag}[{attribute}="{parts[2]}"]'
    return f"{tag}[{attribute}]"


def _build_css_from_tag_class_contains(identifier: str) -> str:
    tag, class_substring = identifier.split(SELECTOR_DELIMITER, 1)
    return f'{tag}[class*="{class_substring}"]'


def _build_xpath_from_tag_attribute_contains(identifier: str) -> str:
    """
    identifier format:
    tag|||attribute|||substring
    """
    tag, attribute, value_part = identifier.split(SELECTOR_DELIMITER, 2)
    return f'.//{tag}[contains(@{attribute}, "{value_part}")]'


def _resolve_selector(
    method: ElementSelectorMethod, identifier: str
) -> Tuple[By, str, bool]:
    """
    Returns (By, selector, single_element_only)
    """
    if method == ElementSelectorMethod.ID:
        return By.ID, identifier, True

    if method == ElementSelectorMethod.CLASS_NAME:
        return By.CLASS_NAME, identifier, False

    if method == ElementSelectorMethod.CSS_SELECTOR:
        return By.CSS_SELECTOR, identifier, False

    if method == ElementSelectorMethod.NAME:
        return By.NAME, identifier, False

    if method == ElementSelectorMethod.TAG_WITH_ATTRIBUTE:
        return By.CSS_SELECTOR, _build_css_from_tag_attribute(identifier), False

    if method == ElementSelectorMethod.TAG_WITH_CLASS_CONTAINS:
        return By.CSS_SELECTOR, _build_css_from_tag_class_contains(identifier), False

    if method == ElementSelectorMethod.TAG_WITH_ATTRIBUTE_CONTAINS:
        return (
            By.XPATH,
            _build_xpath_from_tag_attribute_contains(identifier),
            False,
        )

    raise ValueError(f"Unsupported selector method: {method}")


# ---------------------------
# Core element pickers
# ---------------------------


def pick_elements(
    driver: WebDriver,
    method: ElementSelectorMethod,
    identifier: str,
    wait_time: int = 0,  # seconds to wait for at least 1 element
) -> List[WebElement]:
    """
    Picks all elements matching the selector.
    If wait_time > 0, it waits until at least one element is present.
    """
    by, selector, single = _resolve_selector(method, identifier)

    if wait_time > 0:
        try:

            def find_elements_present(driver):
                elems = driver.find_elements(by, selector)
                return elems if elems else False

            return WebDriverWait(driver, wait_time).until(find_elements_present)
        except Exception as e:
            print(f"[pick_elements wait] {method.name}: {e}")
            return []

    # fallback: immediate pick
    try:
        if single:
            element = driver.find_element(by, selector)
            return [element] if element else []
        return driver.find_elements(by, selector)
    except Exception as e:
        print(f"[pick_elements] {method.name}: {e}")
        return []


def pick_element(
    driver: WebDriver,
    method: ElementSelectorMethod,
    identifier: str,
    nth: int = 0,
    wait_time: int = 10,  # seconds to wait for element to appear
) -> Optional[WebElement]:
    """
    Picks the nth element matching the selector.
    If wait_time > 0, it will wait until the element is present.
    """
    if wait_time > 0:
        by, selector, single = _resolve_selector(method, identifier)
        try:

            def find_nth(driver):
                elements = driver.find_elements(by, selector)
                if 0 <= nth < len(elements):
                    return elements[nth]
                return False  # keep waiting

            element = WebDriverWait(driver, wait_time).until(find_nth)
            return element

        except Exception as e:
            print(f"[pick_element wait] {method.name}: {e}")
            return None

    # fallback: immediate pick without wait
    elements = pick_elements(driver, method, identifier)
    if 0 <= nth < len(elements):
        return elements[nth]

    if elements:
        print(f"[pick_element] Index {nth} out of bounds (found {len(elements)})")
    return None


# ---------------------------
# Utility helpers
# ---------------------------


def is_element_present(
    driver: WebDriver,
    method: ElementSelectorMethod,
    identifier: str,
    nth: int = 0,
) -> bool:
    return pick_element(driver, method, identifier, nth) is not None


def get_label_for_input(
    driver: WebDriver,
    input_element: WebElement,
) -> Optional[WebElement]:
    try:
        input_id = input_element.get_attribute("id")
        if not input_id:
            return None

        return driver.find_element(By.CSS_SELECTOR, f'label[for="{input_id}"]')

    except Exception as e:
        print(f"[get_label_for_input] {e}")
        return None

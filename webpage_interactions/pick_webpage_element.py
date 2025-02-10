from enum import Enum, auto
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from typing import List, Optional


# Enum to allow generic func instead of code duplication in extending scripts
class ElementSelectorMethod(Enum):
    ID = auto()
    CLASS_NAME = auto()
    CSS_SELECTOR = auto()
    NAME = auto()


def pick_element(
    driver: WebDriver, method: ElementSelectorMethod, identifier: str, nth: int = 0
) -> Optional[WebElement]:
    """
    Picks a WebElement using a specified selection method.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
        method (ElementSelectorMethod): The method to use (ID, CLASS_NAME, CSS_SELECTOR, NAME).
        identifier (str): The value used for element lookup.
        nth (int, optional): The index for CLASS_NAME-based selection (default 0).

    Returns:
        WebElement | None: The found element or None if not found.
    """
    try:

        if method.value == ElementSelectorMethod.ID.value:
            return pick_element_by_id(driver, identifier)
        elif method.value == ElementSelectorMethod.CLASS_NAME.value:
            return pick_element_by_class(driver, identifier, nth)
        elif method.value == ElementSelectorMethod.CSS_SELECTOR.value:
            return pick_element_by_css_selector(driver, identifier, nth)
        elif method.value == ElementSelectorMethod.NAME.value:
            return pick_element_by_name(driver, identifier)
        else:
            print(f"Method {method} is not supported in pick_element func")
            return None
    except Exception as e:
        print(f"Error finding element with {method.value}: {e}")
        return None


def pick_elements(
    driver: WebDriver, method: ElementSelectorMethod, identifier: str
) -> List[WebElement]:
    """
    Picks multiple WebElements using a specified selection method.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
        method (ElementSelectorMethod): The method to use (ID, CLASS_NAME, CSS_SELECTOR, NAME).
        identifier (str): The value used for element lookup.

    Returns:
        List[WebElement]: A list of found elements.
    """
    # FIXME: to be refactored when required
    pass

    # try:
    #     if method == ElementSelectorMethod.CLASS_NAME:
    #         return driver.find_elements(By.CLASS_NAME, identifier)
    #     elif method == ElementSelectorMethod.CSS_SELECTOR:
    #         return driver.find_elements(By.CSS_SELECTOR, identifier)
    #     else:
    #         print(f"Method {method} does not support multiple elements")
    #         return []
    # except Exception as e:
    #     print(f"Error finding elements with {method.value}: {e}")
    #     return []


def pick_element_by_id(driver: WebDriver, element_id: str) -> WebElement:
    """
    Picks a WebElement by its ID.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
        element_id (str): The ID of the element to retrieve.

    Returns:
        WebElement: The element with the specified ID.
    """
    try:
        element = driver.find_element(By.ID, element_id)
        return element
    except Exception as e:
        print(f"Error finding element by ID: {e}")
        return None


def pick_element_by_class(
    driver: WebDriver, class_name: str, nth: int = 0
) -> WebElement:
    """
    Picks the n-th WebElement by its class name.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
        class_name (str): The class name of the element to retrieve.
        nth (int): The index of the element (default is 0 for the first element).

    Returns:
        WebElement: The n-th element with the specified class name.
    """
    try:
        elements = driver.find_elements(By.CLASS_NAME, class_name)
        if 0 <= nth < len(elements):
            return elements[nth]
        else:
            print(
                f"Error: The n-th index {nth} is out of bounds for elements with class '{class_name}'"
            )
            return None
    except Exception as e:
        print(f"Error finding element by class name: {e}")
        return None


def pick_element_by_css_selector(
    driver: WebDriver, css_selector: str, nth: int = 0
) -> WebElement:
    """
    Picks the n-th WebElement by its CSS selector.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
        css_selector (str): The CSS selector of the element to retrieve.
        nth (int): The index of the element (default is 0 for the first element).

    Returns:
        WebElement: The n-th element matching the specified CSS selector.
    """
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, css_selector)
        if 0 <= nth < len(elements):
            return elements[nth]
        else:
            print(
                f"Error: The n-th index {nth} is out of bounds for elements with CSS selector '{css_selector}'"
            )
            return None
    except Exception as e:
        print(f"Error finding element by CSS selector: {e}")
        return None


def pick_element_by_name(driver: WebDriver, name: str) -> WebElement:
    """Pick an element by its name."""
    try:
        element = driver.find_element(By.NAME, name)
        return element
    except Exception as e:
        print(f"Error finding element by name: {e}")
        return None


def is_element_present(
    driver: WebDriver, method: ElementSelectorMethod, identifier: str, nth: int = 0
) -> bool:
    """
    Checks if a WebElement exists on the page using the specified selection method.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
        method (ElementSelectorMethod): The method to use (ID, CLASS_NAME, CSS_SELECTOR, NAME).
        identifier (str): The value used for element lookup.
        nth (int, optional): The index for CLASS_NAME-based selection (default 0).

    Returns:
        bool: True if the element exists, False otherwise.
    """
    try:
        element = pick_element(driver, method, identifier, nth)
        if element is not None:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error checking for element with {method.value}: {e}")
        return False

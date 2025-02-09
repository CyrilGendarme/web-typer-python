from enum import Enum
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from typing import List, Optional


# Enum to allow generic func instead of code duplication in extending scripts
class ElementSelector(Enum):
    ID = "id"
    CLASS_NAME = "class_name"
    CSS_SELECTOR = "css_selector"
    NAME = "name"


def pick_element(
    driver: WebDriver, method: ElementSelector, identifier: str, nth: int = 0
) -> Optional[WebElement]:
    """
    Picks a WebElement using a specified selection method.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
        method (ElementSelector): The method to use (ID, CLASS_NAME, CSS_SELECTOR, NAME).
        identifier (str): The value used for element lookup.
        nth (int, optional): The index for CLASS_NAME-based selection (default 0).

    Returns:
        WebElement | None: The found element or None if not found.
    """
    try:
        if method == ElementSelector.ID:
            return driver.find_element(By.ID, identifier)
        elif method == ElementSelector.CLASS_NAME:
            elements = driver.find_elements(By.CLASS_NAME, identifier)
            return elements[nth] if 0 <= nth < len(elements) else None
        elif method == ElementSelector.CSS_SELECTOR:
            return driver.find_element(By.CSS_SELECTOR, identifier)
        elif method == ElementSelector.NAME:
            return driver.find_element(By.NAME, identifier)
    except Exception as e:
        print(f"Error finding element with {method.value}: {e}")
        return None


def pick_elements(
    driver: WebDriver, method: ElementSelector, identifier: str
) -> List[WebElement]:
    """
    Picks multiple WebElements using a specified selection method.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
        method (ElementSelector): The method to use (ID, CLASS_NAME, CSS_SELECTOR, NAME).
        identifier (str): The value used for element lookup.

    Returns:
        List[WebElement]: A list of found elements.
    """
    try:
        if method == ElementSelector.CLASS_NAME:
            return driver.find_elements(By.CLASS_NAME, identifier)
        elif method == ElementSelector.CSS_SELECTOR:
            return driver.find_elements(By.CSS_SELECTOR, identifier)
        else:
            print(f"Method {method} does not support multiple elements")
            return []
    except Exception as e:
        print(f"Error finding elements with {method.value}: {e}")
        return []


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


def pick_elements_by_class_filter(
    driver: WebDriver, class_name: str, condition_func
) -> List[WebElement]:
    """
    Picks a list of WebElements by class name and filters them based on a condition.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
        class_name (str): The class name of the elements to retrieve.
        condition_func (function): A function that takes a WebElement and returns True if the element satisfies the condition.

    Returns:
        List[WebElement]: A list of elements that satisfy the condition.
    """
    try:
        elements = driver.find_elements(By.CLASS_NAME, class_name)
        filtered_elements = [element for element in elements if condition_func(element)]
        return filtered_elements
    except Exception as e:
        print(f"Error finding and filtering elements by class name: {e}")
        return []


def pick_element_by_css_selector(driver: WebDriver, css_selector: str) -> WebElement:
    """
    Picks a WebElement by its CSS selector.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
        css_selector (str): The CSS selector of the element to retrieve.

    Returns:
        WebElement: The element matching the specified CSS selector.
    """
    try:
        element = driver.find_element(By.CSS_SELECTOR, css_selector)
        return element
    except Exception as e:
        print(f"Error finding element by CSS selector: {e}")
        return None


def pick_elements_by_css_selector(
    driver: WebDriver, css_selector: str
) -> List[WebElement]:
    """
    Picks a list of WebElements by their CSS selector.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
        css_selector (str): The CSS selector of the elements to retrieve.

    Returns:
        List[WebElement]: A list of elements matching the specified CSS selector.
    """
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, css_selector)
        return elements
    except Exception as e:
        print(f"Error finding elements by CSS selector: {e}")
        return []


def pick_element_by_name(driver: WebDriver, name: str) -> WebElement:
    """Pick an element by its name."""
    return driver.find_element(By.NAME, name)

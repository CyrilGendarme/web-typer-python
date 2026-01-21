from enum import Enum, auto
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from typing import List, Optional

SELECTOR_DELIMITER = "|||"


# Enum to allow generic func instead of code duplication in extending scripts
class ElementSelectorMethod(Enum):
    ID = auto()
    CLASS_NAME = auto()
    CSS_SELECTOR = auto()
    NAME = auto()
    TAG_WITH_ATTRIBUTE = auto()
    TAG_WITH_CLASS_CONTAINS = auto()


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
        elif method.value == ElementSelectorMethod.TAG_WITH_ATTRIBUTE.value:
            return pick_element_by_tag_attribute(driver, identifier, nth)
        elif method.value == ElementSelectorMethod.TAG_WITH_CLASS_CONTAINS.value:
            # identifier format: tag|||class_substring
            elements = pick_elements_by_tag_class_contains(driver, identifier)
            if 0 <= nth < len(elements):
                return elements[nth]

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
        method (ElementSelectorMethod): The method to use (ID, CLASS_NAME, CSS_SELECTOR, NAME, TAG_WITH_ATTRIBUTE).
        identifier (str): The value used for element lookup.

    Returns:
        List[WebElement]: A list of found elements. Empty if none found or method unsupported.
    """
    try:
        if method.value == ElementSelectorMethod.ID.value:
            # Only one element possible by ID
            element = pick_element_by_id(driver, identifier)
            return [element] if element else []

        elif method.value == ElementSelectorMethod.CLASS_NAME.value:
            return driver.find_elements(By.CLASS_NAME, identifier)

        elif method.value == ElementSelectorMethod.CSS_SELECTOR.value:
            return driver.find_elements(By.CSS_SELECTOR, identifier)

        elif method.value == ElementSelectorMethod.NAME.value:
            return driver.find_elements(By.NAME, identifier)

        elif method.value == ElementSelectorMethod.TAG_WITH_ATTRIBUTE.value:
            # identifier format: tag|||attribute|||value or tag|||attribute
            parts = identifier.split(SELECTOR_DELIMITER)
            tag = parts[0]
            attribute = parts[1]
            css = ""

            if len(parts) == 3:
                value = parts[2]
                css = f'{tag}[{attribute}="{value}"]'
            else:
                css = f"{tag}[{attribute}]"  # attribute exists, value ignored
            try:
                return driver.find_elements(By.CSS_SELECTOR, css)
            except ValueError:
                print(
                    f"Error: Invalid format for TAG_WITH_ATTRIBUTE. "
                    f"Expected 'tag{SELECTOR_DELIMITER}attribute{SELECTOR_DELIMITER}value', got '{identifier}'"
                )
                return []

        elif method.value == ElementSelectorMethod.TAG_WITH_CLASS_CONTAINS.value:
            # identifier format: tag|||class_substring
            return pick_elements_by_tag_class_contains(driver, identifier)

        else:
            print(f"Method {method} is not supported in pick_elements func")
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
        print(f"element_id: {element_id}")

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


def pick_element_by_tag_attribute(
    driver: WebDriver,
    selector: str,
    nth: int = 0,
) -> Optional[WebElement]:
    """
    Picks the n-th element by tag name with a specific attribute/value.

    Example CSS produced:
        input[type="password"]
    """

    # identifier format: tag|||attribute|||value or tag|||attribute
    parts = selector.split(SELECTOR_DELIMITER)
    tag = parts[0]
    attribute = parts[1]
    css = ""

    if len(parts) == 3:
        value = parts[2]
        css = f'{tag}[{attribute}="{value}"]'
    else:
        css = f"{tag}[{attribute}]"  # attribute exists, value ignored

    try:
        elements = driver.find_elements(By.CSS_SELECTOR, css)

        if 0 <= nth < len(elements):
            return elements[nth]

        print(
            f"Error: Index {nth} out of bounds for selector {css} "
            f"(found {len(elements)} elements)"
        )
        return None

    except Exception as e:
        print(f"Error finding element by tag+attribute: {e}")
        return None


def pick_elements_by_tag_class_contains(
    driver: WebDriver,
    identifier: str,
) -> List[WebElement]:
    """
    Picks all elements of a given tag whose class attribute contains a substring.

    Example CSS:
        input[class*="error-field"]
        select[class*="error-field"]
    """
    parts = identifier.split(SELECTOR_DELIMITER)
    tag = parts[0]
    class_substring = parts[1]

    css = f'{tag}[class*="{class_substring}"]'
    try:
        return driver.find_elements(By.CSS_SELECTOR, css)
    except Exception as e:
        print(f"Error finding elements by tag + class contains: {e}")
        return []


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


def get_label_for_input(driver, input_element: WebElement) -> Optional[WebElement]:
    """
    Retrieves the <label> associated with an <input> element.

    Uses the standard HTML 'for' -> 'id' relationship.

    Args:
        driver: Selenium WebDriver
        input_element: The input WebElement

    Returns:
        WebElement | None: The associated label if found
    """
    try:
        input_id = input_element.get_attribute("id")
        if not input_id:
            print("Input element has no id attribute")
            return None

        return driver.find_element(By.CSS_SELECTOR, f'label[for="{input_id}"]')

    except Exception as e:
        print(f"Error finding label for input: {e}")
        return None

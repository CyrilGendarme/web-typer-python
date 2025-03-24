import os
import sys
import time
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

from webpage_interactions.simulate_typing import simulate_typing
from webpage_interactions.pick_webpage_element import (
    ElementSelectorMethod,
    pick_element_by_class,
    pick_element_by_css_selector,
    pick_element_by_id,
    pick_element_by_name,
    pick_element,
)
from webpage_interactions.simulate_click import simulate_click


#
#
# Here are the core functions
#
def click_element(
    driver: WebDriver, method: ElementSelectorMethod, identifier: str, nth: int = 0
):
    """
    Clicks on a webpage element based on the specified selection method.

    Args:
        driver (WebDriver): Selenium WebDriver instance.
        method (ElementSelectorMethod): The method used to locate the element (Enum value).
        identifier (str): The actual value for the selected method (ID, class, CSS selector, etc.).
        nth (int, optional): Index of the element if multiple exist (default is 0).

    Returns:
        None: Clicks the element if found, otherwise prints an error message.
    """
    element = pick_element(driver, method, identifier, nth)
    if element:
        simulate_click(driver, element)
    else:
        print(f"Could not find element {identifier} using {method.name}")


# core
def type_into_element(
    driver: WebDriver,
    method: ElementSelectorMethod,
    identifier: str,
    text: str,
    nth: int = 0,
):
    """
    Finds a webpage element and types the given text into it.

    Args:
        driver (WebDriver): Selenium WebDriver instance.
        method (ElementSelectorMethod): The method used to locate the element (Enum value).
        identifier (str): The actual value for the selected method (ID, class, CSS selector, etc.).
        text (str): The text to be typed into the selected element.
        nth (int, optional): Index of the element if multiple exist (default is 0).

    Returns:
        None: Types the given text if the element is found, otherwise prints an error message.
    """
    element = pick_element(driver, method, identifier, nth)
    if element:
        simulate_typing(driver, element, text)
    else:
        print(f"Could not find element {identifier} using {method.name}")


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
):
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

    # Locate elements
    file_input = pick_element(
        driver, method_file_input, file_input_selector, nth_file_input
    )
    drop_zone = pick_element(
        driver, method_drop_zone, drop_zone_selector, nth_drop_zone
    )

    if not file_input:
        print(
            f"Error: File input element not found using {method_file_input} - {file_input_selector}"
        )
        return

    if not drop_zone:
        print(
            f"Warning: Drop zone element not found using {method_drop_zone} - {drop_zone_selector}"
        )
        print("Proceeding with direct file input upload.")

    # Send file to hidden input
    file_input.send_keys(file_path)

    # If drop zone exists, attempt a visual drag-and-drop
    if drop_zone:
        try:
            action = ActionChains(driver)
            action.click_and_hold(file_input).move_to_element(
                drop_zone
            ).release().perform()
            print("Drag-and-drop simulation executed.")
        except Exception as e:
            print(f"Drag-and-drop action failed: {e}")

    print("File upload process completed.")


# core
def sleep(delay):
    time.sleep(delay)


#
#
# Example in local main, kept to make it work but we prefer generic stuff
#
def click_cookie_btn(driver):

    # click_element(driver, ElementSelectorMethod.ID, "L2AGLb")

    cookie_btn = pick_element_by_id(driver, "L2AGLb")
    if not cookie_btn:
        print("Cookie button not found!")
        return
    simulate_click(driver, cookie_btn)


# example
def type_and_click_in_search(driver, text):

    # type_into_element(driver, ElementSelectorMethod.NAME, "q", text)
    # click_element(driver, ElementSelectorMethod.CLASS_NAME, "gNO89b")

    search_box = pick_element_by_name(driver, "q")
    if not search_box:
        print("Search box not found!")
        return
    simulate_typing(driver, search_box, text)

    search_btn = pick_element_by_class(driver, "gNO89b")
    if not search_btn:
        print("Search button not found!")
        return
    simulate_click(driver, search_btn)


# example
def click_on_first_result(driver):

    # click_element(driver, ElementSelectorMethod.CSS_SELECTOR, "h3", 0)

    first_result = pick_element_by_css_selector(driver, "h3")
    if not first_result:
        print("First search result not found!")
        return
    print(f"Clicking on: {first_result.text}")
    simulate_click(driver, first_result)

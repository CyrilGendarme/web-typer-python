## This is open to extension for project-specific stuff


import os
import sys
import time
from selenium.webdriver.remote.webdriver import WebDriver

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

from webpage_interactions.simulate_typing import simulate_typing
from webpage_interactions.pick_webpage_element import (
    ElementSelector,
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
    driver: WebDriver, method: ElementSelector, identifier: str, nth: int = 0
):
    """
    Clicks on a webpage element based on the specified selection method.

    Args:
        driver (WebDriver): Selenium WebDriver instance.
        method (ElementSelector): The method used to locate the element (Enum value).
        identifier (str): The actual value for the selected method (ID, class, CSS selector, etc.).
        nth (int, optional): Index of the element if multiple exist (default is 0).

    Returns:
        None: Clicks the element if found, otherwise prints an error message.
    """
    element = pick_element(driver, method.value, identifier, nth)
    if element:
        simulate_click(driver, element)
    else:
        print(f"Could not find element {identifier} using {method.name}")


# core
def type_into_element(
    driver: WebDriver, method: ElementSelector, identifier: str, text: str, nth: int = 0
):
    """
    Finds a webpage element and types the given text into it.

    Args:
        driver (WebDriver): Selenium WebDriver instance.
        method (ElementSelector): The method used to locate the element (Enum value).
        identifier (str): The actual value for the selected method (ID, class, CSS selector, etc.).
        text (str): The text to be typed into the selected element.
        nth (int, optional): Index of the element if multiple exist (default is 0).

    Returns:
        None: Types the given text if the element is found, otherwise prints an error message.
    """
    element = pick_element(driver, method.value, identifier, nth)
    if element:
        simulate_typing(driver, element, text)
    else:
        print(f"Could not find element {identifier} using {method.name}")


# core
def sleep(delay):
    time.sleep(delay)


#
#
# Example in local main, kept to make it work but we prefer generic stuff
#
def click_cookie_btn(driver):

    # click_element(driver, ElementSelector.ID, "L2AGLb")

    cookie_btn = pick_element_by_id(driver, "L2AGLb")
    if not cookie_btn:
        print("Cookie button not found!")
        return
    simulate_click(driver, cookie_btn)


# example
def type_and_click_in_search(driver, text):

    # type_into_element(driver, ElementSelector.NAME, "q", text)
    # click_element(driver, ElementSelector.CLASS_NAME, "gNO89b")

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

    # click_element(driver, ElementSelector.CSS_SELECTOR, "h3", 0)

    first_result = pick_element_by_css_selector(driver, "h3")
    if not first_result:
        print("First search result not found!")
        return
    print(f"Clicking on: {first_result.text}")
    simulate_click(driver, first_result)

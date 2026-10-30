"""Google search demo tasks used by main.py. Prefer the generic tasks in tasks.py."""

from selenium.webdriver.remote.webdriver import WebDriver

from ..webpage_interactions.pick_webpage_element import ElementSelectorMethod
from .tasks import click_element, type_into_element

__all__ = ["click_cookie_btn", "type_and_click_in_search", "click_on_first_result"]


def click_cookie_btn(driver: WebDriver) -> bool:
    return click_element(driver, ElementSelectorMethod.ID, "L2AGLb")


def type_and_click_in_search(driver: WebDriver, text: str) -> bool:
    return type_into_element(
        driver, ElementSelectorMethod.NAME, "q", text
    ) and click_element(driver, ElementSelectorMethod.CLASS_NAME, "gNO89b")


def click_on_first_result(driver: WebDriver) -> bool:
    return click_element(driver, ElementSelectorMethod.CSS_SELECTOR, "h3")

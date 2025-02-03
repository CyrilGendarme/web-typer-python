import os
import sys
import time
import threading
from selenium import webdriver
from PyQt6.QtWidgets import QApplication
from selenium.webdriver.remote.webdriver import WebDriver

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

# Import the provided functions
from pick_webdriver import get_headless_webdriver
from simulate_typing import simulate_typing
from simulate_click import simulate_click
from mutation_observer import observe_dom_changes, observe_dom_changes_with_trigger
from pick_webpage_element import (
    pick_element_by_id,
    pick_element_by_class,
    pick_elements_by_class_filter,
    pick_element_by_css_selector,
    pick_elements_by_css_selector,
    pick_element_by_name,
)
from vars.config import DEBUG_DELAY
from mutation_observer import observe_dom_changes_with_trigger
from ui.captcha_wait import wait_for_captcha


def func_1(driver: WebDriver):
    cookie_btn = pick_element_by_id(driver, "L2AGLb")
    if not cookie_btn:
        print("Cookie button not found!")
        return
    simulate_click(driver, cookie_btn)


def func_2(driver: WebDriver):
    search_box = pick_element_by_name(driver, "q")
    if not search_box:
        print("Search box not found!")
        return
    simulate_typing(driver, search_box, "Selenium WebDriver Python")


def func_3(driver: WebDriver):
    search_btn = pick_element_by_class(driver, "gNO89b")
    if not search_btn:
        print("Search button not found!")
        return
    simulate_click(driver, search_btn)


def func_4(driver: WebDriver):
    first_result = pick_element_by_css_selector(driver, "h3")
    if not first_result:
        print("First search result not found!")
        return
    print(f"Clicking on: {first_result.text}")
    simulate_click(driver, first_result)

    time.sleep(DEBUG_DELAY)

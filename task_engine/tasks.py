## This is open to extension for project-specific stuff


import os
import sys
import time

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

from webpage_interactions.simulate_typing import simulate_typing
from webpage_interactions.pick_webpage_element import (
    pick_element_by_class,
    pick_element_by_css_selector,
    pick_element_by_id,
    pick_element_by_name,
)
from webpage_interactions.simulate_click import simulate_click


def sleep(delay):
    time.sleep(delay)


def click_cookie_btn(driver):
    cookie_btn = pick_element_by_id(driver, "L2AGLb")
    if not cookie_btn:
        print("Cookie button not found!")
        return
    simulate_click(driver, cookie_btn)


def type_and_click_in_search(driver, text):
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


def click_on_first_result(driver):
    first_result = pick_element_by_css_selector(driver, "h3")
    if not first_result:
        print("First search result not found!")
        return
    print(f"Clicking on: {first_result.text}")
    simulate_click(driver, first_result)

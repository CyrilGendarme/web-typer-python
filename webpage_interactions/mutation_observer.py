import os
import sys
import time
import threading
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(root_dir)

from web_typer_python.config import MUTATION_OBSERVER_BASE_POLL_INTERVAL
import task_engine.tasks_queue as task_engine
from task_engine.enums_and_mappings import UiToShow


def observe_dom_changes_with_trigger(
    driver: WebDriver,
    watched_classes: list,
    watched_ids: list,
    target_selector: str = "body",
    ui_interaction_queue: task_engine.TasksQueue = None,
    poll_interval: float = MUTATION_OBSERVER_BASE_POLL_INTERVAL,
) -> None:
    previous_html = None

    while True:
        time.sleep(poll_interval)

        try:
            # print("******* Checking for DOM changes...")

            # Get the target element and compare the HTML
            target_element = driver.find_element(By.CSS_SELECTOR, target_selector)
            current_html = target_element.get_attribute("outerHTML")

            if current_html != previous_html:
                # print("DOM has changed!")
                executed = False

                for class_name in watched_classes:
                    try:
                        if driver.find_element(By.CLASS_NAME, class_name):
                            print(f"Element with class '{class_name}' detected!")
                            # Emit a pseudo-signal
                            ui_interaction_queue.add_task(
                                UiToShow.CAPTCHA, check_duplicate=True
                            )
                            executed = True
                            break

                    except NoSuchElementException:
                        continue

                if not executed:
                    for id in watched_ids:
                        try:
                            if driver.find_element(By.ID, id):
                                print(f"Element with id '{id}' detected!")
                                # Emit a pseudo-signal
                                ui_interaction_queue.add_task(
                                    UiToShow.CAPTCHA, check_duplicate=True
                                )
                                break

                        except NoSuchElementException:
                            continue

                # Update previous HTML state
                previous_html = current_html

        except StaleElementReferenceException:
            print("StaleElementReferenceException: Re-locating target element...")
            continue
        except Exception as e:
            print(f"Error while observing DOM: {e}")

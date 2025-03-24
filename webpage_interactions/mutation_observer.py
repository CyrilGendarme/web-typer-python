import os
import sys
import time
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(root_dir)

from config import MUTATION_OBSERVER_BASE_POLL_INTERVAL
from submodules.python_task_queue_scheduler.tasks_queue import TasksQueue
from task_engine_extension.enums_and_mappings import UiToShow


import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.remote.webdriver import WebDriver


def observe_dom_changes_with_trigger(
    driver: WebDriver,
    watched_classes: list = [],
    watched_ids: list = [],
    watched_inner_text: list = [],
    watched_any_content_in_html: list = [],
    target_selector: str = "body",
    task_queue: TasksQueue = None,
    poll_interval: float = MUTATION_OBSERVER_BASE_POLL_INTERVAL,
    task_enum=None,
    task_args: list = [],
    task_to_top: bool = False,
) -> None:
    previous_html = None

    while True:

        # Thread killing sequence if the driver is closed
        if not driver.title:
            print(f"no driver.title")
            try:
                driver.quit()
            except:
                pass
            sys.exit(0)

        target_element = driver.find_element(By.CSS_SELECTOR, target_selector)
        current_html = target_element.get_attribute("outerHTML")

        if current_html != previous_html:

            trigger_detected = False

            for class_name in watched_classes:
                try:
                    if driver.find_element(By.CLASS_NAME, class_name):
                        print(
                            f"[DOM OBSERVER] Element with class '{class_name}' detected!"
                        )
                        trigger_detected = True
                        break
                except NoSuchElementException:
                    continue

            if not trigger_detected:
                for element_id in watched_ids:
                    try:
                        if driver.find_element(By.ID, element_id):
                            print(
                                f"[DOM OBSERVER] Element with id '{element_id}' detected!"
                            )
                            trigger_detected = True
                            break
                    except NoSuchElementException:
                        continue

            if not trigger_detected and watched_inner_text:
                for text_snippet in watched_inner_text:
                    if text_snippet in target_element.text:
                        print(
                            f"[DOM OBSERVER] Text snippet '{text_snippet}' found in inner text!"
                        )
                        trigger_detected = True
                        break

            if not trigger_detected and watched_any_content_in_html:
                for content_snippet in watched_any_content_in_html:
                    if content_snippet in current_html:
                        print(
                            f"[DOM OBSERVER] Snippet '{content_snippet}' found in HTML content!"
                        )
                        trigger_detected = True
                        break

            if trigger_detected:
                if task_queue:
                    task_queue.add_task(
                        task_enum=task_enum,
                        args=task_args,
                        check_duplicate=True,
                        add_to_top=task_to_top,
                    )
                else:
                    print("[DOM OBSERVER] Action triggered! (No queue provided)")

            # Update the HTML snapshot
            previous_html = current_html

        # except StaleElementReferenceException:
        #     print(
        #         "[DOM OBSERVER] StaleElementReferenceException: Re-locating target element..."
        #     )
        #     continue
        # except Exception as e:
        #     print(f"[DOM OBSERVER] Thread will exit - Error while observing DOM: {e}")

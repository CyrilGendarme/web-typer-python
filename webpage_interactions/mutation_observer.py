import os
import time
import threading
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)
from ui.captcha_wait import captcha_handler  # Import the signal handler


def observe_dom_changes_with_trigger(
    driver: WebDriver,
    watched_classes: list,
    watched_ids: list,
    target_selector: str = "body",
    poll_interval: float = 1.0,
) -> None:
    previous_html = None

    while True:
        time.sleep(poll_interval)

        try:
            print("******* Checking for DOM changes...")

            # Get the target element and compare the HTML
            target_element = driver.find_element(By.CSS_SELECTOR, target_selector)
            current_html = target_element.get_attribute("outerHTML")

            if current_html != previous_html:
                print("DOM has changed!")

                for class_name in watched_classes:
                    try:
                        # Try finding an element with the class name
                        if driver.find_element(By.CLASS_NAME, class_name):
                            print(f"Element with class '{class_name}' detected!")

                            # Emit a signal to notify the main thread
                            captcha_handler.captcha_triggered.emit()  # This triggers the popup in the main thread
                            break  # Stop checking other classes for this iteration

                    except NoSuchElementException:
                        continue

                # Update previous HTML state
                previous_html = current_html

        except StaleElementReferenceException:
            print("StaleElementReferenceException: Re-locating target element...")
            continue
        except Exception as e:
            print(f"Error while observing DOM: {e}")

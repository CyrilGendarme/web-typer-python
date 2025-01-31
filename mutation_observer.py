import os
import time
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


def observe_dom_changes(
    driver: WebDriver, target_selector: str = "body", poll_interval: float = 1.0
) -> None:
    target_element = driver.find_element(By.CSS_SELECTOR, target_selector)

    # Initial state
    previous_html = target_element.get_attribute("outerHTML")

    while True:
        time.sleep(poll_interval)  # Poll every 'poll_interval' seconds

        try:
            current_html = target_element.get_attribute("outerHTML")

            if current_html != previous_html:
                print("DOM has changed!")

                # Check for added/removed elements
                if len(current_html) > len(previous_html):
                    print("A child node has been added.")
                elif len(current_html) < len(previous_html):
                    print("A child node has been removed.")

                previous_html = current_html  # Update the previous state

        except Exception as e:
            print(f"Error while observing DOM: {e}")


import threading
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)


def observe_dom_changes_with_trigger(
    driver: WebDriver,
    watched_classes: list,
    watched_ids: list,
    trigger_action=None,
    target_selector: str = "body",
    poll_interval: float = 1.0,
    stop_event: threading.Event = None,
) -> None:
    previous_html = None  # Store the last known state of the DOM

    while True:
        time.sleep(poll_interval)  # Poll every 'poll_interval' seconds

        try:
            print("******* Checking for DOM changes...")

            # Re-locate the target element on every iteration to prevent stale references
            target_element = driver.find_element(By.CSS_SELECTOR, target_selector)

            # Get the current state of the element's HTML
            current_html = target_element.get_attribute("outerHTML")
            print(f"Current HTML: {current_html[:100]}...")

            # Check if the DOM has changed
            if current_html != previous_html:
                print("DOM has changed!")  # This should now print correctly

                # Check for the presence of watched classes
                for class_name in watched_classes:
                    try:
                        if driver.find_element(By.CLASS_NAME, class_name):
                            print(f"Element with class '{class_name}' detected!")

                            if trigger_action:
                                print("Triggering captcha resolution action...")
                                stop_event.set()  # Pause main execution
                                print("DEBUG 1")
                                trigger_action_result = trigger_action()
                                print("DEBUG 2")

                                # Wait until captcha is resolved
                                while trigger_action_result is None:
                                    print("DEBUG 3")

                                    print("Waiting for user resolution...")
                                    time.sleep(1)
                                    trigger_action_result = trigger_action()
                                    print("DEBUG 1")

                                if trigger_action_result is False:
                                    print(
                                        "Stopping execution due to failed captcha action."
                                    )
                                    os._exit(1)

                                stop_event.clear()  # Resume main execution
                            else:
                                print("No action provided. Skipping.")

                            break  # Stop checking other classes for this iteration
                    except NoSuchElementException:
                        continue  # If element is not found, keep checking

                # Check for the presence of watched IDs
                for element_id in watched_ids:
                    try:
                        captcha_element = driver.find_element(By.ID, element_id)
                        if captcha_element:
                            print(f"Captcha detected with ID '{element_id}'!")

                            if trigger_action:
                                print("Triggering captcha resolution action...")
                                stop_event.set()  # Pause main execution
                                trigger_action_result = trigger_action()

                                # Wait until captcha is resolved
                                while trigger_action_result is None:
                                    print("Waiting for user resolution...")
                                    time.sleep(1)
                                    trigger_action_result = trigger_action()

                                if trigger_action_result is False:
                                    print(
                                        "Stopping execution due to failed captcha action."
                                    )
                                    os._exit(1)

                                stop_event.clear()  # Resume main execution
                            else:
                                print("No action provided. Skipping.")

                            break
                    except NoSuchElementException:
                        continue

                previous_html = current_html  # Update state after checks

        except StaleElementReferenceException:
            print("StaleElementReferenceException: Re-locating target element...")
            continue  # Retry finding the element
        except Exception as e:
            print(f"Error while observing DOM: {e}")

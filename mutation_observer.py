import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


def observe_dom_changes(driver, target_selector="body", poll_interval=1):
    """
    Observes changes in the DOM by polling for attribute modifications or new child nodes.

    :param driver: Selenium WebDriver instance
    :param target_selector: CSS selector for the target node to observe
    :param poll_interval: Time (in seconds) between checks
    """

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


# Example usage
from selenium import webdriver

driver = webdriver.Chrome()
driver.get("https://example.com")

# Start observing changes
observe_dom_changes(driver, target_selector="body")

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement


def simulate_click(driver: WebDriver, element: WebElement) -> bool:
    """Simulates user interaction by dispatching click-related events."""

    # Wait until the element is clickable
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable(element))

    # Scroll the element into view
    driver.execute_script("arguments[0].scrollIntoView(true);", element)

    actions = ActionChains(driver)

    # Try using mouse events (mousedown, mouseup, click)
    try:
        print("Attempting to click using mouse events (mousedown, mouseup).")
        actions.move_to_element(element).click_and_hold().release().perform()
        print("Mouse events (mousedown, mouseup) succeeded.")
        return True
    except Exception as e:
        print(f"Mouse events failed: {e}")

    # Try focusing and clicking the element directly
    try:
        print("Attempting to click using element.focus() and element.click().")
        driver.execute_script("arguments[0].focus();", element)
        element.click()  # Perform actual click
        print("Element focus and click succeeded.")
        return True
    except Exception as e:
        print(f"Element focus and click failed: {e}")

    # Try using JavaScript click event dispatch (in case the normal click doesn't work)
    try:
        print("Attempting to click using JavaScript click event.")
        driver.execute_script("arguments[0].click();", element)
        print("JavaScript click succeeded.")
        return True
    except Exception as e:
        print(f"JavaScript click failed: {e}")

    # If the element is still not clicked, throw an exception
    print("All click attempts have failed...")
    return False

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


def simulate_click(driver: WebDriver, element: WebElement) -> None:
    """Simulates user interaction by dispatching click-related events."""

    actions = ActionChains(driver)

    # Simulate mouse events
    actions.move_to_element(element).click_and_hold().release().perform()

    # Simulate focus events
    driver.execute_script("arguments[0].focus();", element)

    # Perform actual click
    element.click()

    # Simulate second focus event (to match JavaScript behavior)
    driver.execute_script(
        "arguments[0].dispatchEvent(new FocusEvent('focus', { bubbles: true, cancelable: true }));",
        element,
    )

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
import time


def simulate_typing(
    driver: WebDriver, element: WebElement, value: str, delay: float = 0.05
) -> None:
    """
    Simulates typing characters into an input field with delays and triggers related events.

    :param driver: Selenium WebDriver instance
    :param element: WebElement representing the input field
    :param value: String value to type
    :param delay: Time (in seconds) between each keystroke
    """

    # Clear the field before typing
    element.clear()

    for char in value:
        element.send_keys(char)  # Type character
        time.sleep(delay)  # Mimic natural typing speed

        # Dispatch JavaScript key events for realism
        driver.execute_script(
            """
            let eventOptions = { bubbles: true, cancelable: true, key: arguments[1], char: arguments[1] };
            ['keydown', 'keypress', 'keyup'].forEach(eventType => {
                arguments[0].dispatchEvent(new KeyboardEvent(eventType, eventOptions));
            });
        """,
            element,
            char,
        )

    # Simulate blur and change events after typing
    driver.execute_script(
        """
        arguments[0].dispatchEvent(new FocusEvent('focusout', { bubbles: true, cancelable: true }));
        arguments[0].dispatchEvent(new FocusEvent('blur', { bubbles: true, cancelable: true }));
        arguments[0].dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
    """,
        element,
    )

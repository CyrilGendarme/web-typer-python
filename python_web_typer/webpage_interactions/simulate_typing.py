import random
import time

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

__all__ = ["simulate_typing"]

_DISPATCH_KEY_EVENTS_JS = """
const eventOptions = { bubbles: true, cancelable: true, key: arguments[1], char: arguments[1] };
['keydown', 'keypress', 'keyup'].forEach(eventType => {
    arguments[0].dispatchEvent(new KeyboardEvent(eventType, eventOptions));
});
"""

_DISPATCH_FOCUS_OUT_JS = """
arguments[0].dispatchEvent(new FocusEvent('focusout', { bubbles: true, cancelable: true }));
arguments[0].dispatchEvent(new FocusEvent('blur', { bubbles: true, cancelable: true }));
arguments[0].dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
"""


def simulate_typing(
    driver: WebDriver,
    element: WebElement,
    value: str,
    delay: float = 0.05,
    shall_focus_out_after_typing: bool = True,
    javascript_key_events_to_be_mimiced: bool = False,
) -> None:
    """
    Simulates typing characters into an input field with delays and triggers related events.

    :param driver: Selenium WebDriver instance
    :param element: WebElement representing the input field
    :param value: String value to type
    :param delay: Time (in seconds) between each keystroke (+/- 20% jitter)
    :param shall_focus_out_after_typing: Whether to trigger focusout, blur, and change events after typing
    :param javascript_key_events_to_be_mimiced: Also dispatch synthetic JS key events per character.
        send_keys already emits trusted key events, so this is only needed for pages that
        listen to events send_keys doesn't reach. Synthetic events have isTrusted=false.
    """

    # Clear the field before typing
    element.clear()

    for char in value:
        # Mimic natural typing speed
        time.sleep(delay * random.uniform(0.8, 1.2))
        element.send_keys(char)

        if javascript_key_events_to_be_mimiced:
            driver.execute_script(_DISPATCH_KEY_EVENTS_JS, element, char)

    if shall_focus_out_after_typing:
        driver.execute_script(_DISPATCH_FOCUS_OUT_JS, element)

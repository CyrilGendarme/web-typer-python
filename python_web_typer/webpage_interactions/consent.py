"""
Cookie banners and consent walls ("Avant d'accéder à YouTube", OneTrust, ...):
refused (optional cookies only) as soon as they show, so the actions see the page.

Only a reject button sitting inside a block that talks about cookies / consent is
clicked, never an unrelated "Reject" (friend requests...).
"""

import logging
import threading

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

from .mutation_observer import start_dom_observer_thread

__all__ = ["find_consent_refusal", "refuse_consent", "start_consent_refuser"]

logger = logging.getLogger(__name__)

# Normalised labels (lowercase, single spaces, straight apostrophes)
_REFUSE_LABELS = (
    "reject all",
    "reject",
    "decline",
    "decline optional cookies",
    "only allow essential cookies",
    "necessary cookies only",
    "use necessary cookies only",
    "tout refuser",
    "refuser tout",
    "refuser",
    "rejeter",
    "refuser les cookies optionnels",
    "continuer sans accepter",
    "alles weigeren",
    "weigeren",
    "optionele cookies weigeren",
    "alle ablehnen",
    "ablehnen",
    "nur notwendige cookies",
    "optionale cookies ablehnen",
)

# The visible refuse button of a consent block, or null
_FIND_REFUSAL_JS = r"""
const [labels] = arguments;
const norm = s => (s || '').replace(/[’]/g, "'").replace(/\s+/g, ' ').trim().toLowerCase();
const wanted = new Set(labels);
const about = /cookie|consent|confidentialit|privacy|données personnelles|personal data|gegevens|datenschutz/i;
for (const btn of document.querySelectorAll('button, [role="button"], input[type="submit"], input[type="button"]')) {
    const r = btn.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    const label = norm(btn.innerText || btn.value || btn.getAttribute('aria-label'));
    if (!wanted.has(label)) continue;
    let block = btn.parentElement;
    for (let depth = 0; block && depth < 8; depth++, block = block.parentElement) {
        if (about.test((block.innerText || '').slice(0, 3000))) return btn;
    }
}
return null;
"""


def find_consent_refusal(driver: WebDriver):
    """The refuse button of a showing cookie banner / consent wall, or None."""
    return driver.execute_script(_FIND_REFUSAL_JS, list(_REFUSE_LABELS))


def refuse_consent(driver: WebDriver) -> bool:
    """Clicks the refuse button of a showing banner. True if one was clicked."""
    try:
        button = find_consent_refusal(driver)
        if button is None:
            return False
        label = (button.text or button.get_attribute("aria-label") or "").strip()
        driver.execute_script("arguments[0].click();", button)
    except WebDriverException as e:
        logger.debug("Consent banner not refused: %s", e)
        return False
    logger.info("Cookie banner refused (\"%s\")", label)
    return True


def _refuse_on_poll(driver: WebDriver) -> None:
    refuse_consent(driver)
    return None  # nothing for the observer to track: refused right away, retried next poll


def start_consent_refuser(driver: WebDriver, stop_event: threading.Event) -> threading.Thread:
    """Background thread refusing cookie banners until `stop_event` is set."""
    return start_dom_observer_thread(driver, stop_event=stop_event, detector=_refuse_on_poll)

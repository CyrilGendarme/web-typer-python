"""
Detection of CAPTCHAs and verification pages (2FA code, checkpoint, bot check).

They are left to the operator: actions pause while one shows (see
cancellation.hold_actions and the DOM observer) and resume once it is solved.
"""

import logging
from typing import Optional

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

from ..config import CAPTCHA_SPECIFIC_CLASSES, CAPTCHA_SPECIFIC_IDS

__all__ = ["find_human_check", "present_human_check"]

logger = logging.getLogger(__name__)

# Visible challenge widgets and pages, in the current document. Invisible
# reCAPTCHA (score only, nothing to solve) is ignored, and so is a widget whose
# response token is filled: solved, waiting for the page to go on.
# Returns a description or null.
_FIND_HUMAN_CHECK_JS = r"""
const [frameRe, urlRe, textRe, classes, ids] = arguments;
const solved = [...document.querySelectorAll(
    '[name="g-recaptcha-response"], [name="h-captcha-response"], [name="cf-turnstile-response"]'
)].some(el => el.value);
if (solved) return null;
const vis = el => { const r = el.getBoundingClientRect(); return r.width > 40 && r.height > 40 && getComputedStyle(el).visibility !== 'hidden'; };
if (new RegExp(urlRe, 'i').test(location.href)) return `verification page (${location.pathname})`;
// Cloudflare Turnstile / hCaptcha draw their frame in a closed shadow root, out of
// reach of querySelectorAll: an empty answer field in a visible widget gives them away.
// (Invisible reCAPTCHA keeps an empty field in its corner badge: skipped.)
for (const field of document.querySelectorAll('[name="cf-turnstile-response"], [name="h-captcha-response"], [name="g-recaptcha-response"]')) {
    const widget = field.parentElement;
    if (!field.value && widget && vis(widget) && !field.closest('.grecaptcha-badge')) {
        return `CAPTCHA (${field.name.replace('-response', '')})`;
    }
}
const frames = new RegExp(frameRe, 'i');
for (const f of document.querySelectorAll('iframe')) {
    if (vis(f) && frames.test(f.src) && !/size=invisible/.test(f.src)) return `CAPTCHA (${new URL(f.src).hostname})`;
}
for (const c of classes) for (const el of document.getElementsByClassName(c)) if (vis(el)) return `CAPTCHA (.${c})`;
for (const i of ids) { const el = document.getElementById(i); if (el && vis(el)) return `CAPTCHA (#${i})`; }
const text = new RegExp(textRe, 'i');
for (const line of (document.body ? document.body.innerText : '').split('\n')) {
    if (line.length < 160 && text.test(line)) return `verification: "${line.trim()}"`;
}
return null;
"""

_HUMAN_CHECK_FRAMES = (
    r"recaptcha|hcaptcha\.com|challenges\.cloudflare\.com|captcha-delivery\.com|arkoselabs\.com"
    r"|funcaptcha\.com|geetest|/captcha"
)
_HUMAN_CHECK_URLS = r"/(?:auth_platform/)?(?:re)?captcha|/challenge|/checkpoint|/two_step_verification|/signin/v\d/challenge"
_HUMAN_CHECK_TEXTS = (
    r"i'?m not a robot|je ne suis pas un robot|ik ben geen robot|ich bin kein roboter"
    r"|verify (?:you are|you're) (?:a )?human|vérifiez que vous êtes (?:un )?humain|confirm you'?re human"
    r"|security check|vérification de sécurité|contrôle de sécurité"
    r"|enter the (?:\d-digit )?code|saisissez le code|entrez le code|two-factor|deux facteurs|authentication code|code d'authentification"
)


def find_human_check(driver: WebDriver) -> Optional[str]:
    """CAPTCHA, bot check or verification (2FA, checkpoint) showing in the current document."""
    return driver.execute_script(
        _FIND_HUMAN_CHECK_JS,
        _HUMAN_CHECK_FRAMES,
        _HUMAN_CHECK_URLS,
        _HUMAN_CHECK_TEXTS,
        list(CAPTCHA_SPECIFIC_CLASSES),
        list(CAPTCHA_SPECIFIC_IDS),
    )


# Scrolls the challenge widget (frame or Turnstile / hCaptcha container) to the middle
# of the screen. Returns true if one was found.
_SCROLL_TO_CHALLENGE_JS = r"""
const [frameRe] = arguments;
const frames = new RegExp(frameRe, 'i');
const target =
    [...document.querySelectorAll('iframe')].find(f => frames.test(f.src) && !/size=invisible/.test(f.src))
    || [...document.querySelectorAll('[name="cf-turnstile-response"], [name="h-captcha-response"]')]
        .map(field => field.parentElement).find(Boolean);
if (!target) return false;
target.scrollIntoView({block: 'center', inline: 'center'});
return true;
"""


def present_human_check(driver: WebDriver) -> None:
    """
    Puts the challenge in front of the operator: browser window raised, widget
    scrolled into view. Solving it stays a human's job.
    """
    try:
        driver.switch_to.window(driver.current_window_handle)  # activates the tab / window
        driver.execute_script(_SCROLL_TO_CHALLENGE_JS, _HUMAN_CHECK_FRAMES)
    except WebDriverException as e:
        logger.debug("Couldn't bring the challenge into view: %s", e)

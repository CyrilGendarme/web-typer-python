"""
Detection of CAPTCHAs and verification pages (2FA code, checkpoint, bot check).

They are left to the operator: actions pause while one shows (see
cancellation.hold_actions and the DOM observer) and resume once it is solved.
"""

from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver

from ..config import CAPTCHA_SPECIFIC_CLASSES, CAPTCHA_SPECIFIC_IDS

__all__ = ["find_human_check"]

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

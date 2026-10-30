"""
Page helpers driven by visible text rather than CSS classes: social platforms
obfuscate and rotate their class names, but button labels stay stable.
Each helper is a single JS round trip.
"""

import time
from typing import List, Optional, Sequence, Tuple

from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait

__all__ = [
    "collect_profile_links",
    "find_follow_buttons_with_profiles",
    "find_follow_button",
    "has_follow_label",
    "read_text",
    "scroll_scope",
    "wait_for",
    "wait_until_label_changes",
]

# Shared JS prelude: label normalisation and scope resolution
_PRELUDE = r"""
const norm = s => (s || '').replace(/[’]/g, "'").replace(/\s+/g, ' ').trim().toLowerCase();
const resolveScope = css => (css && document.querySelector(css)) || document.body;
const isFollowButton = (el, wanted) =>
    wanted.has(norm(el.innerText)) || wanted.has(norm(el.getAttribute('aria-label')));
"""

# [[account_href, card_text], ...] for each distinct profile link in scope.
# card_text = text of the largest ancestor that contains only this profile.
_COLLECT_PROFILE_LINKS_JS = _PRELUDE + r"""
const [scopeCss, profileRe] = arguments;
const scope = resolveScope(scopeCss);
const re = new RegExp(profileRe, 'i');
const idOf = a => (a.href.match(re) || [])[1];
const seen = new Map();
for (const a of scope.querySelectorAll('a[href]')) {
    const id = idOf(a);
    if (!id || seen.has(id.toLowerCase())) continue;
    let card = a;
    while (card.parentElement && card.parentElement !== scope) {
        const ids = new Set([...card.parentElement.querySelectorAll('a[href]')].map(idOf).filter(Boolean));
        if (ids.size > 1) break;
        card = card.parentElement;
    }
    seen.set(id.toLowerCase(), [a.href, (card.innerText || '').slice(0, 600)]);
}
return [...seen.values()];
"""

# [[button, profile_href], ...]: visible follow buttons paired with the profile
# link of the card (closest ancestor holding a profile link) they belong to.
_FIND_BUTTONS_WITH_PROFILES_JS = _PRELUDE + r"""
const [scopeCss, labels, profileRe] = arguments;
const scope = resolveScope(scopeCss);
const wanted = new Set(labels);
const re = new RegExp(profileRe, 'i');
const out = [];
for (const btn of scope.querySelectorAll('button, [role="button"]')) {
    if (!btn.offsetParent || !isFollowButton(btn, wanted)) continue;
    let el = btn, href = null;
    for (let depth = 0; depth < 10 && el && !href; depth++) {
        el = el.parentElement;
        const link = el && [...el.querySelectorAll('a[href]')].find(a => re.test(a.href));
        if (link) href = link.href;
    }
    if (href) out.push([btn, href]);
}
return out;
"""

# Also matches menu entries ("Unfollow" / "Unfriend" in a "..." menu)
_FIND_FOLLOW_BUTTON_JS = _PRELUDE + r"""
const [scopeCss, labels, exclude] = arguments;
const wanted = new Set(labels);
const selector = 'button, [role="button"], [role="menuitem"], [role="option"]';
for (const btn of resolveScope(scopeCss).querySelectorAll(selector)) {
    if (btn !== exclude && btn.offsetParent && isFollowButton(btn, wanted)) return btn;
}
return null;
"""

_HAS_FOLLOW_LABEL_JS = _PRELUDE + r"""
const [el, labels] = arguments;
return el.isConnected && isFollowButton(el, new Set(labels));
"""

_READ_TEXT_JS = r"""
const [css, maxLength] = arguments;
const nodes = css ? [...document.querySelectorAll(css)] : [];
const text = nodes.length ? nodes.map(n => n.innerText).join('\n') : document.body.innerText;
return text.slice(0, maxLength);
"""

# Scrolls the largest scrollable element in scope (dialogs, nested panes) or the
# window. Returns true if the position moved.
_SCROLL_SCOPE_JS = _PRELUDE + r"""
const [scopeCss] = arguments;
const scope = resolveScope(scopeCss);
let target = null;
for (const el of [scope, ...scope.querySelectorAll('*')]) {
    if (el.scrollHeight <= el.clientHeight + 20) continue;
    const overflowY = getComputedStyle(el).overflowY;
    if ((overflowY === 'auto' || overflowY === 'scroll') && (!target || el.scrollHeight > target.scrollHeight)) target = el;
}
if (!target) {
    const before = window.scrollY;
    window.scrollBy(0, window.innerHeight * 0.9);
    return window.scrollY !== before;
}
const before = target.scrollTop;
target.scrollTop += target.clientHeight * 0.9;
return target.scrollTop !== before;
"""


def collect_profile_links(
    driver: WebDriver, profile_url_re: str, scope_css: Optional[str] = None
) -> List[Tuple[str, str]]:
    """[(profile_href, card_text), ...] in page order."""
    return [tuple(pair) for pair in driver.execute_script(_COLLECT_PROFILE_LINKS_JS, scope_css, profile_url_re)]


def find_follow_buttons_with_profiles(
    driver: WebDriver,
    labels: Sequence[str],
    profile_url_re: str,
    scope_css: Optional[str] = None,
) -> List[Tuple[WebElement, str]]:
    return [
        tuple(pair)
        for pair in driver.execute_script(
            _FIND_BUTTONS_WITH_PROFILES_JS, scope_css, list(labels), profile_url_re
        )
    ]


def find_follow_button(
    driver: WebDriver,
    labels: Sequence[str],
    scope_css: Optional[str] = None,
    exclude: Optional[WebElement] = None,
) -> Optional[WebElement]:
    """First visible button or menu entry labelled with one of `labels`, `exclude` aside."""
    return driver.execute_script(_FIND_FOLLOW_BUTTON_JS, scope_css, list(labels), exclude)


def has_follow_label(driver: WebDriver, element: WebElement, labels: Sequence[str]) -> bool:
    """False once the button switched to "Following"/"Requested" (or was removed)."""
    try:
        return driver.execute_script(_HAS_FOLLOW_LABEL_JS, element, list(labels))
    except StaleElementReferenceException:
        return False


def read_text(driver: WebDriver, css: Optional[str] = None, max_length: int = 5000) -> str:
    """innerText of all elements matching `css` (whole page if none match)."""
    return driver.execute_script(_READ_TEXT_JS, css, max_length) or ""


def scroll_scope(driver: WebDriver, scope_css: Optional[str] = None) -> bool:
    return bool(driver.execute_script(_SCROLL_SCOPE_JS, scope_css))


def wait_for(driver: WebDriver, condition, timeout: float, poll: float = 0.5):
    """Polls `condition(driver)` until truthy. Returns its value, or None on timeout."""
    try:
        return WebDriverWait(
            driver, timeout, poll_frequency=poll, ignored_exceptions=(WebDriverException,)
        ).until(lambda d: condition(d) or False)
    except TimeoutException:
        return None


def wait_until_label_changes(
    driver: WebDriver, element: WebElement, labels: Sequence[str], timeout: float = 5
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not has_follow_label(driver, element, labels):
            return True
        time.sleep(0.3)
    return False

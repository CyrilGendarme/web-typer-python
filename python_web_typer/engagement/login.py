"""
Automatic login from config.CREDENTIALS, one declarative step list per platform.

Steps were written from the real pages (cookie banner, iframe, one- or two-step
forms). When a required step can't be done, the page is dumped (screenshot +
visible fields and buttons) to config.LOGIN_DEBUG_DIR so the step list can be
fixed. CAPTCHAs and verification pages (2FA code, checkpoint, bot check) are left
to the operator: the login pauses while one shows (up to
config.LOGIN_HUMAN_CHECK_TIMEOUT), then goes on.
A page saying the login or password is wrong stops the login at once
(BadCredentials), with the message shown by the platform.
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from selenium.common.exceptions import (
    ElementNotInteractableException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from ..cancellation import cancellable_sleep
from ..config import (
    CREDENTIALS,
    LOGIN_DEBUG_DIR,
    LOGIN_HUMAN_CHECK_TIMEOUT,
    LOGIN_VERIFICATION_TIMEOUT,
)
from ..humanize import Humanized, draw
from ..webpage_interactions.human_check import find_human_check
from ..webpage_interactions.simulate_click import simulate_click
from ..webpage_interactions.simulate_typing import simulate_typing
from .dom import find_follow_button, find_visible, wait_for

__all__ = ["LOGIN_SPECS", "BadCredentials", "BotBlocked", "HumanCheckCallback", "credentials", "login_platforms", "auto_login", "is_logged_in", "dump_page"]

logger = logging.getLogger(__name__)

# Pause between two steps (reading the page, moving to the next field)
_STEP_PAUSE = Humanized(1.2, 2.5, min=0.5)

# (platform, description) called when a CAPTCHA / verification waits for the operator
HumanCheckCallback = Callable[[str, str], None]


class LoginFailed(Exception):
    pass


class BotBlocked(Exception):
    """
    The platform's bot protection refused the automated browser (no CAPTCHA to
    solve). Retrying only prolongs the block: log in by hand instead.
    """

    def __init__(self, platform: str, message: str):
        super().__init__(f"[{platform}] Automated browser blocked by the site's bot protection: \"{message}\"")
        self.platform = platform
        self.message = message


class BadCredentials(ValueError):
    """The platform refused the login or the password. `message` is its own wording."""

    def __init__(self, platform: str, message: str):
        super().__init__(f"[{platform}] Login refused, check the login / password: \"{message}\"")
        self.platform = platform
        self.message = message


# ---------------------------
# Steps
# ---------------------------


@dataclass(frozen=True)
class Step:
    """
    kind: "click" (css or button labels), "fill" (field = "login"/"password"),
    "frame" (enter the iframe matching css), "submit" (Enter in the last filled
    field, or click css / labels). Optional steps are skipped when nothing
    matches within `timeout` (cookie banners only shown once per profile).
    """

    kind: str
    css: Optional[str] = None
    labels: Tuple[str, ...] = ()
    field: Optional[str] = None
    optional: bool = False
    # Generous: the page after a submit can take a while (Mixcloud sends an email first)
    timeout: float = 30

    def describe(self) -> str:
        target = self.field or self.css or "/".join(self.labels[:3]) or "Enter"
        return f"{self.kind} {target}"


def dismiss(css: Optional[str] = None, *labels: str, timeout: float = 6) -> Step:
    return Step("click", css, tuple(labels), optional=True, timeout=timeout)


def click(css: Optional[str] = None, *labels: str) -> Step:
    return Step("click", css, tuple(labels))


def fill(field: str, css: str, timeout: float = 30) -> Step:
    return Step("fill", css, field=field, timeout=timeout)


def frame(css: str) -> Step:
    return Step("frame", css)


def submit(css: Optional[str] = None, *labels: str) -> Step:
    return Step("submit", css, tuple(labels))


# Cookie banners: refuse what can be refused (normalised labels, see dom.py)
_REFUSE_OPTIONAL_COOKIES = (
    "refuser les cookies optionnels",
    "decline optional cookies",
    "only allow essential cookies",
    "optionele cookies weigeren",
    "optionale cookies ablehnen",
)
_REJECT_ALL = ("reject all", "tout refuser", "rejeter", "reject", "alles weigeren", "alle ablehnen")


@dataclass(frozen=True)
class LoginSpec:
    url: str
    steps: Tuple[Step, ...]
    # Session cookie set once logged in, on the domain reached after login
    session_cookie: Optional[str] = None
    # Element only shown to logged-out visitors (login button, password field)
    logged_out_css: str = 'input[type="password"]'


LOGIN_SPECS: Dict[str, LoginSpec] = {
    "facebook": LoginSpec(
        url="https://www.facebook.com/login",
        steps=(
            dismiss(None, *_REFUSE_OPTIONAL_COOKIES),
            fill("login", 'input[name="email"]'),
            fill("password", 'input[name="pass"]'),
            submit(),
        ),
        session_cookie="c_user",
    ),
    "instagram": LoginSpec(
        url="https://www.instagram.com/accounts/login/",
        steps=(
            dismiss(None, *_REFUSE_OPTIONAL_COOKIES),
            fill("login", 'input[name="email"], input[name="username"]'),
            fill("password", 'input[name="pass"], input[name="password"]'),
            submit(),
        ),
        session_cookie="sessionid",
    ),
    # Form in an iframe: email -> Continue -> password
    "soundcloud": LoginSpec(
        url="https://soundcloud.com/signin",
        steps=(
            dismiss("#onetrust-reject-all-handler"),
            frame('iframe[src*="secure.soundcloud.com"]'),
            fill("login", "#sign_in_up_email"),
            click('#sign_in_up_submit, [data-testid="sign_in_up_submit"]'),
            fill("password", 'input[type="password"]'),
            submit(),
        ),
        session_cookie="oauth_token",
    ),
    # /login/ opens the login modal: email -> Continue -> "with your password" -> password
    "mixcloud": LoginSpec(
        url="https://www.mixcloud.com/login/",
        steps=(
            dismiss(None, "ok"),
            fill("login", 'input[name="email"][autocomplete="username"], input[name="email"]'),
            submit(),
            # Mixcloud emails a one-time code by default
            click(None, "log in with your password", "se connecter avec votre mot de passe"),
            fill("password", 'input[type="password"]'),
            submit(),
        ),
        logged_out_css='[data-testid="top-nav-login-button"], [data-testid="top-nav-login-button-your-account"]',
    ),
    # Google account: email -> Next -> password
    "youtube": LoginSpec(
        url="https://accounts.google.com/ServiceLogin?service=youtube&continue=https://www.youtube.com/",
        steps=(
            fill("login", "#identifierId"),
            submit(),
            fill("password", 'input[name="Passwd"]'),
            submit(),
        ),
        session_cookie="LOGIN_INFO",
        logged_out_css="#identifierId, input[name='Passwd']",
    ),
    "rumble": LoginSpec(
        url="https://rumble.com/login.php",
        steps=(
            dismiss("#ketch-banner-button-secondary", *_REJECT_ALL),
            fill("login", 'input[name="username"]'),
            fill("password", 'input[name="password"]'),
            submit(),
        ),
    ),
    # Modal opened from the top bar
    "kick": LoginSpec(
        url="https://kick.com/",
        steps=(
            dismiss(None, *_REJECT_ALL),
            click('[data-testid="login"]'),
            fill("login", 'input[name="emailOrUsername"]'),
            fill("password", 'input[name="password"]'),
            # Enter doesn't submit; a tab above the form has the same "Log in" label
            submit('form button[type="submit"]'),
        ),
        logged_out_css='[data-testid="login"]',
    ),
    "twitch": LoginSpec(
        url="https://www.twitch.tv/login",
        steps=(
            dismiss(None, *_REJECT_ALL),
            fill("login", "#login-username"),
            fill("password", "#password-input"),
            submit('[data-a-target="passport-login-button"]'),
        ),
        session_cookie="auth-token",
    ),
}


# ---------------------------
# Running the steps
# ---------------------------

# Visible fields and buttons, for the debug dump of a blocked login
_DUMP_PAGE_JS = r"""
const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'; };
const t = s => (s || '').replace(/\s+/g, ' ').trim().slice(0, 80);
const attrs = el => Object.fromEntries(['type', 'name', 'id', 'autocomplete', 'aria-label', 'placeholder', 'data-testid', 'data-a-target']
    .map(a => [a, el.getAttribute(a)]).filter(([, v]) => v));
return {
    url: location.href,
    title: document.title,
    inputs: [...document.querySelectorAll('input, textarea')].filter(el => vis(el) && el.type !== 'hidden').map(attrs),
    buttons: [...document.querySelectorAll('button, [role="button"], a, input[type=submit]')].filter(vis)
        .map(el => [el.tagName, t(el.innerText || el.value || el.getAttribute('aria-label')), attrs(el)]).filter(b => b[1]).slice(0, 80),
    iframes: [...document.querySelectorAll('iframe')].filter(vis).map(f => f.src.slice(0, 200)),
    text: (document.body.innerText || '').slice(0, 2000),
};
"""


def dump_page(driver: WebDriver, platform: str, reason: str) -> Optional[str]:
    """Saves a screenshot and the visible controls of the current page. Returns the file prefix."""
    os.makedirs(LOGIN_DEBUG_DIR, exist_ok=True)
    prefix = os.path.join(LOGIN_DEBUG_DIR, f"{platform}-{time.strftime('%Y%m%d-%H%M%S')}")
    try:
        driver.save_screenshot(prefix + ".png")
        page = driver.execute_script(_DUMP_PAGE_JS)
        with open(prefix + ".json", "w", encoding="utf-8") as f:
            json.dump({"reason": reason, **page}, f, indent=1, ensure_ascii=False)
    except (WebDriverException, OSError) as e:
        logger.warning("[%s] Page dump failed: %s", platform, e)
        return None
    return prefix


def _find(driver: WebDriver, step: Step) -> Optional[WebElement]:
    if step.css:
        element = find_visible(driver, step.css)
        if element is not None:
            return element
    if step.labels:
        return find_follow_button(driver, step.labels)
    return None


class _LoginRun:
    """One login attempt: runs the steps, remembering the iframe they work in."""

    def __init__(self, driver: WebDriver, platform: str, creds: dict, on_human_check: Optional[HumanCheckCallback]):
        self.driver = driver
        self.platform = platform
        self.creds = creds
        self.on_human_check = on_human_check
        self.frame_css: Optional[str] = None
        self.last_field: Optional[WebElement] = None
        self._alerted: Optional[str] = None

    # ----- iframe -----

    def _enter_frame(self) -> bool:
        self.driver.switch_to.default_content()
        element = find_visible(self.driver, self.frame_css)
        if element is None:
            return False
        # Cross-origin frames don't scroll the outer page: their fields would sit off screen
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'start'});", element)
        self.driver.switch_to.frame(element)
        return True

    def _reenter_frame(self) -> None:
        """After an error: the iframe may have been reloaded, leaving us in a dead document."""
        if self.frame_css:
            try:
                self._enter_frame()
            except WebDriverException:
                pass

    # ----- waiting, with CAPTCHA / verification pauses -----

    def human_check(self) -> Optional[str]:
        """Description of a CAPTCHA or verification page showing (page or login iframe), else None."""
        try:
            self.driver.switch_to.default_content()
            found = find_human_check(self.driver)
            if not found and self.frame_css:
                found = self._enter_frame() and find_human_check(self.driver)
            return found or None
        except WebDriverException:
            return None
        finally:
            self._reenter_frame()

    def pause_for_human_check(self) -> bool:
        """
        If a CAPTCHA / verification shows, alerts once and waits until it's gone
        (solved by the operator). Returns True if there was one.
        """
        _check_page(self.driver, self.platform)  # unsolvable block / refused login: no point waiting
        self._reenter_frame()
        found = self.human_check()
        if not found:
            return False
        if found != self._alerted:
            self._alerted = found
            logger.warning("[%s] %s: solve it in the browser, the login goes on afterwards", self.platform, found)
            if self.on_human_check:
                self.on_human_check(self.platform, found)
        deadline = time.monotonic() + LOGIN_HUMAN_CHECK_TIMEOUT
        while time.monotonic() < deadline:
            cancellable_sleep(2)
            _check_page(self.driver, self.platform)
            self._reenter_frame()
            if not self.human_check():
                logger.info("[%s] Check passed, resuming", self.platform)
                return True
        raise LoginFailed(f"{found}: not solved within {LOGIN_HUMAN_CHECK_TIMEOUT}s")

    def wait_for(self, condition, timeout: float):
        """dom.wait_for, pausing (without consuming the timeout) while a human check shows."""
        while True:
            result = wait_for(self.driver, condition, timeout)
            if result is not None or not self.pause_for_human_check():
                return result

    # ----- steps -----

    def run(self, step: Step) -> None:
        try:
            self._run(step)
        except (StaleElementReferenceException, ElementNotInteractableException) as e:
            # The page re-rendered under us (SoundCloud reloads its iframe): retry once
            logger.debug("[%s] %s: %s, retrying", self.platform, step.describe(), type(e).__name__)
            cancellable_sleep(1.5)
            self._reenter_frame()
            self._run(step)

    def _run(self, step: Step) -> None:
        driver = self.driver
        if step.kind == "frame":
            self.frame_css = step.css
            if not self.wait_for(lambda d: self._enter_frame(), step.timeout):
                raise LoginFailed(f"iframe {step.css} not found")
            return

        if step.kind == "submit" and not (step.css or step.labels):
            if self.last_field is None:
                raise LoginFailed("nothing to submit")
            self.last_field.send_keys(Keys.ENTER)
            return

        element = self.wait_for(lambda d: _find(d, step), step.timeout)
        if element is None:
            raise LoginFailed(f"{step.describe()}: not found")

        if step.kind == "fill":
            simulate_click(driver, element, wait_time=3)
            simulate_typing(driver, element, self.creds[step.field])
            self.last_field = element
            return
        if not simulate_click(driver, element, wait_time=5):
            raise LoginFailed(f"{step.describe()}: click failed")


# ---------------------------
# Refused credentials
# ---------------------------

# A short line of the page combining a failure word with a credential word, e.g.
# "The password that you've entered is incorrect", "Impossible de trouver ce compte"
_FAILURE_RE = re.compile(
    r"incorrect|invalid|wrong|isn't connected|doesn't belong|does not (?:exist|belong|match)"
    r"|(?:couldn't|could not|can't|cannot) find|not recogni[sz]ed|no account"
    r"|not valid|non[- ]valide|pas valide|invalide|erron[ée]|introuvable|impossible de trouver|n'est associ[ée]|n'appartient|n'existe pas|aucun compte"
    r"|onjuist|ongeldig|niet gevonden|bestaat niet|falsch|ungültig|nicht gefunden|existiert nicht"
)
_CREDENTIAL_RE = re.compile(
    r"password|username|e-?mail|phone|account|credentials|login"
    r"|mot de passe|identifiant|nom d'utilisateur|adresse|num[ée]ro|compte"
    r"|wachtwoord|gebruikersnaam|passwort|benutzername|konto"
)
_MAX_ERROR_LINE = 200


def find_credential_error(text: str) -> Optional[str]:
    """First line of `text` saying the login or password is wrong, else None."""
    for line in text.splitlines():
        line = line.strip()
        normalized = re.sub(r"\s+", " ", line.replace("\u2019", "'")).lower()
        if (
            len(normalized) <= _MAX_ERROR_LINE
            and _FAILURE_RE.search(normalized)
            and _CREDENTIAL_RE.search(normalized)
        ):
            return line
    return None


# Bot protection pages that can't be solved (DataDome "t=bv", Cloudflare / Akamai blocks)
_BOT_BLOCK_RE = re.compile(
    r"accès temporairement restreint|pourquoi ce blocage|access (?:is )?temporarily (?:restricted|blocked)"
    r"|you(?:'ve| have) been blocked|why (?:have i|was i) been blocked|toegang tijdelijk beperkt|zugriff vorübergehend",
    re.IGNORECASE,
)
_BOT_BLOCK_FRAME_RE = re.compile(r"captcha-delivery\.com/.*[?&]t=bv\b")

_VISIBLE_FRAMES_JS = """
return [...document.querySelectorAll('iframe')].filter(f => {
    const r = f.getBoundingClientRect();
    return r.width > 40 && r.height > 40;
});
"""


def _page_texts(driver: WebDriver, depth: int = 2) -> List[Tuple[str, str]]:
    """
    [(url, innerText)] of the current document and of its visible iframes, nested
    ones included (block pages and errors often sit in a frame). Leaves the
    top-level page selected.
    """
    found: List[Tuple[str, str]] = []

    def scan(level: int) -> None:
        try:
            found.append(driver.execute_script("return [location.href, document.body ? document.body.innerText : '']"))
            frames = driver.execute_script(_VISIBLE_FRAMES_JS) if level < depth else []
        except WebDriverException:
            return
        for element in frames:
            try:
                src = element.get_attribute("src") or ""
                driver.switch_to.frame(element)
            except WebDriverException:
                continue
            found.append((src, ""))  # cross-origin src known even if the frame can't be read
            scan(level + 1)
            driver.switch_to.parent_frame()

    try:
        driver.switch_to.default_content()
        scan(0)
    finally:
        driver.switch_to.default_content()
    return found


def _check_page(driver: WebDriver, platform: str) -> None:
    """
    Raises BotBlocked / BadCredentials if the page or one of its frames shows a
    bot-protection block or says the login or password is wrong.
    """
    texts = _page_texts(driver)
    for url, text in texts:
        if _BOT_BLOCK_FRAME_RE.search(url):
            raise BotBlocked(platform, "DataDome block page")
        match = _BOT_BLOCK_RE.search(text)
        if match:
            raise BotBlocked(platform, match.group(0))
    for _url, text in texts:
        message = find_credential_error(text)
        if message:
            raise BadCredentials(platform, message)


def is_logged_in(driver: WebDriver, platform: str) -> Optional[bool]:
    """True / False when the page tells, None while it can't tell (still loading)."""
    spec = LOGIN_SPECS[platform]
    try:
        if spec.session_cookie and driver.get_cookie(spec.session_cookie):
            return True
        if find_visible(driver, spec.logged_out_css) is not None:
            return False
    except WebDriverException:
        return None
    # Without a session cookie to check, the absence of the login control is the sign
    return None if spec.session_cookie else True


def _wait_session(run: "_LoginRun", timeout: float) -> bool:
    """
    Waits for a logged-in sign, confirmed a moment later (pages flicker while
    redirecting). Time spent on a CAPTCHA / verification doesn't count.
    """
    driver, platform = run.driver, run.platform
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        _check_page(driver, platform)
        if is_logged_in(driver, platform):
            cancellable_sleep(3)
            if is_logged_in(driver, platform):
                return True
        paused = run.pause_for_human_check()
        driver.switch_to.default_content()  # the check may have left us in the login iframe
        if paused:
            deadline = time.monotonic() + timeout
        cancellable_sleep(1)
    return False


def _initial_state(driver: WebDriver, platform: str) -> Optional[bool]:
    """Logged in or out once the login page told, None if it didn't within a few seconds."""
    states = {True: "in", False: "out"}
    state = wait_for(driver, lambda d: states.get(is_logged_in(d, platform)), timeout=10)
    return None if state is None else state == "in"


def credentials(platform: str) -> dict:
    creds = CREDENTIALS.get(platform) or {}
    return {"login": (creds.get("login") or "").strip(), "password": creds.get("password") or ""}


def login_platforms(configured_only: bool = True):
    """Platforms with a login and a password set (all of them if not `configured_only`)."""
    return [p for p in LOGIN_SPECS if not configured_only or all(credentials(p).values())]


def auto_login(driver: WebDriver, platform: str, on_human_check: Optional[HumanCheckCallback] = None) -> bool:
    """
    Logs in to `platform` with config.CREDENTIALS unless already logged in.
    Returns True once logged in. On a blocked step, dumps the page and returns False.

    A CAPTCHA or verification page (2FA code, checkpoint) pauses the login until
    the operator solved it in the browser; `on_human_check(platform, description)`
    is called once when it shows.

    Raises:
        BotBlocked: if the site's bot protection blocks the automated browser
            (log in by hand: open_login_browser).
        BadCredentials: if the platform says the login or the password is wrong
            (also when a two-step form refuses the login before asking the password).
        ValueError: if no login / password is set.
    """
    spec = LOGIN_SPECS[platform]
    creds = credentials(platform)
    if not all(creds.values()):
        raise ValueError(f"[{platform}] set the login and password in config.CREDENTIALS")

    driver.get(spec.url)
    if _initial_state(driver, platform):
        logger.info("[%s] Already logged in", platform)
        return True

    run = _LoginRun(driver, platform, creds, on_human_check)
    try:
        for step in spec.steps:
            cancellable_sleep(draw(_STEP_PAUSE))
            try:
                run.run(step)
                logger.debug("[%s] %s: done", platform, step.describe())
            except LoginFailed as e:
                if not step.optional:
                    raise
                logger.debug("[%s] Skipped optional %s", platform, e)
    except (LoginFailed, WebDriverException) as e:
        driver.switch_to.default_content()
        # Two-step forms: a refused login shows an error instead of the password field
        cancellable_sleep(1)
        _check_page(driver, platform)
        reason = str(e).splitlines()[0] if str(e) else type(e).__name__
        prefix = dump_page(driver, platform, reason)
        logger.error("[%s] Login blocked at %s (page saved to %s.*)", platform, reason, prefix)
        return False
    finally:
        driver.switch_to.default_content()

    logger.info("[%s] Credentials submitted, waiting for the session", platform)
    if _wait_session(run, LOGIN_VERIFICATION_TIMEOUT):
        logger.info("[%s] Logged in", platform)
        return True
    prefix = dump_page(driver, platform, "no session after submitting")
    logger.error("[%s] Not logged in after submitting (page saved to %s.*)", platform, prefix)
    return False

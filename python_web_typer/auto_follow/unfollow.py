"""Unfollow every followed account except the ones in the keep list."""

import logging
import time
from dataclasses import dataclass
from typing import Iterable, Optional, Set, Tuple

from selenium.webdriver.remote.webelement import WebElement

from ..config import AUTO_FOLLOW_IDLE_SCROLLS, AUTO_UNFOLLOW_DELAY, SCROLL_PAUSE
from ..humanize import draw
from ..task_engine_extension.tasks import scroll_to_bottom
from ..webpage_interactions.simulate_click import simulate_click
from .dom import (
    collect_profile_links,
    find_follow_button,
    find_follow_buttons_with_profiles,
    scroll_scope,
    wait_for,
    wait_until_label_changes,
)
from .session import ActionSession
from .store import UNFOLLOWED

__all__ = ["UnfollowSpec", "UnfollowSession", "normalize_keep_list", "run_unfollow"]

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class UnfollowSpec:
    """
    Where the followed accounts are listed and which buttons undo a follow.

    steps: label sets clicked in order. The first one is the account's own
        button ("Following", "Subscribed"...), the next ones are menu entries or
        confirmation dialogs ("Unfollow", "Unfriend", "Confirm"...).
    on_profile: False = the first button sits on each card of the following
        list. True = the list only links to profiles, each profile is opened.
    """

    following_url: str  # may contain {me} (config own_account)
    steps: Tuple[Tuple[str, ...], ...]
    scope_css: Optional[str] = None
    on_profile: bool = False


def normalize_keep_list(spec, entries: Iterable[str]) -> Set[str]:
    """
    Account ids of the keep list. "@name", "name" and profile URLs are accepted.

    Raises:
        ValueError: on an entry that doesn't resolve to an account id, so a typo
            can't silently cause a wanted account to be unfollowed.
    """
    keep = set()
    for entry in entries:
        account_id = _resolve_account(spec, entry)
        if account_id is None:
            raise ValueError(f"[{spec.name}] keep list entry not recognised: {entry!r}")
        keep.add(account_id)
    return keep


def _resolve_account(spec, entry: str) -> Optional[str]:
    entry = entry.strip()
    if entry.lower().startswith("http"):
        return spec.account_id(entry)
    name = entry.strip("/")
    # "@name" is the id itself on YouTube, a decoration elsewhere: try both
    for candidate in (name, name.lstrip("@"), "@" + name.lstrip("@")):
        account_id = spec.account_id(spec.profile_url.format(id=candidate))
        if account_id:
            return account_id
    return None


class UnfollowSession(ActionSession):
    verb = "unfollow"
    past_tense = "Unfollowed"
    delay = AUTO_UNFOLLOW_DELAY

    def _click_steps(self, first_button: WebElement) -> bool:
        steps = self.spec.unfollow.steps
        if not simulate_click(self.driver, first_button, wait_time=5):
            return False
        previous = first_button
        for labels in steps[1:]:
            button = wait_for(
                self.driver,
                lambda d: find_follow_button(d, labels, exclude=previous),
                timeout=6,
            )
            if button is None or not simulate_click(
                self.driver, button, shall_scroll=False, wait_time=5
            ):
                return False
            previous = button
        # Done once the account's button no longer reads "Following"
        return wait_until_label_changes(self.driver, first_button, steps[0])

    def unfollow(self, button: Optional[WebElement], account_id: str, url: str) -> bool:
        if self.dry_run:
            self.succeeded(account_id)
            return True

        if not self._click_steps(button):
            self.failed(account_id)
            return False

        self.store.mark(self.spec.name, account_id, UNFOLLOWED, url)
        self.succeeded(account_id)
        return True


def _run_in_list(session: UnfollowSession, keep: Set[str]) -> None:
    driver, spec = session.driver, session.spec
    unfollow = spec.unfollow
    first_labels = unfollow.steps[0]

    def cards(d):
        return find_follow_buttons_with_profiles(d, first_labels, spec.profile_url_re, unfollow.scope_css)

    if not wait_for(driver, cards, timeout=15):
        logger.info("[%s] No followed account found", spec.name)
        return

    seen = set()
    idle_scrolls = 0
    max_idle_scrolls = draw(AUTO_FOLLOW_IDLE_SCROLLS)
    while not session.done and idle_scrolls < max_idle_scrolls:
        fresh = False
        for button, url in cards(driver):
            account_id = spec.account_id(url)
            if not account_id or account_id in seen:
                continue
            seen.add(account_id)
            fresh = True
            if account_id in keep:
                logger.debug("[%s] Keeping %s", spec.name, account_id)
                continue
            session.unfollow(button, account_id, url)
            if session.done:
                return

        idle_scrolls = 0 if fresh else idle_scrolls + 1
        scroll_scope(driver, unfollow.scope_css)
        time.sleep(draw(SCROLL_PAUSE))


def _run_on_profiles(session: UnfollowSession, keep: Set[str]) -> None:
    driver, spec = session.driver, session.spec
    unfollow = spec.unfollow

    def profiles(d):
        return collect_profile_links(d, spec.profile_url_re, unfollow.scope_css)

    if not wait_for(driver, profiles, timeout=15):
        logger.info("[%s] No followed account found", spec.name)
        return
    scroll_to_bottom(driver)  # load the whole list first

    accounts = {}
    for url, _ in profiles(driver):
        account_id = spec.account_id(url)
        if account_id and account_id not in keep:
            accounts.setdefault(account_id, url)
    logger.info("[%s] %d accounts to unfollow (keep list excluded)", spec.name, len(accounts))

    for account_id, url in accounts.items():
        if session.done:
            return
        if session.dry_run:
            session.unfollow(None, account_id, url)
            continue
        driver.get(url)
        button = wait_for(
            driver,
            lambda d: find_follow_button(d, unfollow.steps[0], spec.profile_header_css),
            timeout=8,
        )
        if button is None:
            # Not followed (e.g. a recommendation shown next to the list)
            logger.debug("[%s] No unfollow button on %s", spec.name, account_id)
            continue
        time.sleep(draw(SCROLL_PAUSE))
        session.unfollow(button, account_id, url)


def run_unfollow(session: UnfollowSession, settings: dict, keep: Set[str]) -> None:
    spec = session.spec
    following_url = spec.unfollow.following_url
    own_account = (settings.get("own_account") or "").strip().lstrip("@")
    if "{me}" in following_url and not own_account:
        logger.error("[%s] own_account must be set in config.AUTO_UNFOLLOW", spec.name)
        return

    session.driver.get(following_url.format(me=own_account))
    (_run_on_profiles if spec.unfollow.on_profile else _run_in_list)(session, keep)

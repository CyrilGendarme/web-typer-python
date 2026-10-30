"""Platform definition and follow strategies (search mode, listing mode)."""

import logging
import random
import re
import time
from dataclasses import dataclass
from typing import Callable, FrozenSet, Iterator, Optional, Tuple
from urllib.parse import quote_plus

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from ..config import (
    AUTO_FOLLOW_BROWSE_DELAY,
    AUTO_FOLLOW_FOLLOW_DELAY,
    AUTO_FOLLOW_IDLE_SCROLLS,
    AUTO_FOLLOW_PROFILE_VISITS_PER_TERM,
    SCROLL_PAUSE,
)
from ..humanize import draw, upper_bound
from ..task_engine_extension.tasks import scroll_to_bottom
from ..webpage_interactions.simulate_click import simulate_click
from .counts import find_follower_count
from .dom import (
    collect_profile_links,
    find_follow_button,
    find_follow_buttons_with_profiles,
    read_text,
    scroll_scope,
    wait_for,
    wait_until_label_changes,
)
from .like import LikeSpec
from .session import ActionSession
from .store import FOLLOWED, SKIPPED
from .unfollow import UnfollowSpec

__all__ = [
    "FOLLOW_LABELS",
    "PlatformSpec",
    "FollowSession",
    "browse_pause",
    "run_search",
    "run_listing",
]

logger = logging.getLogger(__name__)

# Normalised (lowercase, single spaces) button labels meaning "follow this account"
FOLLOW_LABELS = (
    "follow",
    "follow back",
    "subscribe",
    "suivre",
    "suivre en retour",
    "s'abonner",
    "volgen",
    "abonneren",
    "folgen",
    "abonnieren",
)


@dataclass(frozen=True)
class PlatformSpec:
    """
    How to find and follow accounts on one platform.

    Search mode (search_url set): search -> profiles -> follow those under
    `max_followers`. Listing mode (listing_pages set): pages listing accounts
    with a follow button on each card (followers list, friend list).
    """

    name: str
    login_url: str
    # Matches a profile URL, group 1 = account id (must also be a valid JS regex)
    profile_url_re: str
    # Profile URL from an account id ({id}), inverse of profile_url_re
    profile_url: str
    reserved_ids: FrozenSet[str] = frozenset()
    follow_labels: Tuple[str, ...] = FOLLOW_LABELS
    # Search mode
    search_url: Optional[str] = None  # contains {query}
    results_scope_css: Optional[str] = "main"
    profile_header_css: Optional[str] = "main"
    # Listing mode: (driver, spec, settings) -> URLs of pages listing accounts
    listing_pages: Optional[Callable[..., Iterator[str]]] = None
    listing_scope_css: Optional[str] = None
    # How to undo follows (unfollow.UnfollowSpec)
    unfollow: Optional[UnfollowSpec] = None
    # How to find and like posts (like.LikeSpec)
    like: Optional[LikeSpec] = None

    def account_id(self, url: str) -> Optional[str]:
        match = re.match(self.profile_url_re, url, re.IGNORECASE)
        if not match:
            return None
        account_id = match.group(1).lower()
        return None if account_id in self.reserved_ids else account_id


def browse_pause() -> None:
    time.sleep(draw(AUTO_FOLLOW_BROWSE_DELAY))


class FollowSession(ActionSession):
    verb = "follow"
    past_tense = "Followed"
    delay = AUTO_FOLLOW_FOLLOW_DELAY

    def browse_pause(self) -> None:
        browse_pause()

    def click_follow(
        self,
        button: WebElement,
        account_id: str,
        url: str,
        follower_count: Optional[int] = None,
    ) -> bool:
        """Clicks `button` and records the follow once the button state changed."""
        labels = self.spec.follow_labels
        if not (
            simulate_click(self.driver, button, wait_time=5)
            and wait_until_label_changes(self.driver, button, labels)
        ):
            self.failed(account_id)
            return False

        self.store.mark(self.spec.name, account_id, FOLLOWED, url, follower_count)
        self.succeeded(
            account_id,
            f", {follower_count} followers" if follower_count is not None else "",
        )
        return True


# ---------------------------
# Search mode
# ---------------------------


def run_search(session: FollowSession, settings: dict) -> None:
    driver, spec, store = session.driver, session.spec, session.store
    # Drawn anew for each account; skips above the hard cap are never reconsidered
    max_followers = settings["max_followers"]
    max_followers_cap = upper_bound(max_followers)
    terms = list(settings.get("search_terms") or ())
    if not terms:
        logger.warning("[%s] No search_terms configured", spec.name)
        return
    random.shuffle(terms)

    def profiles(d: WebDriver):
        return collect_profile_links(d, spec.profile_url_re, spec.results_scope_css)

    for term in terms:
        if session.done:
            return
        driver.get(spec.search_url.format(query=quote_plus(term)))
        if not wait_for(driver, profiles, timeout=15):
            logger.info("[%s] No results for %r", spec.name, term)
            continue
        session.browse_pause()
        scroll_to_bottom(driver, max_rounds=settings["search_scrolls"])
        candidates = profiles(driver)
        logger.info("[%s] %r: %d accounts found", spec.name, term, len(candidates))

        visits = 0
        max_visits = draw(AUTO_FOLLOW_PROFILE_VISITS_PER_TERM)
        for url, card_text in candidates:
            if session.done or visits >= max_visits:
                break
            account_id = spec.account_id(url)
            if not account_id or store.is_known(spec.name, account_id, max_followers_cap):
                continue

            # Skip the profile visit when the search card already shows the count
            threshold = draw(max_followers)
            count = find_follower_count(card_text)
            if count is not None and count >= threshold:
                store.mark(spec.name, account_id, SKIPPED, url, count)
                continue

            driver.get(url)
            visits += 1
            if count is None:
                count = wait_for(
                    driver,
                    lambda d: find_follower_count(read_text(d, spec.profile_header_css)),
                    timeout=10,
                )
            if count is None:
                logger.info("[%s] Follower count of %s not found", spec.name, account_id)
                continue
            if count >= threshold:
                store.mark(spec.name, account_id, SKIPPED, url, count)
                continue

            button = wait_for(
                driver,
                lambda d: find_follow_button(d, spec.follow_labels, spec.profile_header_css),
                timeout=8,
            )
            if button is None:
                # Already followed, own account, or page variant without button
                logger.info("[%s] No follow button on %s", spec.name, account_id)
                store.mark(spec.name, account_id, SKIPPED, url, count)
                continue

            session.browse_pause()
            session.click_follow(button, account_id, url, count)


# ---------------------------
# Listing mode
# ---------------------------


def run_listing(session: FollowSession, settings: dict) -> None:
    driver, spec, store = session.driver, session.spec, session.store

    for page_url in spec.listing_pages(driver, spec, settings):
        if session.done:
            return
        driver.get(page_url)
        if not wait_for(
            driver,
            lambda d: find_follow_buttons_with_profiles(
                d, spec.follow_labels, spec.profile_url_re, spec.listing_scope_css
            ),
            timeout=15,
        ):
            logger.info("[%s] Nothing to follow on %s", spec.name, page_url)
            continue
        session.browse_pause()

        seen = set()
        idle_scrolls = 0
        max_idle_scrolls = draw(AUTO_FOLLOW_IDLE_SCROLLS)
        while not session.done and idle_scrolls < max_idle_scrolls:
            fresh = False
            for button, url in find_follow_buttons_with_profiles(
                driver, spec.follow_labels, spec.profile_url_re, spec.listing_scope_css
            ):
                account_id = spec.account_id(url)
                if not account_id or account_id in seen:
                    continue
                seen.add(account_id)
                fresh = True
                if store.is_known(spec.name, account_id):
                    continue
                session.click_follow(button, account_id, url)
                if session.done:
                    return

            idle_scrolls = 0 if fresh else idle_scrolls + 1
            scroll_scope(driver, spec.listing_scope_css)
            time.sleep(draw(SCROLL_PAUSE))

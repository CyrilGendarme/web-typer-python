"""Like posts found by search requests, never liking the same post twice."""

import logging
import random
import re
import time
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import quote_plus

from selenium.webdriver.remote.webelement import WebElement

from ..config import AUTO_LIKE_DELAY, AUTO_LIKE_POSTS_PER_TERM, AUTO_LIKE_VIEW_DELAY
from ..humanize import draw
from ..task_engine_extension.tasks import scroll_to_bottom
from ..webpage_interactions.simulate_click import simulate_click
from .dom import collect_profile_links, find_like_button, wait_for, wait_until_liked
from .session import ActionSession

__all__ = ["LIKED", "LikeSpec", "LikeSession", "likes_store_key", "run_like"]

logger = logging.getLogger(__name__)

LIKED = "liked"
SKIPPED_POST = "skipped"


def likes_store_key(platform: str) -> str:
    """Liked posts are stored next to accounts, under their own "platform" key."""
    return f"{platform}:likes"


@dataclass(frozen=True)
class LikeSpec:
    """
    search_url: may contain {query} (URL-encoded term) and {tag} (term as a hashtag).
    post_url_re: matches a post URL, group 1 = post id (must also be a valid JS regex).
    labels / button_css / min_button_size: identify the not-yet-liked like button
        (see dom.find_like_button).
    scope_css: post page area holding the like button.
    """

    search_url: str
    post_url_re: str
    labels: Tuple[str, ...] = ()
    button_css: Optional[str] = None
    min_button_size: int = 0
    scope_css: Optional[str] = None
    results_scope_css: Optional[str] = "main"

    def post_id(self, url: str) -> Optional[str]:
        match = re.match(self.post_url_re, url, re.IGNORECASE)
        return match.group(1) if match else None

    def search_page(self, term: str) -> str:
        return self.search_url.format(query=quote_plus(term), tag=re.sub(r"\W", "", term))


class LikeSession(ActionSession):
    verb = "like"
    past_tense = "Liked"
    delay = AUTO_LIKE_DELAY

    def like(self, button: WebElement, post_id: str, url: str) -> bool:
        like = self.spec.like
        if not (
            simulate_click(self.driver, button, wait_time=5)
            and wait_until_liked(self.driver, button, like.labels)
        ):
            self.failed(post_id)
            return False

        self.store.mark(likes_store_key(self.spec.name), post_id, LIKED, url)
        self.succeeded(post_id)
        return True


def run_like(session: LikeSession, settings: dict) -> None:
    driver, spec, store = session.driver, session.spec, session.store
    like = spec.like
    store_key = likes_store_key(spec.name)
    terms = list(settings.get("search_terms") or ())
    if not terms:
        logger.warning("[%s] No search_terms configured", spec.name)
        return
    random.shuffle(terms)

    def posts(d):
        return collect_profile_links(d, like.post_url_re, like.results_scope_css)

    for term in terms:
        if session.done:
            return
        driver.get(like.search_page(term))
        if not wait_for(driver, posts, timeout=15):
            logger.info("[%s] No posts for %r", spec.name, term)
            continue
        scroll_to_bottom(driver, max_rounds=settings["search_scrolls"])

        candidates = [(like.post_id(url), url) for url, _ in posts(driver)]
        candidates = [(p, u) for p, u in candidates if p and not store.is_known(store_key, p)]
        # Don't always take the top results in the same order
        random.shuffle(candidates)
        logger.info("[%s] %r: %d new posts found", spec.name, term, len(candidates))

        for post_id, url in candidates[: draw(AUTO_LIKE_POSTS_PER_TERM)]:
            if session.done:
                return
            driver.get(url)
            button = wait_for(
                driver,
                lambda d: find_like_button(
                    d, like.labels, like.scope_css, like.button_css, like.min_button_size
                ),
                timeout=10,
            )
            if button is None:
                # Already liked, or the post layout isn't recognised
                logger.info("[%s] No like button on %s", spec.name, post_id)
                store.mark(store_key, post_id, SKIPPED_POST, url)
                continue

            time.sleep(draw(AUTO_LIKE_VIEW_DELAY))
            session.like(button, post_id, url)

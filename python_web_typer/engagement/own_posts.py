"""
Like and comment your own latest posts, each post once.

Only your own post list is opened (profile grid, channel videos, tracks): no
search, no other account's content.
"""

import logging
import time
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from ..config import AUTO_LIKE_VIEW_DELAY, AUTO_OWN_POSTS_DELAY, SCROLL_PAUSE
from ..humanize import draw
from ..task_engine_extension.tasks import scroll_to_bottom
from ..webpage_interactions.simulate_click import simulate_click
from .chat import type_and_submit
from .dom import (
    collect_profile_links,
    find_editable,
    find_like_button,
    find_visible,
    wait_for,
    wait_until_liked,
)
from .messages import pick_message, recent_messages
from .session import ActionSession

__all__ = ["OwnPostsSpec", "OwnPostsSession", "own_posts_store_key", "run_own_posts"]

logger = logging.getLogger(__name__)

HANDLED = "handled"
# Page scrolls tried while looking for the comment field (YouTube loads comments lazily)
_COMMENT_FIELD_SCROLLS = 10


def own_posts_store_key(platform: str) -> str:
    return f"{platform}:own-posts"


@dataclass(frozen=True)
class OwnPostsSpec:
    """
    posts_url: your post list ({me} = your account id). Posts are recognised
        with the platform's LikeSpec.post_url_re.
    comment_input_css: candidates for the comment field.
    comment_open_css: element clicked first to reveal the field (YouTube's
        "Add a comment..." placeholder). The page is scrolled until it shows up.
    comment_submit_labels: submit button labels, empty = submit with Enter.
    is_own_post: (post_id, me) -> bool, extra safety where the post URL names its owner.
    """

    posts_url: str
    comment_input_css: str
    posts_scope_css: Optional[str] = "main"
    comment_open_css: Optional[str] = None
    comment_submit_labels: Tuple[str, ...] = ()
    is_own_post: Optional[Callable[[str, str], bool]] = None


class OwnPostsSession(ActionSession):
    verb = "post update"
    past_tense = "Updated"
    delay = AUTO_OWN_POSTS_DELAY


def _comment_field(driver: WebDriver, own: OwnPostsSpec) -> Optional[WebElement]:
    """Scrolls down until the comment field (or its placeholder) appears."""
    for _ in range(_COMMENT_FIELD_SCROLLS):
        if own.comment_open_css:
            opener = find_visible(driver, own.comment_open_css)
            if opener is not None:
                simulate_click(driver, opener, wait_time=5)
                return wait_for(driver, lambda d: find_editable(d, own.comment_input_css), timeout=5)
        else:
            field = find_editable(driver, own.comment_input_css)
            if field is not None:
                return field
        driver.execute_script("window.scrollBy(0, window.innerHeight * 0.8);")
        time.sleep(draw(SCROLL_PAUSE))
    return None


def _like(session: OwnPostsSession) -> Optional[bool]:
    """True: liked. None: nothing to like (already liked). False: like failed."""
    like = session.spec.like
    button = wait_for(
        session.driver,
        lambda d: find_like_button(d, like.labels, like.scope_css, like.button_css, like.min_button_size),
        timeout=8,
    )
    if button is None:
        return None
    return simulate_click(session.driver, button, wait_time=5) and wait_until_liked(
        session.driver, button, like.labels
    )


def run_own_posts(session: OwnPostsSession, settings: dict, me: str) -> None:
    driver, spec, store = session.driver, session.spec, session.store
    own, like = spec.own_posts, spec.like
    store_key = own_posts_store_key(spec.name)

    def posts(d):
        return collect_profile_links(d, like.post_url_re, own.posts_scope_css)

    driver.get(own.posts_url.format(me=me))
    if not wait_for(driver, posts, timeout=15):
        logger.info("[%s] No post found on your profile", spec.name)
        return
    scroll_to_bottom(driver, max_rounds=settings["scrolls"])

    # Page order = newest first
    candidates = {}
    for url, _ in posts(driver):
        post_id = like.post_id(url)
        if not post_id or post_id in candidates or store.is_known(store_key, post_id):
            continue
        if own.is_own_post and not own.is_own_post(post_id, me):
            continue
        candidates[post_id] = url
    logger.info("[%s] %d of your posts not handled yet", spec.name, len(candidates))

    recent = recent_messages(settings["messages"])
    for post_id, url in candidates.items():
        if session.done:
            return
        driver.get(url)
        time.sleep(draw(AUTO_LIKE_VIEW_DELAY))
        actions = []

        if settings["like"]:
            liked = _like(session)
            if liked is False:
                session.failed(post_id)
                continue
            if liked:
                actions.append("liked")

        if settings["comment"]:
            field = _comment_field(driver, own)
            if field is None:
                logger.info("[%s] No comment field on %s (comments off?)", spec.name, post_id)
            else:
                message = pick_message(settings["messages"], recent)
                if not type_and_submit(driver, field, message, own.comment_submit_labels):
                    # Not recorded: retried next run (the like, if done, won't be redone)
                    session.failed(post_id)
                    continue
                actions.append(f"commented {message!r}")

        store.mark(store_key, post_id, HANDLED, url)
        if actions:
            session.succeeded(post_id, ": " + ", ".join(actions))
        else:
            logger.info("[%s] Nothing to do on %s", spec.name, post_id)

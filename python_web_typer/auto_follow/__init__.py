"""
Auto-follow accounts on social platforms, never following the same account twice,
and unfollow every account except a keep list.

Log in once per platform in the automation browser profile (python main.py login),
then run python main.py follow / unfollow. Settings live in config.AUTO_FOLLOW and
config.AUTO_UNFOLLOW.
"""

import logging
from typing import Dict, List, Optional, Set

from selenium.webdriver.remote.webdriver import WebDriver

from ..config import (
    AUTO_FOLLOW,
    AUTO_FOLLOW_DB_PATH,
    AUTO_FOLLOW_DEFAULTS,
    AUTO_UNFOLLOW,
    AUTO_UNFOLLOW_DEFAULTS,
)
from ..humanize import draw
from .engine import FollowSession, run_listing, run_search
from .platforms import PLATFORMS
from .store import FOLLOWED, UNFOLLOWED, FollowedStore
from .unfollow import UnfollowSession, normalize_keep_list, run_unfollow

__all__ = [
    "PLATFORMS",
    "FollowedStore",
    "platform_settings",
    "enabled_platforms",
    "auto_follow",
    "unfollow_settings",
    "keep_list",
    "auto_unfollow",
]

logger = logging.getLogger(__name__)


def platform_settings(platform: str) -> Dict:
    return {**AUTO_FOLLOW_DEFAULTS, **AUTO_FOLLOW.get(platform, {})}


def enabled_platforms() -> List[str]:
    return [name for name in PLATFORMS if platform_settings(name)["enabled"]]


def _quota(store: FollowedStore, platform: str, status: str, per_run, per_24h) -> int:
    # Both caps drawn anew each run, never above their configured max
    remaining_24h = draw(per_24h) - store.count_last_24h(platform, status)
    return min(draw(per_run), remaining_24h)


def auto_follow(
    driver: WebDriver, platform: str, store: Optional[FollowedStore] = None
) -> int:
    """
    Follows up to `max_follows` new accounts on `platform` (config.AUTO_FOLLOW),
    within `max_follows_per_24h`, both drawn at random for this run.
    Returns the number of accounts followed.
    """
    spec = PLATFORMS[platform]
    settings = platform_settings(platform)
    own_store = store is None
    store = store or FollowedStore(AUTO_FOLLOW_DB_PATH)

    try:
        quota = _quota(
            store, platform, FOLLOWED, settings["max_follows"], settings["max_follows_per_24h"]
        )
        if quota <= 0:
            logger.info("[%s] 24h follow cap reached, skipping", platform)
            return 0

        logger.info("[%s] Following up to %d accounts", platform, quota)
        session = FollowSession(driver, store, spec, quota)
        (run_listing if spec.listing_pages else run_search)(session, settings)
        logger.info("[%s] Done: %d followed", platform, session.followed)
        return session.followed
    finally:
        if own_store:
            store.close()


def unfollow_settings(platform: str) -> Dict:
    return {**AUTO_UNFOLLOW_DEFAULTS, **AUTO_UNFOLLOW.get(platform, {})}


def keep_list(platform: str) -> Set[str]:
    """
    Account ids never unfollowed on `platform` (own account included).

    Raises:
        ValueError: on a keep list entry that isn't a valid account.
    """
    settings = unfollow_settings(platform)
    entries = list(settings["keep"])
    if settings.get("own_account"):
        entries.append(settings["own_account"])
    return normalize_keep_list(PLATFORMS[platform], entries)


def auto_unfollow(
    driver: WebDriver,
    platform: str,
    dry_run: bool = False,
    store: Optional[FollowedStore] = None,
) -> int:
    """
    Unfollows up to `max_unfollows` accounts on `platform`, every account except
    the config.AUTO_UNFOLLOW keep list, within `max_unfollows_per_24h`.
    With `dry_run`, only logs which accounts would be unfollowed.
    Returns the number of accounts unfollowed (or that would be).
    """
    spec = PLATFORMS[platform]
    settings = unfollow_settings(platform)
    keep = keep_list(platform)  # validated before touching anything
    own_store = store is None
    store = store or FollowedStore(AUTO_FOLLOW_DB_PATH)

    try:
        quota = _quota(
            store, platform, UNFOLLOWED, settings["max_unfollows"], settings["max_unfollows_per_24h"]
        )
        if quota <= 0:
            logger.info("[%s] 24h unfollow cap reached, skipping", platform)
            return 0

        logger.info(
            "[%s] %sUnfollowing up to %d accounts, keeping %d",
            platform,
            "[dry-run] " if dry_run else "",
            quota,
            len(keep),
        )
        session = UnfollowSession(driver, store, spec, quota, dry_run)
        run_unfollow(session, settings, keep)
        logger.info("[%s] Done: %d unfollowed", platform, session.unfollowed)
        return session.unfollowed
    finally:
        if own_store:
            store.close()

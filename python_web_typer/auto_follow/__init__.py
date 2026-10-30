"""
Auto-follow accounts on social platforms, never following the same account twice.

Log in once per platform in the automation browser profile (python main.py login),
then run python main.py follow. Settings live in config.AUTO_FOLLOW.
"""

import logging
from typing import Dict, List, Optional

from selenium.webdriver.remote.webdriver import WebDriver

from ..config import AUTO_FOLLOW, AUTO_FOLLOW_DB_PATH, AUTO_FOLLOW_DEFAULTS
from .engine import FollowSession, run_listing, run_search
from .platforms import PLATFORMS
from .store import FollowedStore

__all__ = ["PLATFORMS", "FollowedStore", "platform_settings", "enabled_platforms", "auto_follow"]

logger = logging.getLogger(__name__)


def platform_settings(platform: str) -> Dict:
    return {**AUTO_FOLLOW_DEFAULTS, **AUTO_FOLLOW.get(platform, {})}


def enabled_platforms() -> List[str]:
    return [name for name in PLATFORMS if platform_settings(name)["enabled"]]


def auto_follow(
    driver: WebDriver, platform: str, store: Optional[FollowedStore] = None
) -> int:
    """
    Follows up to `max_follows` new accounts on `platform` (config.AUTO_FOLLOW),
    within `max_follows_per_24h`. Returns the number of accounts followed.
    """
    spec = PLATFORMS[platform]
    settings = platform_settings(platform)
    own_store = store is None
    store = store or FollowedStore(AUTO_FOLLOW_DB_PATH)

    try:
        remaining_24h = settings["max_follows_per_24h"] - store.count_followed_last_24h(platform)
        quota = min(settings["max_follows"], remaining_24h)
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

"""
Auto-follow accounts on social platforms, never following the same account twice,
unfollow every account except a keep list, like posts, post timed messages in
your own live chats, and like / comment your own posts.

Log in once per platform in the automation browser profile (python main.py login,
automatic with config.CREDENTIALS),
then run python main.py follow / unfollow / like / chat / own-posts. Settings
live in config.OWN_ACCOUNTS, AUTO_FOLLOW, AUTO_UNFOLLOW, AUTO_LIKE, AUTO_CHAT
and AUTO_OWN_POSTS.
"""

import logging
from typing import Dict, List, Optional, Set

from selenium.webdriver.remote.webdriver import WebDriver

from ..config import (
    AUTO_CHAT,
    AUTO_CHAT_DEFAULTS,
    AUTO_FOLLOW,
    AUTO_FOLLOW_DB_PATH,
    AUTO_FOLLOW_DEFAULTS,
    AUTO_LIKE,
    AUTO_LIKE_DEFAULTS,
    AUTO_OWN_POSTS,
    AUTO_OWN_POSTS_DEFAULTS,
    AUTO_UNFOLLOW,
    AUTO_UNFOLLOW_DEFAULTS,
    OWN_ACCOUNTS,
)
from ..humanize import draw
from .chat import chat_page_url, run_chat
from .engine import FollowSession, run_listing, run_search
from .login import BadCredentials, BotBlocked, auto_login, credentials, login_platforms
from .like import LIKED, LikeSession, likes_store_key, run_like
from .own_posts import OwnPostsSession, run_own_posts
from .platforms import PLATFORMS
from .store import FOLLOWED, UNFOLLOWED, FollowedStore
from .unfollow import UnfollowSession, normalize_keep_list, run_unfollow

__all__ = [
    "PLATFORMS",
    "BadCredentials",
    "BotBlocked",
    "auto_login",
    "credentials",
    "login_platforms",
    "FollowedStore",
    "platform_settings",
    "enabled_platforms",
    "auto_follow",
    "unfollow_settings",
    "keep_list",
    "auto_unfollow",
    "like_settings",
    "like_platforms",
    "auto_like",
    "chat_settings",
    "chat_platforms",
    "check_chat_settings",
    "auto_chat",
    "own_account",
    "own_posts_settings",
    "own_posts_platforms",
    "auto_own_posts",
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
        logger.info("[%s] Done: %d followed", platform, session.count)
        return session.count
    finally:
        if own_store:
            store.close()


def own_account(platform: str, override: str = "") -> Optional[str]:
    """
    Your account id on `platform`: `override`, else config.OWN_ACCOUNTS. None if unset.

    Raises:
        ValueError: if the configured value isn't a valid account of this platform.
    """
    entry = override or OWN_ACCOUNTS.get(platform, "")
    if not entry:
        return None
    account_id = PLATFORMS[platform].resolve_account(entry)
    if account_id is None:
        raise ValueError(f"[{platform}] own account not recognised: {entry!r}")
    return account_id


def unfollow_settings(platform: str) -> Dict:
    settings = {**AUTO_UNFOLLOW_DEFAULTS, **AUTO_UNFOLLOW.get(platform, {})}
    settings["own_account"] = settings["own_account"] or OWN_ACCOUNTS.get(platform, "")
    return settings


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
        session = UnfollowSession(driver, store, spec, quota, dry_run=dry_run)
        run_unfollow(session, settings, keep)
        logger.info("[%s] Done: %d unfollowed", platform, session.count)
        return session.count
    finally:
        if own_store:
            store.close()


def like_settings(platform: str) -> Dict:
    return {**AUTO_LIKE_DEFAULTS, **AUTO_LIKE.get(platform, {})}


def like_platforms() -> List[str]:
    return [name for name, spec in PLATFORMS.items() if spec.like and name in AUTO_LIKE]


def auto_like(
    driver: WebDriver, platform: str, store: Optional[FollowedStore] = None
) -> int:
    """
    Likes up to `max_likes` posts found with the search terms of
    config.AUTO_LIKE, within `max_likes_per_24h`. Returns the number of likes.
    """
    spec = PLATFORMS[platform]
    if spec.like is None:
        raise ValueError(f"Liking isn't supported on {platform}")
    settings = like_settings(platform)
    own_store = store is None
    store = store or FollowedStore(AUTO_FOLLOW_DB_PATH)

    try:
        quota = _quota(
            store,
            likes_store_key(platform),
            LIKED,
            settings["max_likes"],
            settings["max_likes_per_24h"],
        )
        if quota <= 0:
            logger.info("[%s] 24h like cap reached, skipping", platform)
            return 0

        logger.info("[%s] Liking up to %d posts", platform, quota)
        session = LikeSession(driver, store, spec, quota)
        run_like(session, settings)
        logger.info("[%s] Done: %d liked", platform, session.count)
        return session.count
    finally:
        if own_store:
            store.close()


def chat_settings(platform: str) -> Dict:
    settings = {**AUTO_CHAT_DEFAULTS, **AUTO_CHAT.get(platform, {})}
    settings["channel"] = settings["channel"] or OWN_ACCOUNTS.get(platform, "")
    return settings


def chat_platforms(configured_only: bool = False) -> List[str]:
    """Platforms with live chat support (with a channel / chat_url set, if asked)."""
    names = [name for name, spec in PLATFORMS.items() if spec.chat and name in AUTO_CHAT]
    if configured_only:
        names = [n for n in names if chat_settings(n)["channel"] or chat_settings(n)["chat_url"]]
    return names


def check_chat_settings(platforms: List[str]) -> None:
    """
    Raises:
        ValueError: on a missing / invalid channel or an empty message list.
    """
    for platform in platforms:
        settings = chat_settings(platform)
        if not settings["messages"]:
            raise ValueError(f"[{platform}] messages list is empty")
        if not chat_page_url(PLATFORMS[platform], settings):
            raise ValueError(f"[{platform}] set channel (or chat_url) in config.AUTO_CHAT")


def auto_chat(driver: WebDriver, platforms: List[str]) -> Dict[str, int]:
    """
    Posts messages from config.AUTO_CHAT in your own live chat on each platform
    (one tab each), every `interval`, up to `max_messages`. Returns sent counts.
    """
    check_chat_settings(platforms)
    counts = run_chat(driver, [PLATFORMS[p] for p in platforms], chat_settings)
    logger.info("Chat done: %s", counts)
    return counts


def own_posts_settings(platform: str) -> Dict:
    return {**AUTO_OWN_POSTS_DEFAULTS, **AUTO_OWN_POSTS.get(platform, {})}


def own_posts_platforms(configured_only: bool = False) -> List[str]:
    """Platforms supporting own-posts (with your account set, if asked)."""
    names = [n for n, spec in PLATFORMS.items() if spec.own_posts and n in AUTO_OWN_POSTS]
    if configured_only:
        names = [n for n in names if OWN_ACCOUNTS.get(n)]
    return names


def auto_own_posts(
    driver: WebDriver, platform: str, store: Optional[FollowedStore] = None
) -> int:
    """
    Likes and/or comments (config.AUTO_OWN_POSTS) up to `max_posts` of your own
    latest posts not handled yet. Returns the number of posts updated.

    Raises:
        ValueError: if your account isn't set or valid in config.OWN_ACCOUNTS.
    """
    spec = PLATFORMS[platform]
    settings = own_posts_settings(platform)
    me = own_account(platform)
    if not me:
        raise ValueError(f"[{platform}] set your account in config.OWN_ACCOUNTS")
    if settings["comment"] and not settings["messages"]:
        raise ValueError(f"[{platform}] messages list is empty")
    own_store = store is None
    store = store or FollowedStore(AUTO_FOLLOW_DB_PATH)

    try:
        quota = draw(settings["max_posts"])
        logger.info("[%s] Updating up to %d of your posts (%s)", platform, quota, me)
        session = OwnPostsSession(driver, store, spec, quota)
        run_own_posts(session, settings, me)
        logger.info("[%s] Done: %d posts updated", platform, session.count)
        return session.count
    finally:
        if own_store:
            store.close()

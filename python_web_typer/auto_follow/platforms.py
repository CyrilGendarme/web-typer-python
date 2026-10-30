"""
Per-platform definitions. Selectors rely on URLs and button labels (see dom.py);
the CSS scopes only narrow the search and fall back to the whole page.
"""

import logging
import random
from typing import Dict, Iterator

from selenium.webdriver.remote.webdriver import WebDriver

from ..task_engine_extension.tasks import scroll_to_bottom
from .dom import collect_profile_links, wait_for
from .engine import FOLLOW_LABELS, PlatformSpec

__all__ = ["PLATFORMS"]

logger = logging.getLogger(__name__)

# Trailing part of a profile URL: optional slash, optional query/fragment, nothing else
_END = r"/?(?:[?&#].*)?$"


# ---------------------------
# Facebook: friends of a random friend -> "Add friend"
# ---------------------------

_FACEBOOK_ADD_FRIEND_LABELS = (
    "add friend",
    "ajouter",
    "ajouter en ami",
    "ajouter en ami(e)",
    "ajouter comme ami(e)",
    "vriend toevoegen",
    "als vriend toevoegen",
    "freund/in hinzufügen",
    "als freund/in hinzufügen",
)


def _facebook_friends_url(account_id: str) -> str:
    if account_id.startswith("profile.php?id="):
        return f"https://www.facebook.com/{account_id}&sk=friends"
    return f"https://www.facebook.com/{account_id}/friends"


def _facebook_listing_pages(driver: WebDriver, spec: PlatformSpec, settings: dict) -> Iterator[str]:
    """Friend lists of your own friends, in random order."""
    driver.get("https://www.facebook.com/me/friends")

    def friends(d):
        return collect_profile_links(d, spec.profile_url_re, 'div[role="main"]')

    if not wait_for(driver, friends, timeout=15):
        logger.warning("[facebook] Your friend list could not be read (logged in?)")
        return
    scroll_to_bottom(driver, pause=1, max_rounds=3)

    own_friends = {spec.account_id(url) for url, _ in friends(driver)} - {None}
    logger.info("[facebook] %d friends found", len(own_friends))
    for account_id in random.sample(sorted(own_friends), len(own_friends)):
        yield _facebook_friends_url(account_id)


FACEBOOK = PlatformSpec(
    name="facebook",
    login_url="https://www.facebook.com/login",
    profile_url_re=r"^https://(?:www|web|m)\.facebook\.com/(profile\.php\?id=\d+|[a-z0-9.]{5,})" + _END,
    reserved_ids=frozenset(
        "friends groups pages watch marketplace events gaming messages notifications "
        "settings help policies privacy login reel reels stories story.php photo.php "
        "photos permalink.php hashtag search bookmarks saved ads business home.php "
        "memories fundraisers people profile.php".split()
    ),
    follow_labels=_FACEBOOK_ADD_FRIEND_LABELS,
    listing_pages=_facebook_listing_pages,
    listing_scope_css='div[role="main"]',
)


# ---------------------------
# Instagram: followers of seed accounts -> "Follow"
# ---------------------------


def _instagram_listing_pages(driver: WebDriver, spec: PlatformSpec, settings: dict) -> Iterator[str]:
    seeds = list(settings.get("seed_accounts") or ())
    if not seeds:
        logger.warning("[instagram] No seed_accounts configured")
        return
    random.shuffle(seeds)
    for seed in seeds:
        # Opens the profile with the followers dialog on top
        yield f"https://www.instagram.com/{seed.strip('@/ ')}/followers/"


INSTAGRAM = PlatformSpec(
    name="instagram",
    login_url="https://www.instagram.com/accounts/login/",
    profile_url_re=r"^https://www\.instagram\.com/([a-z0-9._]+)" + _END,
    reserved_ids=frozenset(
        "explore accounts direct reels reel p stories about legal developer web "
        "challenge emails session directory tv privacy terms".split()
    ),
    follow_labels=FOLLOW_LABELS,
    listing_pages=_instagram_listing_pages,
    listing_scope_css='div[role="dialog"]',
)


# ---------------------------
# Search-based platforms: search request -> accounts under max_followers
# ---------------------------

SOUNDCLOUD = PlatformSpec(
    name="soundcloud",
    login_url="https://soundcloud.com/signin",
    search_url="https://soundcloud.com/search/people?q={query}",
    profile_url_re=r"^https://soundcloud\.com/([a-z0-9_-]+)" + _END,
    reserved_ids=frozenset(
        "search discover stream upload you feed charts pages people terms-of-use imprint "
        "settings messages notifications signin mobile pro artists popular tags stations "
        "jobs creators premium go".split()
    ),
    results_scope_css="main, #content",
    profile_header_css=".profileHeader, .infoStats",
)

MIXCLOUD = PlatformSpec(
    name="mixcloud",
    login_url="https://www.mixcloud.com/",
    search_url="https://www.mixcloud.com/search/?q={query}&type=user",
    profile_url_re=r"^https://www\.mixcloud\.com/([a-z0-9_-]+)" + _END,
    reserved_ids=frozenset(
        "search discover upload dashboard live select about settings notifications "
        "messages favorites pro tag genres categories privacy terms faq".split()
    ),
)

YOUTUBE = PlatformSpec(
    name="youtube",
    login_url="https://accounts.google.com/ServiceLogin?service=youtube",
    # sp=EgIQAg%3D%3D: "Channels" filter
    search_url="https://www.youtube.com/results?search_query={query}&sp=EgIQAg%253D%253D",
    profile_url_re=r"^https://www\.youtube\.com/(@[^/?#]+|channel/[^/?#]+)" + _END,
    results_scope_css="ytd-search",
    profile_header_css="#page-header, ytd-c4-tabbed-header-renderer",
)

RUMBLE = PlatformSpec(
    name="rumble",
    login_url="https://rumble.com/login.php",
    search_url="https://rumble.com/search/channel?q={query}",
    profile_url_re=r"^https://rumble\.com/((?:c|user)/[^/?#]+)" + _END,
)

KICK = PlatformSpec(
    name="kick",
    login_url="https://kick.com/",
    search_url="https://kick.com/search?query={query}",
    profile_url_re=r"^https://kick\.com/([a-z0-9_-]+)" + _END,
    reserved_ids=frozenset(
        "search categories category browse following dashboard terms-of-service "
        "privacy-policy community-guidelines dmca-policy signup login video clips".split()
    ),
)

TWITCH = PlatformSpec(
    name="twitch",
    login_url="https://www.twitch.tv/login",
    search_url="https://www.twitch.tv/search?term={query}&type=channels",
    profile_url_re=r"^https://www\.twitch\.tv/([a-z0-9_]{3,25})" + _END,
    reserved_ids=frozenset(
        "directory search videos settings downloads jobs turbo prime subscriptions "
        "inventory wallet drops friends messages login signup store bits user moderator "
        "popout team collections broadcast creatorcamp following".split()
    ),
)


PLATFORMS: Dict[str, PlatformSpec] = {
    spec.name: spec
    for spec in (FACEBOOK, INSTAGRAM, SOUNDCLOUD, MIXCLOUD, YOUTUBE, RUMBLE, KICK, TWITCH)
}

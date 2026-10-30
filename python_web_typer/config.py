import logging
import os

DEBUG = True
DEBUG_DELAY = 2
LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO

# DOM observer: one JS round trip per poll, so sub-second polling is cheap enough
MUTATION_OBSERVER_BASE_POLL_INTERVAL = 0.5
# Consecutive WebDriver errors after which the observer assumes the browser is gone
MUTATION_OBSERVER_MAX_CONSECUTIVE_ERRORS = 5

DEFAULT_ELEMENT_WAIT_TIME = 10

# Browsers tried in this order, first installed one is used
# (values of webpage_interactions.browsers.Browser)
BROWSER_PRIORITY = ("chromium", "firefox", "chrome", "edge")

# Dedicated browser profiles for automation (one sub-folder per browser):
# keeps logins/cookies between runs
BROWSER_PROFILES_DIR = os.path.join(
    os.path.expanduser("~"), ".python_web_typer", "profiles"
)

# ---------------------------
# Auto-follow
# ---------------------------

# SQLite file listing every account already followed (or skipped), per platform
AUTO_FOLLOW_DB_PATH = os.path.join(
    os.path.expanduser("~"), ".python_web_typer", "followed_accounts.sqlite3"
)

# Random pause (seconds) after each follow / after each page load.
# Platforms flag accounts that follow in fast bursts: keep these generous.
AUTO_FOLLOW_FOLLOW_DELAY_RANGE = (8.0, 25.0)
AUTO_FOLLOW_BROWSE_DELAY_RANGE = (2.0, 5.0)

# Search requests, one is picked at random per round (search-based platforms)
AUTO_FOLLOW_SEARCH_TERMS = ["deep house", "techno mix", "lofi beats", "dj set"]

# Defaults for every platform, overridden per platform in AUTO_FOLLOW below
AUTO_FOLLOW_DEFAULTS = {
    "enabled": True,
    "max_follows": 10,  # accounts to follow per run
    "max_follows_per_24h": 30,  # hard cap over a rolling 24h window
    "max_followers": 1000,  # search platforms: only follow accounts below this
    "search_terms": AUTO_FOLLOW_SEARCH_TERMS,
    "search_scrolls": 3,  # result pages to load per search request
}

AUTO_FOLLOW = {
    # Friends of a random friend of yours -> "Add friend"
    "facebook": {"max_follows": 5, "max_follows_per_24h": 15},
    # Followers of these accounts -> "Follow"
    "instagram": {"max_follows_per_24h": 40, "seed_accounts": []},
    "soundcloud": {"max_followers": 500},
    "mixcloud": {"max_followers": 500},
    "youtube": {"max_followers": 1000},
    "rumble": {"max_followers": 1000},
    "kick": {"max_followers": 1000},
    "twitch": {"max_followers": 1000},
}

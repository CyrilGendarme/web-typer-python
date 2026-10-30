"""
Settings.

Behaviour numbers are `Humanized(mean, max, min=0)`: a fresh random value is
drawn at every use, averaging `mean` and never above `max` (see humanize.py).
Technical limits (timeouts, error thresholds) are plain numbers.
"""

import logging
import os

from .humanize import Humanized

DEBUG = True
DEBUG_DELAY = Humanized(2.0, 4.0, min=0.5)  # pause between queued tasks (DEBUG only)
LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO

# DOM observer: one JS round trip per poll, so sub-second polling is cheap enough
MUTATION_OBSERVER_BASE_POLL_INTERVAL = Humanized(0.5, 0.9, min=0.2)
# Consecutive WebDriver errors after which the observer assumes the browser is gone
MUTATION_OBSERVER_MAX_CONSECUTIVE_ERRORS = 5

DEFAULT_ELEMENT_WAIT_TIME = 10

# Seconds between two typed characters
TYPING_DELAY = Humanized(0.08, 0.2, min=0.03)
# Seconds waited after each scroll (lets lazy content load, reading time)
SCROLL_PAUSE = Humanized(1.0, 2.5, min=0.4)

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

# Pause (seconds) after each follow / after each page load.
# Platforms flag accounts that follow in fast bursts: keep these generous.
AUTO_FOLLOW_FOLLOW_DELAY = Humanized(15.0, 35.0, min=6.0)
AUTO_FOLLOW_BROWSE_DELAY = Humanized(3.5, 8.0, min=1.5)
# Profiles opened per search request
AUTO_FOLLOW_PROFILE_VISITS_PER_TERM = Humanized(20, 30, min=5)
# Scrolls without any new account before leaving a list (friends, followers)
AUTO_FOLLOW_IDLE_SCROLLS = Humanized(3, 5, min=2)

# Search requests, one is picked at random per round (search-based platforms)
AUTO_FOLLOW_SEARCH_TERMS = ["deep house", "techno mix", "lofi beats", "dj set"]

# Defaults for every platform, overridden per platform in AUTO_FOLLOW below
AUTO_FOLLOW_DEFAULTS = {
    "enabled": True,
    "max_follows": Humanized(10, 15, min=1),  # accounts to follow per run
    "max_follows_per_24h": Humanized(30, 40),  # cap over a rolling 24h window
    # Search platforms: only follow accounts below this many followers
    "max_followers": Humanized(1000, 1500),
    "search_terms": AUTO_FOLLOW_SEARCH_TERMS,
    # Result pages loaded per search (Facebook: of your own friend list)
    "search_scrolls": Humanized(3, 6, min=1),
}

AUTO_FOLLOW = {
    # Friends of a random friend of yours -> "Add friend"
    "facebook": {
        "max_follows": Humanized(5, 8, min=1),
        "max_follows_per_24h": Humanized(15, 20),
    },
    # Followers of these accounts -> "Follow"
    "instagram": {"max_follows_per_24h": Humanized(40, 50), "seed_accounts": []},
    "soundcloud": {"max_followers": Humanized(500, 750)},
    "mixcloud": {"max_followers": Humanized(500, 750)},
    "youtube": {"max_followers": Humanized(1000, 1500)},
    "rumble": {"max_followers": Humanized(1000, 1500)},
    "kick": {"max_followers": Humanized(1000, 1500)},
    "twitch": {"max_followers": Humanized(1000, 1500)},
}

# ---------------------------
# Auto-unfollow: unfollows every followed account except the "keep" list
# ---------------------------

# Pause (seconds) after each unfollow
AUTO_UNFOLLOW_DELAY = Humanized(12.0, 30.0, min=4.0)

AUTO_UNFOLLOW_DEFAULTS = {
    "max_unfollows": Humanized(15, 25, min=1),  # accounts to unfollow per run
    "max_unfollows_per_24h": Humanized(50, 70),  # cap over a rolling 24h window
    # Accounts never unfollowed: usernames ("@name" or "name") or profile URLs.
    # An entry that can't be recognised aborts the platform (nothing unfollowed).
    "keep": [],
    # Your own username, required where the following list URL contains it
    "own_account": "",
}

AUTO_UNFOLLOW = {
    # Facebook: REMOVES FRIENDS (only undone by a new friend request)
    "facebook": {"max_unfollows": Humanized(5, 8, min=1), "max_unfollows_per_24h": Humanized(15, 20)},
    "instagram": {"own_account": ""},  # required
    "soundcloud": {"own_account": ""},  # required (profile URL name)
    "mixcloud": {"own_account": ""},  # required (profile URL name)
    "youtube": {},
    "rumble": {},
    "kick": {},
    "twitch": {},
}

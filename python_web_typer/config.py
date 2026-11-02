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

# Your own account per platform: "@name", "name" or profile URL. Used to find your
# following list (unfollow), your live chat (chat) and your posts (own-posts).
OWN_ACCOUNTS = {
    "facebook": "",
    "instagram": "",
    "soundcloud": "",
    "mixcloud": "",
    "youtube": "",  # "@handle"
    "rumble": "",
    "kick": "",
    "twitch": "",
}

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
    # Overrides OWN_ACCOUNTS (required for instagram, soundcloud, mixcloud)
    "own_account": "",
}

AUTO_UNFOLLOW = {
    # Facebook: REMOVES FRIENDS (only undone by a new friend request)
    "facebook": {"max_unfollows": Humanized(5, 8, min=1), "max_unfollows_per_24h": Humanized(15, 20)},
    "instagram": {},
    "soundcloud": {},
    "mixcloud": {},
    "youtube": {},
    "rumble": {},
    "kick": {},
    "twitch": {},
}

# ---------------------------
# Auto-like: posts found by search requests, never liked twice
# ---------------------------

# Seconds spent on a post before liking it (watching / listening / reading)
AUTO_LIKE_VIEW_DELAY = Humanized(10.0, 30.0, min=3.0)
# Pause (seconds) after each like
AUTO_LIKE_DELAY = Humanized(10.0, 25.0, min=4.0)
# Posts opened per search request
AUTO_LIKE_POSTS_PER_TERM = Humanized(8, 12, min=2)

AUTO_LIKE_DEFAULTS = {
    "max_likes": Humanized(15, 25, min=1),  # posts to like per run
    "max_likes_per_24h": Humanized(60, 80),  # cap over a rolling 24h window
    "search_terms": AUTO_FOLLOW_SEARCH_TERMS,  # Instagram: used as hashtags
    "search_scrolls": Humanized(2, 4, min=1),  # result pages loaded per search
}

AUTO_LIKE = {
    "instagram": {"max_likes_per_24h": Humanized(50, 70)},
    "youtube": {},
    "soundcloud": {},
}

# ---------------------------
# Auto-chat: timed messages in YOUR OWN live chats (one browser tab per platform)
# ---------------------------

# Messages picked at random, never one of the last few sent
AUTO_CHAT_MESSAGES = [
    "Thanks for tuning in!",
    "Enjoying the mix? Drop a follow so you don't miss the next one",
    "Tracklist and next dates on my profile",
]

AUTO_CHAT_DEFAULTS = {
    # Overrides OWN_ACCOUNTS. Or set "chat_url" to the chat page.
    "channel": "",
    "chat_url": "",
    "messages": AUTO_CHAT_MESSAGES,
    "interval": Humanized(600.0, 900.0, min=240.0),  # seconds between two messages
    "max_messages": Humanized(12, 18, min=1),  # messages per run
}

AUTO_CHAT = {
    "mixcloud": {},
    "youtube": {},  # the current live is found from your "@handle"
    "rumble": {},  # chat_url required: the URL of the live (it changes every stream)
    "twitch": {},
    "kick": {},
}

# ---------------------------
# Own posts: like and comment YOUR OWN latest posts (each post handled once)
# ---------------------------

# Comments picked at random, never one of the last few posted
AUTO_OWN_POSTS_MESSAGES = [
    "Full tracklist in the description",
    "Thanks for listening, more coming soon!",
    "Which track was your favourite?",
]

# Pause (seconds) between two posts
AUTO_OWN_POSTS_DELAY = Humanized(20.0, 45.0, min=8.0)

AUTO_OWN_POSTS_DEFAULTS = {
    "like": True,
    "comment": True,
    "messages": AUTO_OWN_POSTS_MESSAGES,
    "max_posts": Humanized(5, 8, min=1),  # posts handled per run
    "scrolls": Humanized(2, 4, min=1),  # pages of your post list loaded
}

AUTO_OWN_POSTS = {
    "instagram": {},
    "youtube": {},
    "soundcloud": {},
}

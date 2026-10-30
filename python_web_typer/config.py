import logging

DEBUG = True
DEBUG_DELAY = 2
LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO

# DOM observer: one JS round trip per poll, so sub-second polling is cheap enough
MUTATION_OBSERVER_BASE_POLL_INTERVAL = 0.5
# Consecutive WebDriver errors after which the observer assumes the browser is gone
MUTATION_OBSERVER_MAX_CONSECUTIVE_ERRORS = 5

DEFAULT_ELEMENT_WAIT_TIME = 10

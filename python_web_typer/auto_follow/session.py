"""Quota, pacing and failure tracking shared by the follow / unfollow / like runs."""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, ClassVar

from selenium.webdriver.remote.webdriver import WebDriver

from ..humanize import Number, draw
from .store import FollowedStore

__all__ = ["ActionSession"]

logger = logging.getLogger(__name__)

# Actions not confirmed by the page, in a row, before giving up on a platform
# (usually: logged out, rate limited or action blocked)
_MAX_CONSECUTIVE_FAILURES = 3


@dataclass
class ActionSession:
    """
    One run of an action on one platform. Subclasses set `verb`, `past_tense`
    and `delay` (pause after each successful action).
    """

    verb: ClassVar[str] = "action"
    past_tense: ClassVar[str] = "Done"
    delay: ClassVar[Number] = 0

    driver: WebDriver
    store: FollowedStore
    spec: Any  # engine.PlatformSpec
    quota: int
    dry_run: bool = False
    count: int = 0
    aborted: bool = False
    _failures: int = field(default=0, repr=False)

    @property
    def done(self) -> bool:
        return self.aborted or self.count >= self.quota

    def failed(self, target: str) -> None:
        name = self.spec.name
        self._failures += 1
        logger.warning("[%s] %s of %s not confirmed", name, self.verb.capitalize(), target)
        if self._failures >= _MAX_CONSECUTIVE_FAILURES:
            self.aborted = True
            logger.error(
                "[%s] %d %ss in a row failed, stopping. Logged in? "
                "(python main.py login %s) Rate limited?",
                name,
                self._failures,
                self.verb,
                name,
            )

    def succeeded(self, target: str, details: str = "") -> None:
        self._failures = 0
        self.count += 1
        logger.info(
            "[%s] %s%s %s (%d/%d)%s",
            self.spec.name,
            "[dry-run] Would have " if self.dry_run else "",
            self.past_tense.lower() if self.dry_run else self.past_tense,
            target,
            self.count,
            self.quota,
            details,
        )
        if not self.done and not self.dry_run:
            time.sleep(draw(self.delay))

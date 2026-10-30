"""
Persistent record of the accounts already handled, so none is followed twice.

SQLite (stdlib): atomic writes survive a crash mid-run, the primary key
prevents duplicates, and lookups stay instant as the list grows.
"""

import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..config import AUTO_FOLLOW_DB_PATH

__all__ = ["FOLLOWED", "SKIPPED", "FollowedStore"]

logger = logging.getLogger(__name__)

FOLLOWED = "followed"
SKIPPED = "skipped"  # e.g. too many followers, re-evaluated if max_followers is raised

_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    platform        TEXT NOT NULL,
    account_id      TEXT NOT NULL,
    status          TEXT NOT NULL,
    url             TEXT,
    follower_count  INTEGER,
    updated_at      TEXT NOT NULL,
    PRIMARY KEY (platform, account_id)
);
CREATE INDEX IF NOT EXISTS accounts_followed_at
    ON accounts (platform, status, updated_at);
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FollowedStore:
    def __init__(self, path: str = AUTO_FOLLOW_DB_PATH):
        if os.path.dirname(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self._conn = sqlite3.connect(path)
        self._conn.executescript(_SCHEMA)

    def __enter__(self) -> "FollowedStore":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    def is_known(
        self, platform: str, account_id: str, max_followers: Optional[int] = None
    ) -> bool:
        """
        True if the account was followed, or skipped for a reason that still holds
        (a skip because of too many followers is reconsidered when `max_followers`
        is now above the recorded count).
        """
        row = self._conn.execute(
            "SELECT status, follower_count FROM accounts WHERE platform = ? AND account_id = ?",
            (platform, account_id),
        ).fetchone()
        if row is None:
            return False
        status, follower_count = row
        if status == SKIPPED and max_followers is not None and follower_count is not None:
            return follower_count >= max_followers
        return True

    def mark(
        self,
        platform: str,
        account_id: str,
        status: str,
        url: Optional[str] = None,
        follower_count: Optional[int] = None,
    ) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO accounts (platform, account_id, status, url, follower_count, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (platform, account_id) DO UPDATE SET
                    status = excluded.status,
                    url = COALESCE(excluded.url, url),
                    follower_count = COALESCE(excluded.follower_count, follower_count),
                    updated_at = excluded.updated_at
                """,
                (platform, account_id, status, url, follower_count, _now().isoformat()),
            )

    def count_followed_since(self, platform: str, since: datetime) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) FROM accounts WHERE platform = ? AND status = ? AND updated_at >= ?",
            (platform, FOLLOWED, since.isoformat()),
        ).fetchone()[0]

    def count_followed_last_24h(self, platform: str) -> int:
        return self.count_followed_since(platform, _now() - timedelta(hours=24))

    def stats(self) -> dict:
        """{platform: {status: count}}"""
        result: dict = {}
        for platform, status, count in self._conn.execute(
            "SELECT platform, status, COUNT(*) FROM accounts GROUP BY platform, status"
        ):
            result.setdefault(platform, {})[status] = count
        return result

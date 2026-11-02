"""Random message picking without short-term repeats (chat, comments)."""

import random
from collections import deque
from typing import Deque, Sequence

__all__ = ["recent_messages", "pick_message"]

# How many of the last messages are never repeated (capped to len(messages) - 1)
_NO_REPEAT_WINDOW = 3


def recent_messages(messages: Sequence[str]) -> Deque[str]:
    """Memory of the last messages picked from `messages`, for `pick_message`."""
    return deque(maxlen=max(0, min(_NO_REPEAT_WINDOW, len(messages) - 1)))


def pick_message(messages: Sequence[str], recent: Deque[str]) -> str:
    candidates = [m for m in messages if m not in recent] or list(messages)
    message = random.choice(candidates)
    recent.append(message)
    return message

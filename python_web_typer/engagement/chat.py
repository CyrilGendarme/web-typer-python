"""
Timed messages in your own live chats.

Only the chat of the configured channel (or chat_url) is ever opened: no search,
no other streamer's chat. Several platforms run side by side (multistream), one
browser tab each, every platform on its own randomised interval.
"""

import logging
import re
import time
from dataclasses import dataclass
from typing import Callable, Deque, Dict, Iterable, Optional, Sequence

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver

from ..cancellation import cancellable_sleep
from ..humanize import draw
from ..webpage_interactions.simulate_click import simulate_click
from ..webpage_interactions.simulate_typing import simulate_typing
from .dom import find_editable, find_follow_button, wait_for, wait_until_emptied
from .messages import pick_message, recent_messages
from .session import ActionSession

__all__ = [
    "ChatSpec",
    "ChatSession",
    "chat_page_url",
    "youtube_live_chat_url",
    "type_and_submit",
    "run_chat",
]

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ChatSpec:
    """
    chat_url: chat page of a channel ({channel} = account id). None when the URL
        can't be derived from the channel (setting chat_url is then required).
    input_css: candidates for the message field (first visible editable one wins).
    resolve_url: turns the opened page into the actual chat page URL, or None
        when the channel isn't live (e.g. YouTube: /@handle/live -> live_chat popout).
    """

    chat_url: Optional[str]
    input_css: str = 'textarea, [contenteditable="true"]'
    resolve_url: Optional[Callable[[WebDriver], Optional[str]]] = None


def youtube_live_chat_url(driver: WebDriver) -> Optional[str]:
    """On /@handle/live, YouTube redirects to the current live's watch page."""
    match = wait_for(
        driver, lambda d: re.search(r"[?&]v=([\w-]{11})", d.current_url), timeout=10
    )
    if not match:
        return None
    return f"https://www.youtube.com/live_chat?is_popout=1&v={match.group(1)}"


def chat_page_url(spec, settings: dict) -> Optional[str]:
    """
    Chat URL from the settings (chat_url, else channel).

    Raises:
        ValueError: if the channel isn't a valid account of this platform.
    """
    if settings.get("chat_url"):
        return settings["chat_url"]
    channel = settings.get("channel")
    if not channel or not spec.chat.chat_url:
        return None
    account_id = spec.resolve_account(channel)
    if account_id is None:
        raise ValueError(f"[{spec.name}] channel not recognised: {channel!r}")
    return spec.chat.chat_url.format(channel=account_id)


class ChatSession(ActionSession):
    verb = "message"
    past_tense = "Sent"
    delay = 0  # pacing is handled by run_chat (per platform interval)


def type_and_submit(
    driver: WebDriver, field, message: str, submit_labels: Sequence[str] = ()
) -> bool:
    """
    Types `message` like a person, then submits with Enter, or with the button
    labelled `submit_labels` (looked up after typing: it is often disabled before).
    True once the field emptied, i.e. the page accepted the message.
    """
    simulate_typing(
        driver, field, message, shall_focus_out_after_typing=False, clear_first=False
    )
    if not submit_labels:
        field.send_keys(Keys.ENTER)
    else:
        submit = wait_for(driver, lambda d: find_follow_button(d, submit_labels), timeout=5)
        if submit is None or not simulate_click(driver, submit, shall_scroll=False, wait_time=5):
            return False
    return wait_until_emptied(driver, field)


def _send(driver: WebDriver, spec, message: str) -> Optional[bool]:
    """True: sent. False: typed but not sent. None: no chat field (stream ended?)."""
    field = wait_for(driver, lambda d: find_editable(d, spec.chat.input_css), timeout=15)
    if field is None:
        return None
    return type_and_submit(driver, field, message)


def _open_chat(driver: WebDriver, spec, url: str, new_tab: bool) -> Optional[str]:
    """Opens the chat page, returns its window handle (None if not live)."""
    if new_tab:
        driver.switch_to.new_window("tab")
    driver.get(url)
    if spec.chat.resolve_url:
        resolved = spec.chat.resolve_url(driver)
        if resolved is None:
            logger.warning("[%s] Channel not live, skipping", spec.name)
            return None
        driver.get(resolved)
    return driver.current_window_handle


def run_chat(driver: WebDriver, specs: Iterable, settings_of: Callable[[str], dict]) -> Dict[str, int]:
    """Sends messages until every platform reached its quota or stopped. Returns sent counts."""
    sessions: Dict[str, ChatSession] = {}
    windows: Dict[str, str] = {}
    next_at: Dict[str, float] = {}
    recent: Dict[str, Deque[str]] = {}

    for spec in specs:
        settings = settings_of(spec.name)
        url = chat_page_url(spec, settings)
        if not url:
            logger.warning("[%s] No channel / chat_url configured, skipping", spec.name)
            continue
        window = _open_chat(driver, spec, url, new_tab=bool(windows))
        if window is None:
            continue
        windows[spec.name] = window
        sessions[spec.name] = ChatSession(driver, None, spec, quota=draw(settings["max_messages"]))
        next_at[spec.name] = time.monotonic() + draw(settings["interval"])
        recent[spec.name] = recent_messages(settings["messages"])
        logger.info(
            "[%s] Chat open, %d messages planned, first in %.0fs",
            spec.name,
            sessions[spec.name].quota,
            next_at[spec.name] - time.monotonic(),
        )

    active = [name for name, session in sessions.items() if not session.done]
    while active:
        name = min(active, key=next_at.__getitem__)
        cancellable_sleep(max(0.0, next_at[name] - time.monotonic()))

        session, settings = sessions[name], settings_of(name)
        driver.switch_to.window(windows[name])
        message = pick_message(settings["messages"], recent[name])

        sent = _send(driver, session.spec, message)
        if sent is None:
            logger.info("[%s] Chat field gone (stream ended?), stopping", name)
            session.aborted = True
        elif sent:
            session.succeeded(repr(message))
        else:
            session.failed(repr(message))

        next_at[name] = time.monotonic() + draw(settings["interval"])
        active = [n for n in active if not sessions[n].done]

    return {name: session.count for name, session in sessions.items()}

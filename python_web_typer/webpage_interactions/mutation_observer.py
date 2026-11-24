import logging
import threading
from typing import Any, Callable, Optional, Sequence

from selenium.common.exceptions import JavascriptException, WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

from ..humanize import Number, draw
from ..config import (
    MUTATION_OBSERVER_BASE_POLL_INTERVAL,
    MUTATION_OBSERVER_MAX_CONSECUTIVE_ERRORS,
)
from submodules.python_task_queue_scheduler.task_queue.tasks_queue import (
    TasksQueue,
)

__all__ = ["observe_dom_changes_with_trigger", "start_dom_observer_thread"]

logger = logging.getLogger(__name__)

# All checks run in a single round trip. Expensive reads (innerText forces a
# layout, outerHTML serialises the whole subtree) only happen when needed.
_DETECT_TRIGGER_JS = """
const [selector, classes, ids, texts, snippets] = arguments;
const root = document.querySelector(selector);
if (!root) return null;
for (const c of classes) if (root.getElementsByClassName(c).length) return `class '${c}'`;
for (const i of ids) if (document.getElementById(i)) return `id '${i}'`;
if (texts.length) {
    const text = root.innerText;
    for (const t of texts) if (text.includes(t)) return `inner text '${t}'`;
}
if (snippets.length) {
    const html = root.outerHTML;
    for (const s of snippets) if (html.includes(s)) return `HTML snippet '${s}'`;
}
return null;
"""


def observe_dom_changes_with_trigger(
    driver: WebDriver,
    watched_classes: Sequence[str] = (),
    watched_ids: Sequence[str] = (),
    watched_inner_text: Sequence[str] = (),
    watched_any_content_in_html: Sequence[str] = (),
    target_selector: str = "body",
    task_queue: Optional[TasksQueue] = None,
    poll_interval: Number = MUTATION_OBSERVER_BASE_POLL_INTERVAL,
    task_enum: Any = None,
    task_args: Sequence[Any] = (),
    task_to_top: bool = False,
    stop_event: Optional[threading.Event] = None,
    on_browser_gone: Optional[Callable[[], None]] = None,
    detector: Optional[Callable[[WebDriver], Optional[str]]] = None,
    on_detected: Optional[Callable[[str], None]] = None,
    on_cleared: Optional[Callable[[], None]] = None,
    clear_after_polls: int = 4,
) -> None:
    """
    Polls the page and enqueues `task_enum` when any watched item appears.

    The task is enqueued once per appearance (rising edge): it is re-armed only
    after the trigger has disappeared from the page. The loop ends when
    `stop_event` is set or the browser stops responding (window closed by the
    user, crash), in which case `on_browser_gone` is called.

    `detector(driver)` (description or None) replaces the watched_* lists when
    given. `on_detected(description)` is called when the trigger appears,
    `on_cleared()` when it is gone again, i.e. missing from `clear_after_polls`
    polls in a row (widgets such as Cloudflare Turnstile redraw themselves, which
    would otherwise read as solved for an instant).
    """
    stop_event = stop_event or threading.Event()
    script_args = (
        target_selector,
        list(watched_classes),
        list(watched_ids),
        list(watched_inner_text),
        list(watched_any_content_in_html),
    )
    was_detected = False
    misses = 0  # polls in a row without the trigger, while it is detected
    consecutive_errors = 0

    while not stop_event.wait(draw(poll_interval)):
        try:
            if detector is not None:
                match = detector(driver)
            else:
                match = driver.execute_script(_DETECT_TRIGGER_JS, *script_args)
            consecutive_errors = 0
        except JavascriptException as e:
            # Typically a page navigation in progress, retry on next poll
            logger.debug("[DOM OBSERVER] Script error, retrying: %s", e)
            continue
        except WebDriverException as e:
            consecutive_errors += 1
            if consecutive_errors >= MUTATION_OBSERVER_MAX_CONSECUTIVE_ERRORS:
                # Scripts also fail during a slow page change: make sure the window is really gone
                try:
                    driver.window_handles
                    logger.debug("[DOM OBSERVER] Browser still there, retrying: %s", str(e).splitlines()[0])
                    consecutive_errors = 0
                    continue
                except WebDriverException:
                    pass
                logger.info("[DOM OBSERVER] Browser unreachable, stopping: %s", str(e).splitlines()[0])
                if on_browser_gone and not stop_event.is_set():
                    on_browser_gone()
                return
            continue

        if not match:
            if was_detected:
                misses += 1
                if misses >= clear_after_polls:
                    was_detected = False
                    if on_cleared:
                        on_cleared()
            continue
        misses = 0
        if not was_detected:
            logger.info("[DOM OBSERVER] Trigger detected: %s", match)
            if on_detected:
                on_detected(match)
            if task_queue:
                task_queue.add_task(
                    task_enum,
                    *task_args,
                    check_duplicate=True,
                    add_to_top=task_to_top,
                )
            elif not on_detected:
                logger.info("[DOM OBSERVER] Action triggered! (No queue provided)")
        was_detected = True


def start_dom_observer_thread(
    driver: WebDriver, stop_event: Optional[threading.Event] = None, **kwargs: Any
) -> threading.Thread:
    """Starts `observe_dom_changes_with_trigger` in a daemon thread."""
    thread = threading.Thread(
        target=observe_dom_changes_with_trigger,
        args=(driver,),
        kwargs={**kwargs, "stop_event": stop_event},
        name="dom-observer",
        daemon=True,
    )
    thread.start()
    return thread


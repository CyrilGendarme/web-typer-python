import logging
import threading
from typing import Any, Optional, Sequence

from selenium.common.exceptions import JavascriptException, WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

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
    poll_interval: float = MUTATION_OBSERVER_BASE_POLL_INTERVAL,
    task_enum: Any = None,
    task_args: Sequence[Any] = (),
    task_to_top: bool = False,
    stop_event: Optional[threading.Event] = None,
) -> None:
    """
    Polls the page and enqueues `task_enum` when any watched item appears.

    The task is enqueued once per appearance (rising edge): it is re-armed only
    after the trigger has disappeared from the page. The loop ends when
    `stop_event` is set or the browser stops responding.
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
    consecutive_errors = 0

    while not stop_event.wait(poll_interval):
        try:
            match = driver.execute_script(_DETECT_TRIGGER_JS, *script_args)
            consecutive_errors = 0
        except JavascriptException as e:
            # Typically a page navigation in progress, retry on next poll
            logger.debug("[DOM OBSERVER] Script error, retrying: %s", e)
            continue
        except WebDriverException as e:
            consecutive_errors += 1
            if consecutive_errors >= MUTATION_OBSERVER_MAX_CONSECUTIVE_ERRORS:
                logger.info("[DOM OBSERVER] Browser unreachable, stopping: %s", e)
                return
            continue

        if match and not was_detected:
            logger.info("[DOM OBSERVER] Trigger detected: %s", match)
            if task_queue:
                task_queue.add_task(
                    task_enum,
                    *task_args,
                    check_duplicate=True,
                    add_to_top=task_to_top,
                )
            else:
                logger.info("[DOM OBSERVER] Action triggered! (No queue provided)")

        was_detected = bool(match)


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


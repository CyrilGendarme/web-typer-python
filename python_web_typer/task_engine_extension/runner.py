"""
Exception-safe queue execution.

The submodule's `process_queue` peeks the head task, runs it, then pops the head.
If the task raises, it is never removed (infinite retry), and if another thread
inserts a task at the top meanwhile, the wrong task gets popped. Popping first
avoids both.
"""

import logging
import time
from typing import Optional

from submodules.python_task_queue_scheduler.task_queue.tasks_queue import (
    TasksQueue,
)

__all__ = ["run_next_task", "run_all_tasks"]

logger = logging.getLogger(__name__)


def run_next_task(task_queue: TasksQueue) -> bool:
    """Pops and runs the next task. Returns False when the queue was empty."""
    task = task_queue.get_next_task(remove=True)
    if task is None:
        return False

    func, *args = task
    if not callable(func):
        logger.warning("Skipping non-callable task %r", func)
        return True

    try:
        func(*args)
    except Exception:
        logger.exception("Task %s failed", getattr(func, "__name__", func))
    return True


def run_all_tasks(
    task_queue: TasksQueue,
    priority_queue: Optional[TasksQueue] = None,
    pause_between_tasks: float = 0,
) -> None:
    """
    Runs `task_queue` until empty. Before each task, `priority_queue` (e.g. UI
    prompts raised by the DOM observer) is fully drained.
    """
    while True:
        if priority_queue is not None:
            while run_next_task(priority_queue):
                pass
        if not run_next_task(task_queue):
            return
        if pause_between_tasks:
            time.sleep(pause_between_tasks)

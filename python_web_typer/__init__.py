"""
Public API of python_web_typer.

Selenium-based helpers are imported eagerly. Desktop (pyautogui, keyboard) and
UI (PyQt6) helpers are loaded on first attribute access, so importing the
package doesn't require those libraries or a display.
"""

import importlib

from .task_engine_extension.enums_and_mappings import *
from .task_engine_extension.example_tasks import *
from .task_engine_extension.runner import *
from .task_engine_extension.tasks import *
from .webpage_interactions.browsers import *
from .webpage_interactions.mutation_observer import *
from .webpage_interactions.pick_webdriver import *
from .webpage_interactions.pick_webpage_element import *
from .webpage_interactions.simulate_click import *
from .webpage_interactions.simulate_typing import *

from submodules.python_task_queue_scheduler.task_queue import *
import submodules.python_task_queue_scheduler.task_queue as task_queue

_LAZY_MODULES = (
    ".desktop_windows_interactions.simulate_actions",
    ".desktop_windows_interactions.windows_selection",
    ".ui.captcha_wait",
)


def __getattr__(name: str):
    for module_name in _LAZY_MODULES:
        module = importlib.import_module(module_name, __name__)
        if name in getattr(module, "__all__", ()):
            return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

## This is project-specific
import os
import sys
from enum import Enum, auto

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

from task_engine.tasks import *
from ui.captcha_wait import wait_for_captcha


# Define an Enums for strong typing of the pseudo-signals
class UiToShow(Enum):
    CAPTCHA = auto()
    NONE = None  # Represents no UI


class WebpageInteraction(Enum):
    SLEEP = auto()
    CLICK_COOKIE_BTN = auto()
    TYPE_AND_CLICK_IN_SEARCH = auto()
    CLICK_ON_FIRST_RESULT = auto()
    NONE = None  # Represents no UI


webpage_interaction_func_map = {
    WebpageInteraction.SLEEP: sleep,
    WebpageInteraction.CLICK_COOKIE_BTN: click_cookie_btn,
    WebpageInteraction.TYPE_AND_CLICK_IN_SEARCH: type_and_click_in_search,
    WebpageInteraction.CLICK_ON_FIRST_RESULT: click_on_first_result,
}

ui_func_map = {
    UiToShow.CAPTCHA: wait_for_captcha,
}

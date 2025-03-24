from enum import Enum, auto
import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

from desktop_windows_interactions.simulate_actions import select_file_window
from task_engine_extension.tasks import *
from ui.captcha_wait import wait_for_captcha


# Define an Enums for strong typing of the pseudo-signals


# Common stuff
class CommonTasks(Enum):
    SLEEP = auto()
    CLICK_ELEMENT = auto()
    TYPE_INTO_ELEMENT = auto()
    DRAG_AND_DROP_FILE = auto()
    SELECT_FILE_THROUGH_WINDOW = auto()
    NO_OP = auto()  # Represents no operation


class UiToShow(Enum):
    CAPTCHA = auto()


class WebpageInteraction(Enum):
    CLICK_COOKIE_BTN = auto()
    TYPE_AND_CLICK_IN_SEARCH = auto()
    CLICK_ON_FIRST_RESULT = auto()


# Func mapping
common_func_map = {
    CommonTasks.SLEEP: sleep,
    CommonTasks.CLICK_ELEMENT: click_element,
    CommonTasks.TYPE_INTO_ELEMENT: type_into_element,
    CommonTasks.DRAG_AND_DROP_FILE: drag_and_drop_file,
    CommonTasks.SELECT_FILE_THROUGH_WINDOW: select_file_window,
    CommonTasks.NO_OP: None,
}

webpage_interaction_func_map = {
    WebpageInteraction.CLICK_COOKIE_BTN: click_cookie_btn,
    WebpageInteraction.TYPE_AND_CLICK_IN_SEARCH: type_and_click_in_search,
    WebpageInteraction.CLICK_ON_FIRST_RESULT: click_on_first_result,
}

ui_func_map = {
    UiToShow.CAPTCHA: wait_for_captcha,
}

from enum import Enum, auto

from ..auto_follow import auto_follow, auto_like, auto_unfollow
from .example_tasks import (
    click_cookie_btn,
    click_on_first_result,
    type_and_click_in_search,
)
from .tasks import (
    access_url,
    click_element,
    drag_and_drop_file,
    scroll_to_bottom,
    select_file_through_window,
    sleep,
    type_into_element,
    type_keys,
    wait_for_captcha_task,
)

__all__ = [
    "CommonTasks",
    "UiToShow",
    "WebpageInteraction",
    "common_func_map",
    "webpage_interaction_func_map",
    "ui_func_map",
]


# Define an Enums for strong typing of the pseudo-signals


# Common stuff
class CommonTasks(Enum):
    SLEEP = auto()
    CLICK_ELEMENT = auto()
    TYPE_INTO_ELEMENT = auto()
    DRAG_AND_DROP_FILE = auto()
    SELECT_FILE_THROUGH_WINDOW = auto()
    TYPE_KEYS = auto()
    ACCESS_URL = auto()
    SCROLL_TO_BOTTOM = auto()
    AUTO_FOLLOW = auto()  # args: driver, platform name (see auto_follow.PLATFORMS)
    AUTO_UNFOLLOW = auto()  # args: driver, platform name, dry_run
    AUTO_LIKE = auto()  # args: driver, platform name
    NO_OP = auto()  # Represents no operation


class UiToShow(Enum):
    CAPTCHA = auto()


class WebpageInteraction(Enum):
    CLICK_COOKIE_BTN = auto()
    TYPE_AND_CLICK_IN_SEARCH = auto()
    CLICK_ON_FIRST_RESULT = auto()


def _no_op(*_args) -> None:
    pass


# Func mapping
common_func_map = {
    CommonTasks.SLEEP: sleep,
    CommonTasks.CLICK_ELEMENT: click_element,
    CommonTasks.TYPE_INTO_ELEMENT: type_into_element,
    CommonTasks.DRAG_AND_DROP_FILE: drag_and_drop_file,
    CommonTasks.SELECT_FILE_THROUGH_WINDOW: select_file_through_window,
    CommonTasks.TYPE_KEYS: type_keys,
    CommonTasks.ACCESS_URL: access_url,
    CommonTasks.SCROLL_TO_BOTTOM: scroll_to_bottom,
    CommonTasks.AUTO_FOLLOW: auto_follow,
    CommonTasks.AUTO_UNFOLLOW: auto_unfollow,
    CommonTasks.AUTO_LIKE: auto_like,
    # A callable (not None) so the queue can execute and dequeue it
    CommonTasks.NO_OP: _no_op,
}

webpage_interaction_func_map = {
    WebpageInteraction.CLICK_COOKIE_BTN: click_cookie_btn,
    WebpageInteraction.TYPE_AND_CLICK_IN_SEARCH: type_and_click_in_search,
    WebpageInteraction.CLICK_ON_FIRST_RESULT: click_on_first_result,
}

ui_func_map = {
    UiToShow.CAPTCHA: wait_for_captcha_task,
}

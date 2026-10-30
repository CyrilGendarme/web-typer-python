import logging
import threading

from python_web_typer.config import DEBUG, DEBUG_DELAY, LOG_LEVEL
from python_web_typer.task_engine_extension.enums_and_mappings import (
    CommonTasks,
    UiToShow,
    WebpageInteraction,
    common_func_map,
    ui_func_map,
    webpage_interaction_func_map,
)
from python_web_typer.task_engine_extension.runner import run_all_tasks
from python_web_typer.webpage_interactions.mutation_observer import (
    start_dom_observer_thread,
)
from python_web_typer.webpage_interactions.pick_webdriver import get_webdriver

from submodules.python_task_queue_scheduler.task_queue.tasks_queue import TasksQueue

logger = logging.getLogger(__name__)

WEBSITE = "https://www.google.com"
CAPTCHA_SPECIFIC_CLASSES = ["g-recaptcha"]
CAPTCHA_SPECIFIC_IDS = ["captcha-form", "recaptcha"]


def run_test() -> None:
    # Create queues
    tasks_queue = TasksQueue([webpage_interaction_func_map, common_func_map])
    ui_interaction_queue = TasksQueue([ui_func_map])

    driver = get_webdriver()
    stop_observer = threading.Event()

    try:
        driver.get(WEBSITE)

        # Add tasks to the queue
        tasks_queue.add_task(WebpageInteraction.CLICK_COOKIE_BTN, driver)
        tasks_queue.add_task(
            WebpageInteraction.TYPE_AND_CLICK_IN_SEARCH,
            driver,
            "Selenium WebDriver Python",
        )
        tasks_queue.add_task(WebpageInteraction.CLICK_ON_FIRST_RESULT, driver)
        tasks_queue.add_task(CommonTasks.SLEEP, 10)

        # Detect CAPTCHAs in the background and queue a UI prompt when one shows up
        start_dom_observer_thread(
            driver,
            stop_event=stop_observer,
            watched_classes=CAPTCHA_SPECIFIC_CLASSES,
            watched_ids=CAPTCHA_SPECIFIC_IDS,
            task_queue=ui_interaction_queue,
            task_enum=UiToShow.CAPTCHA,
        )

        # UI prompts (CAPTCHA) always run before the next page interaction
        run_all_tasks(
            tasks_queue,
            priority_queue=ui_interaction_queue,
            pause_between_tasks=DEBUG_DELAY if DEBUG else 0,
        )

    finally:
        stop_observer.set()
        driver.quit()


if __name__ == "__main__":
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)-7s [%(threadName)s] %(name)s: %(message)s",
    )
    # Selenium/urllib3 are very chatty at DEBUG
    logging.getLogger("selenium").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)
    run_test()

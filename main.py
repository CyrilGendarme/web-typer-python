import time
import threading
from selenium import webdriver

from python_web_typer.webpage_interactions.mutation_observer import (
    observe_dom_changes_with_trigger,
)
from python_web_typer.config import DEBUG_DELAY
from python_web_typer.task_engine_extension.tasks import *
from python_web_typer.task_engine_extension.enums_and_mappings import *

from submodules.python_task_queue_scheduler.task_queue.tasks_queue import (
    TasksQueue,
    process_queue,
)


def run_test():
    # Some vars
    website = "https://dttktt.sbv.gov.vn/webcenter/portal/en/home/rm/ir"
    CSV_FILE = r"C:\Users\CyrilGendarme\Desktop\temp3\myfile.csv"
    captcha_specific_classes = ["g-recaptcha"]
    captcha_specific_ids = ["captcha-form", "recaptcha"]

    # Create queues
    tasks_queue = TasksQueue([webpage_interaction_func_map])
    ui_interaction_queue = TasksQueue([ui_func_map])

    # Get the selenium webdriver
    driver = webdriver.Chrome()
    driver.get(website)

    # Add tasks to the queue
    tasks_queue.add_task(CommonTasks.SLEEP, 5)
    tasks_queue.add_task(WebpageInteraction.GET_INTEREST_RATE_TABLE_DATA, driver, CSV_FILE)
    tasks_queue.add_task(CommonTasks.SLEEP, 5)

    # Start the observer thread to detect CAPTCHA
    observer_thread = threading.Thread(
        target=observe_dom_changes_with_trigger,
        args=(
            driver,
            captcha_specific_classes,
            captcha_specific_ids,
            [],
            [],
            "body",
            ui_interaction_queue,
            1,
            UiToShow.CAPTCHA,
            [],
            False,
        ),
        daemon=True,
    )
    observer_thread.start()

    time.sleep(DEBUG_DELAY)

    try:
        time.sleep(DEBUG_DELAY)

        while not len(tasks_queue.task_queue) == 0:
            process_queue(tasks_queue)
            time.sleep(DEBUG_DELAY)
            process_queue(ui_interaction_queue)

    finally:
        driver.quit()


if __name__ == "__main__":
    run_test()

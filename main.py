import time
import threading
from selenium import webdriver
from task_engine.tasks_queue import TasksQueue, process_queue
from webpage_interactions.mutation_observer import observe_dom_changes_with_trigger
from config import DEBUG_DELAY
from task_engine.tasks import *
from task_engine.enums_and_mappings import *


def run_test():
    # Some vars
    website = "https://www.google.com"
    captcha_specific_classes = ["g-recaptcha"]
    captcha_specific_ids = ["captcha-form", "recaptcha"]

    # Create queues
    tasks_queue = TasksQueue(webpage_interaction_func_map)
    ui_interaction_queue = TasksQueue(ui_func_map)

    # Get the selenium webdriver
    driver = webdriver.Chrome()
    driver.get(website)

    # Add tasks to the queue
    tasks_queue.add_task(WebpageInteraction.CLICK_COOKIE_BTN, driver)
    tasks_queue.add_task(
        WebpageInteraction.TYPE_AND_CLICK_IN_SEARCH,
        driver,
        "Selenium WebDriver Python",
    )
    tasks_queue.add_task(WebpageInteraction.CLICK_ON_FIRST_RESULT, driver)
    tasks_queue.add_task(WebpageInteraction.SLEEP, 10)

    # Start the observer thread to detect CAPTCHA
    observer_thread = threading.Thread(
        target=observe_dom_changes_with_trigger,
        args=(
            driver,
            captcha_specific_classes,
            captcha_specific_ids,
            "body",
            ui_interaction_queue,
            1,
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

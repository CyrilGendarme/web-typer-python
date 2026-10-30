"""
Usage:
    python main.py login [platform ...]    log in once, kept in the browser profile
    python main.py follow [platform ...]   auto-follow (default: enabled platforms)
    python main.py unfollow platform ... [--dry-run] [--yes]
                                           unfollow everyone except the keep list
    python main.py stats                   accounts followed/skipped per platform
    python main.py demo                    Google search demo
"""

import argparse
import logging
import threading
from contextlib import contextmanager

from python_web_typer.auto_follow import (
    PLATFORMS,
    FollowedStore,
    enabled_platforms,
    keep_list,
)
from python_web_typer.config import AUTO_FOLLOW_DB_PATH, DEBUG, DEBUG_DELAY, LOG_LEVEL
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

DEMO_WEBSITE = "https://www.google.com"
# reCAPTCHA, hCaptcha, Cloudflare Turnstile / challenge page
CAPTCHA_SPECIFIC_CLASSES = ["g-recaptcha", "h-captcha", "cf-turnstile"]
CAPTCHA_SPECIFIC_IDS = ["captcha-form", "recaptcha", "challenge-form"]


@contextmanager
def browser_session():
    """
    Yields (driver, tasks_queue) with a CAPTCHA observer running: when a CAPTCHA
    shows up, a "solved?" prompt is queued ahead of the next task.
    """
    tasks_queue = TasksQueue([webpage_interaction_func_map, common_func_map])
    ui_interaction_queue = TasksQueue([ui_func_map])
    driver = get_webdriver()
    stop_observer = threading.Event()

    try:
        start_dom_observer_thread(
            driver,
            stop_event=stop_observer,
            watched_classes=CAPTCHA_SPECIFIC_CLASSES,
            watched_ids=CAPTCHA_SPECIFIC_IDS,
            task_queue=ui_interaction_queue,
            task_enum=UiToShow.CAPTCHA,
        )
        yield driver, tasks_queue

        run_all_tasks(
            tasks_queue,
            priority_queue=ui_interaction_queue,
            pause_between_tasks=DEBUG_DELAY if DEBUG else 0,
        )
    finally:
        stop_observer.set()
        driver.quit()


def run_demo() -> None:
    with browser_session() as (driver, tasks_queue):
        driver.get(DEMO_WEBSITE)
        tasks_queue.add_task(WebpageInteraction.CLICK_COOKIE_BTN, driver)
        tasks_queue.add_task(
            WebpageInteraction.TYPE_AND_CLICK_IN_SEARCH,
            driver,
            "Selenium WebDriver Python",
        )
        tasks_queue.add_task(WebpageInteraction.CLICK_ON_FIRST_RESULT, driver)
        tasks_queue.add_task(CommonTasks.SLEEP, 10)


def run_follow(platforms) -> None:
    with browser_session() as (driver, tasks_queue):
        for platform in platforms:
            tasks_queue.add_task(CommonTasks.AUTO_FOLLOW, driver, platform)


def confirm_unfollow(platforms, dry_run: bool, assume_yes: bool) -> bool:
    """Validates the keep lists, then asks for confirmation (unfollows are hard to undo)."""
    for platform in platforms:
        keep = keep_list(platform)  # raises on an invalid entry
        warning = "  <- EMPTY: every account will be unfollowed" if not keep else ""
        print(f"{platform:<12} keeping {len(keep)} account(s){warning}")
        if platform == "facebook":
            print(f"{'':<12} Facebook: this REMOVES FRIENDS")
    if dry_run or assume_yes:
        return True
    return input("Type 'unfollow' to proceed: ").strip().lower() == "unfollow"


def run_unfollow(platforms, dry_run: bool) -> None:
    with browser_session() as (driver, tasks_queue):
        for platform in platforms:
            tasks_queue.add_task(CommonTasks.AUTO_UNFOLLOW, driver, platform, dry_run)


def run_login(platforms) -> None:
    """Opens each login page and waits: the session is saved in the browser profile."""
    driver = get_webdriver()
    try:
        for platform in platforms:
            driver.get(PLATFORMS[platform].login_url)
            input(f"Log in to {platform} in the browser, then press Enter...")
    finally:
        driver.quit()


def show_stats() -> None:
    with FollowedStore(AUTO_FOLLOW_DB_PATH) as store:
        stats = store.stats()
    if not stats:
        print("No account handled yet.")
    for platform, counts in sorted(stats.items()):
        print(f"{platform:<12} " + ", ".join(f"{s}: {n}" for s, n in sorted(counts.items())))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("login", "follow"):
        command = commands.add_parser(name)
        command.add_argument(
            "platforms", nargs="*", metavar="platform", help=", ".join(PLATFORMS)
        )
    unfollow = commands.add_parser("unfollow")
    unfollow.add_argument("platforms", nargs="+", metavar="platform", help=", ".join(PLATFORMS))
    unfollow.add_argument("--dry-run", action="store_true", help="only list who would be unfollowed")
    unfollow.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    commands.add_parser("stats")
    commands.add_parser("demo")

    args = parser.parse_args()
    unknown = set(getattr(args, "platforms", ())) - set(PLATFORMS)
    if unknown:
        parser.error(f"unknown platform(s): {', '.join(sorted(unknown))} (choose from {', '.join(PLATFORMS)})")
    return args


if __name__ == "__main__":
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)-7s [%(threadName)s] %(name)s: %(message)s",
    )
    # Selenium/urllib3 are very chatty at DEBUG
    logging.getLogger("selenium").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)

    args = parse_args()
    if args.command == "demo":
        run_demo()
    elif args.command == "stats":
        show_stats()
    elif args.command == "login":
        run_login(args.platforms or list(PLATFORMS))
    elif args.command == "unfollow":
        try:
            confirmed = confirm_unfollow(args.platforms, args.dry_run, args.yes)
        except ValueError as e:
            raise SystemExit(f"Invalid config.AUTO_UNFOLLOW: {e}")
        if not confirmed:
            raise SystemExit("Aborted, nothing unfollowed.")
        run_unfollow(args.platforms, args.dry_run)
    else:
        run_follow(args.platforms or enabled_platforms())

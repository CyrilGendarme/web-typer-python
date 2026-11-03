"""
Usage:
    python main.py login [platform ...]    log in once (config.CREDENTIALS), kept in the browser profile
    python main.py login --by-hand platform ...
                                           log in yourself in a plain (not automated) window
    python main.py follow [platform ...]   auto-follow (default: enabled platforms)
    python main.py unfollow platform ... [--dry-run] [--yes]
                                           unfollow everyone except the keep list
    python main.py like [platform ...]     like posts (instagram, youtube, soundcloud)
    python main.py chat [platform ...]     timed messages in your own live chats
    python main.py own-posts [platform ...]
                                           like / comment your own latest posts
    python main.py stats                   accounts followed/skipped per platform
    python main.py gui                     control panel (settings, actions, logs)
    python main.py demo                    Google search demo
"""

import argparse
import logging
import queue
import sys
import threading
from contextlib import contextmanager
from typing import Optional

from selenium.common.exceptions import WebDriverException

from python_web_typer.engagement import (
    PLATFORMS,
    BadCredentials,
    BotBlocked,
    FollowedStore,
    auto_login,
    credentials,
    chat_platforms,
    check_chat_settings,
    enabled_platforms,
    keep_list,
    like_platforms,
    own_account,
    own_posts_platforms,
)
from python_web_typer.cancellation import (
    Cancelled,
    hold_actions,
    release_actions,
    request_cancel,
)
from python_web_typer.config import (
    AUTO_FOLLOW_DB_PATH,
    DEBUG,
    DEBUG_DELAY,
    LOG_LEVEL,
)
from python_web_typer.task_engine_extension.enums_and_mappings import (
    CommonTasks,
    WebpageInteraction,
    common_func_map,
    ui_func_map,
    webpage_interaction_func_map,
)
from python_web_typer.task_engine_extension.runner import run_all_tasks
from python_web_typer.webpage_interactions.human_check import find_human_check
from python_web_typer.webpage_interactions.mutation_observer import (
    start_dom_observer_thread,
)
from python_web_typer.webpage_interactions.pick_webdriver import (
    get_webdriver,
    open_profile_browser,
)

from submodules.python_task_queue_scheduler.task_queue.tasks_queue import TasksQueue

logger = logging.getLogger(__name__)

DEMO_WEBSITE = "https://www.google.com"


def _on_browser_gone() -> None:
    logger.info("Browser window closed, stopping")
    request_cancel()


@contextmanager
def browser_session():
    """
    Yields (driver, tasks_queue) with a CAPTCHA observer running: when a CAPTCHA
    or verification shows up, the running task waits at its next step until it
    is solved in the browser.
    """
    tasks_queue = TasksQueue([webpage_interaction_func_map, common_func_map])
    ui_interaction_queue = TasksQueue([ui_func_map])
    driver = get_webdriver()
    stop_observer = threading.Event()

    try:
        start_dom_observer_thread(
            driver,
            stop_event=stop_observer,
            detector=find_human_check,
            on_detected=_hold_for_human_check,
            on_cleared=release_actions,
            on_browser_gone=_on_browser_gone,
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


def run_like(platforms) -> None:
    with browser_session() as (driver, tasks_queue):
        for platform in platforms:
            tasks_queue.add_task(CommonTasks.AUTO_LIKE, driver, platform)


def run_chat(platforms) -> None:
    # A single task: the platforms run side by side, one tab each
    with browser_session() as (driver, tasks_queue):
        tasks_queue.add_task(CommonTasks.AUTO_CHAT, driver, platforms)


def run_own_posts(platforms) -> None:
    with browser_session() as (driver, tasks_queue):
        for platform in platforms:
            tasks_queue.add_task(CommonTasks.AUTO_OWN_POSTS, driver, platform)


# Lines typed in the terminal, read by a background thread so that waiting for
# Enter can also notice a closed browser
_typed_lines: "queue.Queue[str]" = queue.Queue()
_stdin_reader: Optional[threading.Thread] = None


def _read_stdin() -> None:
    for line in sys.stdin:
        _typed_lines.put(line)


def wait_for_enter(driver, prompt: str) -> bool:
    """True once Enter is pressed, False if the browser window was closed meanwhile."""
    global _stdin_reader
    if _stdin_reader is None:
        _stdin_reader = threading.Thread(target=_read_stdin, name="stdin", daemon=True)
        _stdin_reader.start()
    print(prompt, end="", flush=True)
    while True:
        try:
            _typed_lines.get(timeout=1)
            return True
        except queue.Empty:
            try:
                driver.current_window_handle
            except WebDriverException:
                print()
                return False


def _hold_for_human_check(description: str) -> None:
    """Observer: a CAPTCHA / verification showed. The action waits at its next step until solved."""
    hold_actions(description)
    print(f"\a\n>>> {description}: solve it in the browser, the action goes on afterwards.")


def run_login(platforms) -> None:
    """
    Logs in with config.CREDENTIALS, or opens the login page and waits when no
    credentials are set or the automatic login got blocked. The session is
    saved in the browser profile.
    """
    driver = get_webdriver()
    stop_observer = threading.Event()
    try:
        # Only watches the browser: closing it stops a running automatic login
        start_dom_observer_thread(
            driver,
            stop_event=stop_observer,
            detector=find_human_check,
            on_detected=_hold_for_human_check,
            on_cleared=release_actions,
            on_browser_gone=_on_browser_gone,
        )
        for platform in platforms:
            if not all(credentials(platform).values()):
                driver.get(PLATFORMS[platform].login_url)
            else:
                try:
                    if auto_login(driver, platform):
                        continue
                except BadCredentials as e:
                    print(f"\n!!! {e}\n    Fix config.CREDENTIALS (GUI: Login / Password), or log in by hand now.")
                except BotBlocked as e:
                    print(f"\n!!! {e}\n    Retrying makes it last longer: python main.py login --by-hand {platform}")
                    continue
            if not wait_for_enter(driver, f"Log in to {platform} in the browser, then press Enter..."):
                raise Cancelled()
    finally:
        stop_observer.set()
        try:
            driver.quit()
        except WebDriverException:
            pass  # already closed


def run_login_by_hand(platforms) -> None:
    """Plain browser windows (not automated), one per platform: for sites refusing automation."""
    for platform in platforms:
        window = open_profile_browser(PLATFORMS[platform].login_url)
        print(f"Log in to {platform} in the browser window, then close it...")
        window.wait()


def show_stats() -> None:
    with FollowedStore(AUTO_FOLLOW_DB_PATH) as store:
        stats = store.stats()
    if not stats:
        print("No account handled yet.")
    for platform, counts in sorted(stats.items()):
        print(
            f"{platform:<12} "
            + ", ".join(f"{s}: {n}" for s, n in sorted(counts.items()))
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("login", "follow", "like", "chat", "own-posts"):
        command = commands.add_parser(name)
        command.add_argument(
            "platforms", nargs="*", metavar="platform", help=", ".join(PLATFORMS)
        )
    commands.choices["login"].add_argument(
        "--by-hand",
        action="store_true",
        help="plain browser window, not automated (for sites blocking automation)",
    )
    unfollow = commands.add_parser("unfollow")
    unfollow.add_argument(
        "platforms", nargs="+", metavar="platform", help=", ".join(PLATFORMS)
    )
    unfollow.add_argument(
        "--dry-run", action="store_true", help="only list who would be unfollowed"
    )
    unfollow.add_argument(
        "--yes", action="store_true", help="skip the confirmation prompt"
    )
    commands.add_parser("stats")
    commands.add_parser("demo")
    commands.add_parser("gui")

    args = parser.parse_args()
    allowed = {
        "like": like_platforms(),
        "chat": chat_platforms(),
        "own-posts": own_posts_platforms(),
    }.get(args.command, list(PLATFORMS))
    unknown = set(getattr(args, "platforms", ())) - set(allowed)
    if unknown:
        parser.error(
            f"unsupported platform(s): {', '.join(sorted(unknown))} (choose from {', '.join(allowed)})"
        )
    return args


def main(args: argparse.Namespace) -> None:
    if args.command == "gui":
        # Imported here: PyQt6 is only needed for the GUI
        from python_web_typer.ui.control_panel import run_gui

        raise SystemExit(run_gui())
    elif args.command == "demo":
        run_demo()
    elif args.command == "stats":
        show_stats()
    elif args.command == "login":
        run = run_login_by_hand if args.by_hand else run_login
        run(args.platforms or list(PLATFORMS))
    elif args.command == "like":
        run_like(args.platforms or like_platforms())
    elif args.command == "chat":
        platforms = args.platforms or chat_platforms(configured_only=True)
        if not platforms:
            raise SystemExit("No channel configured in config.AUTO_CHAT.")
        try:
            check_chat_settings(platforms)
        except ValueError as e:
            raise SystemExit(f"Invalid config.AUTO_CHAT: {e}")
        run_chat(platforms)
    elif args.command == "own-posts":
        platforms = args.platforms or own_posts_platforms(configured_only=True)
        if not platforms:
            raise SystemExit("No account set in config.OWN_ACCOUNTS.")
        try:
            for platform in platforms:
                if not own_account(platform):
                    raise ValueError(
                        f"[{platform}] set your account in config.OWN_ACCOUNTS"
                    )
        except ValueError as e:
            raise SystemExit(f"Invalid config: {e}")
        run_own_posts(platforms)
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


if __name__ == "__main__":
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)-7s [%(threadName)s] %(name)s: %(message)s",
    )
    # Selenium/urllib3 are very chatty at DEBUG
    logging.getLogger("selenium").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)
    # "Connection pool is full": the DOM observer thread shares the driver's
    # single connection, an extra one is opened and dropped. Harmless.
    logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)

    try:
        main(parse_args())
    except Cancelled:
        # Browser window closed (or stop requested): not an error
        raise SystemExit("Stopped.")

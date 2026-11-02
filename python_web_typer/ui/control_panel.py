"""
Control panel: one tab per platform with its settings and action buttons, and a
log area for everything the actions report.

Settings edits apply immediately (also to a running action) and are written to
config.USER_SETTINGS_PATH with "Save settings", where the CLI picks them up too.
One action runs at a time, in its own browser, on a worker thread.
"""

import html
import logging
import sys
import threading
from dataclasses import dataclass
from typing import Callable, List, Optional

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .. import config
from ..cancellation import Cancelled, cancellable_sleep, request_cancel, reset_cancel
from ..engagement import (
    PLATFORMS,
    FollowedStore,
    auto_chat,
    auto_follow,
    auto_like,
    auto_own_posts,
    auto_unfollow,
    chat_platforms,
    chat_settings,
    check_chat_settings,
    keep_list,
    like_settings,
    own_posts_settings,
    platform_settings,
    unfollow_settings,
)
from ..humanize import Humanized
from ..user_settings import save_user_settings
from ..webpage_interactions.mutation_observer import start_dom_observer_thread
from ..webpage_interactions.pick_webdriver import get_webdriver

__all__ = ["ControlPanel", "run_gui"]

logger = logging.getLogger(__name__)

_LEVEL_COLORS = {
    logging.DEBUG: "#888888",
    logging.WARNING: "#c77700",
    logging.ERROR: "#d32f2f",
    logging.CRITICAL: "#d32f2f",
}


# ---------------------------
# Logging -> log area (thread-safe through a Qt signal)
# ---------------------------


class _LogEmitter(QObject):
    record = pyqtSignal(int, str)


class QtLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.emitter = _LogEmitter()
        self.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%H:%M:%S")
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.emitter.record.emit(record.levelno, self.format(record))
        except RuntimeError:
            pass  # window already destroyed


# ---------------------------
# Setting editors
# ---------------------------


class HumanizedEdit(QWidget):
    """avg / max / min spin boxes. Emits `changed` only with a valid Humanized."""

    changed = pyqtSignal(object)

    def __init__(self, value: Humanized, integer: bool):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._boxes = []
        for label, number in (("avg", value.mean), ("max", value.max), ("min", value.min)):
            box = QSpinBox() if integer else QDoubleSpinBox()
            box.setRange(0, 1_000_000)
            if not integer:
                box.setDecimals(2)
            box.setValue(number)
            box.valueChanged.connect(self._on_change)
            layout.addWidget(QLabel(label))
            layout.addWidget(box)
            self._boxes.append(box)
        layout.addStretch()

    def _on_change(self) -> None:
        mean, maximum, minimum = (box.value() for box in self._boxes)
        valid = minimum <= mean <= maximum
        for box in self._boxes:
            box.setStyleSheet("" if valid else "background: #ffd6d6;")
        if valid:
            self.changed.emit(Humanized(mean, maximum, minimum))


class LinesEdit(QPlainTextEdit):
    """One entry per line. Emits `changed` with the non-empty lines."""

    changed = pyqtSignal(object)

    def __init__(self, lines: List[str]):
        super().__init__("\n".join(lines))
        self.setFixedHeight(80)
        self.textChanged.connect(
            lambda: self.changed.emit([l.strip() for l in self.toPlainText().splitlines() if l.strip()])
        )


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str  # "int" / "float" (Humanized), "lines", "text", "bool"
    applies: Callable = lambda spec: True


_SEARCH = lambda spec: spec.search_url is not None  # noqa: E731

FOLLOW_FIELDS = (
    Field("max_follows", "Follows per run", "int"),
    Field("max_follows_per_24h", "Follows per 24h", "int"),
    Field("max_followers", "Only accounts under (followers)", "int", _SEARCH),
    Field("search_terms", "Search requests", "lines", _SEARCH),
    Field("search_scrolls", "Result pages per search", "int", lambda s: s.search_url or s.name == "facebook"),
    Field("seed_accounts", "Follow followers of", "lines", lambda s: s.name == "instagram"),
)
UNFOLLOW_FIELDS = (
    Field("keep", "Never unfollow", "lines"),
    Field("max_unfollows", "Unfollows per run", "int"),
    Field("max_unfollows_per_24h", "Unfollows per 24h", "int"),
)
LIKE_FIELDS = (
    Field("max_likes", "Likes per run", "int"),
    Field("max_likes_per_24h", "Likes per 24h", "int"),
    Field("search_terms", "Search requests", "lines"),
    Field("search_scrolls", "Result pages per search", "int"),
)
CHAT_FIELDS = (
    Field("chat_url", "Chat URL (overrides account)", "text"),
    Field("messages", "Messages", "lines"),
    Field("interval", "Seconds between messages", "float"),
    Field("max_messages", "Messages per run", "int"),
)
OWN_POSTS_FIELDS = (
    Field("like", "Like my posts", "bool"),
    Field("comment", "Comment my posts", "bool"),
    Field("messages", "Comments", "lines"),
    Field("max_posts", "Posts per run", "int"),
    Field("scrolls", "Post list pages", "int"),
)


# ---------------------------
# Worker: one action, in its own browser
# ---------------------------


class _CaptchaNotifier:
    """Stands in for the task queue of the DOM observer: forwards to a callback."""

    def __init__(self, callback: Callable[[], None]):
        self._callback = callback

    def add_task(self, *_args, **_kwargs) -> None:
        self._callback()


class ActionWorker(QThread):
    captcha = pyqtSignal(str)

    def __init__(self, title: str, action: Callable):
        super().__init__()
        self.title = title
        self._action = action

    def run(self) -> None:
        reset_cancel()
        driver = None
        stop_observer = threading.Event()
        logger.info("▶ %s", self.title)
        try:
            driver = get_webdriver()
            start_dom_observer_thread(
                driver,
                stop_event=stop_observer,
                watched_classes=config.CAPTCHA_SPECIFIC_CLASSES,
                watched_ids=config.CAPTCHA_SPECIFIC_IDS,
                task_queue=_CaptchaNotifier(lambda: self.captcha.emit(self.title)),
                task_enum="captcha",
            )
            result = self._action(driver)
            logger.info("■ %s finished: %s", self.title, result)
        except Cancelled:
            logger.warning("■ %s stopped", self.title)
        except ValueError as e:  # configuration problems
            logger.error("■ %s: %s", self.title, e)
        except Exception:
            logger.exception("■ %s failed", self.title)
        finally:
            stop_observer.set()
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass


# ---------------------------
# Main window
# ---------------------------


class ControlPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Social Media Clicker")
        self.resize(1000, 850)
        self._worker: Optional[ActionWorker] = None
        self._action_buttons: List[QPushButton] = []
        self._dirty = False

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._build_top())
        splitter.addWidget(self._build_log_area())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        self.setCentralWidget(splitter)
        self._set_running(False)

    # ----- layout -----

    def _build_top(self) -> QWidget:
        top = QWidget()
        layout = QVBoxLayout(top)

        toolbar = QHBoxLayout()
        save = QPushButton("Save settings")
        save.clicked.connect(self._save)
        stats = QPushButton("Show stats")
        stats.clicked.connect(self._show_stats)
        chat_all = QPushButton("Chat on all configured")
        chat_all.clicked.connect(self._chat_all)
        self._action_buttons.append(chat_all)
        self._stop = QPushButton("Stop")
        self._stop.setStyleSheet("font-weight: bold;")
        self._stop.clicked.connect(self._request_stop)
        self._status = QLabel()
        for widget in (save, stats, chat_all, self._stop):
            toolbar.addWidget(widget)
        toolbar.addStretch()
        toolbar.addWidget(self._status)
        layout.addLayout(toolbar)

        tabs = QTabWidget()
        for name, spec in PLATFORMS.items():
            tabs.addTab(self._build_platform_tab(spec), name.capitalize())
        layout.addWidget(tabs)
        return top

    def _build_log_area(self) -> QWidget:
        area = QWidget()
        layout = QVBoxLayout(area)
        header = QHBoxLayout()
        header.addWidget(QLabel("Logs"))
        header.addStretch()
        level = QComboBox()
        level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        level.setCurrentText("INFO")
        header.addWidget(QLabel("Level"))
        header.addWidget(level)
        clear = QPushButton("Clear")
        header.addWidget(clear)
        layout.addLayout(header)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(5000)
        self._log.setFont(QFont("monospace"))
        layout.addWidget(self._log)
        clear.clicked.connect(self._log.clear)

        self._log_handler = QtLogHandler()
        self._log_handler.setLevel(logging.INFO)
        self._log_handler.emitter.record.connect(self._append_log)
        level.currentTextChanged.connect(lambda name: self._log_handler.setLevel(name))
        logging.getLogger().addHandler(self._log_handler)
        return area

    def _build_platform_tab(self, spec) -> QWidget:
        name = spec.name
        content = QWidget()
        layout = QVBoxLayout(content)

        account = QGroupBox("Account")
        form = QFormLayout(account)
        account_edit = QLineEdit(config.OWN_ACCOUNTS.get(name, ""))
        account_edit.setPlaceholderText("@name, name or profile URL")
        account_edit.textChanged.connect(lambda text: self._set_own_account(name, text))
        form.addRow("My account", account_edit)
        form.addRow(self._buttons(("Log in", lambda: self._login(spec))))
        layout.addWidget(account)

        layout.addWidget(self._section(
            "Follow", "AUTO_FOLLOW", name, platform_settings(name),
            [f for f in FOLLOW_FIELDS if f.applies(spec)],
            ("Follow", lambda: self._start(f"Follow on {name}", lambda d: auto_follow(d, name))),
        ))
        if spec.unfollow:
            dry_run = QCheckBox("Dry run (only list who would be unfollowed)")
            dry_run.setChecked(True)
            layout.addWidget(self._section(
                "Unfollow", "AUTO_UNFOLLOW", name, unfollow_settings(name), UNFOLLOW_FIELDS,
                ("Unfollow", lambda: self._unfollow(name, dry_run.isChecked())),
                extra=dry_run,
            ))
        if spec.like:
            layout.addWidget(self._section(
                "Like posts", "AUTO_LIKE", name, like_settings(name), LIKE_FIELDS,
                ("Like", lambda: self._start(f"Like on {name}", lambda d: auto_like(d, name))),
            ))
        if spec.chat:
            layout.addWidget(self._section(
                "My live chat", "AUTO_CHAT", name, chat_settings(name), CHAT_FIELDS,
                ("Start chat", lambda: self._chat([name])),
            ))
        if spec.own_posts:
            layout.addWidget(self._section(
                "My posts", "AUTO_OWN_POSTS", name, own_posts_settings(name), OWN_POSTS_FIELDS,
                ("Like / comment my posts", lambda: self._start(
                    f"My posts on {name}", lambda d: auto_own_posts(d, name))),
            ))
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        return scroll

    def _section(
        self, title, config_name, platform, current, fields, *buttons, extra: Optional[QWidget] = None
    ) -> QGroupBox:
        group = QGroupBox(title)
        form = QFormLayout(group)
        for field in fields:
            form.addRow(field.label, self._editor(config_name, platform, field, current[field.key]))
        if extra is not None:
            form.addRow(extra)
        form.addRow(self._buttons(*buttons))
        return group

    def _editor(self, config_name: str, platform: str, field: Field, value) -> QWidget:
        def store(new_value):
            getattr(config, config_name).setdefault(platform, {})[field.key] = new_value
            self._dirty = True

        if field.kind in ("int", "float"):
            if not isinstance(value, Humanized):
                value = Humanized(value, value, 0)
            editor = HumanizedEdit(value, integer=field.kind == "int")
            editor.changed.connect(store)
        elif field.kind == "lines":
            editor = LinesEdit(list(value or ()))
            editor.changed.connect(store)
        elif field.kind == "bool":
            editor = QCheckBox()
            editor.setChecked(bool(value))
            editor.toggled.connect(store)
        else:
            editor = QLineEdit(value or "")
            editor.textChanged.connect(lambda text: store(text.strip()))
        return editor

    def _buttons(self, *buttons) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        for label, callback in buttons:
            button = QPushButton(label)
            button.clicked.connect(callback)
            layout.addWidget(button)
            self._action_buttons.append(button)
        layout.addStretch()
        return row

    # ----- settings -----

    def _set_own_account(self, platform: str, text: str) -> None:
        config.OWN_ACCOUNTS[platform] = text.strip()
        self._dirty = True

    def _save(self) -> bool:
        try:
            save_user_settings(config.USER_SETTINGS_PATH, vars(config))
        except OSError as e:
            QMessageBox.critical(self, "Save failed", str(e))
            return False
        self._dirty = False
        logger.info("Settings saved to %s", config.USER_SETTINGS_PATH)
        return True

    def _show_stats(self) -> None:
        with FollowedStore(config.AUTO_FOLLOW_DB_PATH) as store:
            stats = store.stats()
        if not stats:
            logger.info("Stats: nothing handled yet")
        for key, counts in sorted(stats.items()):
            logger.info("Stats %-22s %s", key, ", ".join(f"{s}: {n}" for s, n in sorted(counts.items())))

    # ----- actions -----

    def _start(self, title: str, action: Callable) -> None:
        if self._worker is not None:
            return
        self._worker = ActionWorker(title, action)
        self._worker.captcha.connect(self._on_captcha)
        self._worker.finished.connect(self._on_finished)
        self._set_running(True, title)
        self._worker.start()

    def _login(self, spec) -> None:
        def action(driver):
            driver.get(spec.login_url)
            logger.info("Log in to %s in the browser, then press Stop to close it", spec.name)
            cancellable_sleep(24 * 3600)

        self._start(f"Log in to {spec.name}", action)

    def _unfollow(self, platform: str, dry_run: bool) -> None:
        try:
            keep = keep_list(platform)
        except ValueError as e:
            QMessageBox.critical(self, "Invalid keep list", str(e))
            return
        if not dry_run:
            text = f"Unfollow every account on {platform} except {len(keep)} kept account(s)?"
            if not keep:
                text += "\n\nThe keep list is EMPTY: every account will be unfollowed."
            if platform == "facebook":
                text += "\n\nOn Facebook this REMOVES FRIENDS."
            answer = QMessageBox.warning(
                self, "Confirm unfollow", text,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        title = f"Unfollow on {platform}" + (" (dry run)" if dry_run else "")
        self._start(title, lambda d: auto_unfollow(d, platform, dry_run))

    def _chat(self, platforms: List[str]) -> None:
        try:
            check_chat_settings(platforms)
        except ValueError as e:
            QMessageBox.critical(self, "Chat not configured", str(e))
            return
        self._start(f"Chat on {', '.join(platforms)}", lambda d: auto_chat(d, platforms))

    def _chat_all(self) -> None:
        platforms = chat_platforms(configured_only=True)
        if not platforms:
            QMessageBox.information(self, "Chat", "Set your account (or a chat URL) on a chat platform first.")
            return
        self._chat(platforms)

    def _request_stop(self) -> None:
        if self._worker is not None:
            logger.info("Stopping… (at the next pause)")
            request_cancel()

    def _on_finished(self) -> None:
        self._worker = None
        self._set_running(False)

    def _on_captcha(self, title: str) -> None:
        logger.warning("CAPTCHA detected during %s: solve it in the browser", title)
        box = QMessageBox(QMessageBox.Icon.Warning, "CAPTCHA", f"CAPTCHA detected during {title}.\nSolve it in the browser.", parent=self)
        box.setModal(False)
        box.show()

    def _set_running(self, running: bool, title: str = "") -> None:
        for button in self._action_buttons:
            button.setEnabled(not running)
        self._stop.setEnabled(running)
        self._status.setText(f"Running: {title}" if running else "Idle")

    def _append_log(self, level: int, text: str) -> None:
        color = _LEVEL_COLORS.get(level)
        escaped = html.escape(text)
        self._log.appendHtml(f'<span style="color:{color}">{escaped}</span>' if color else escaped)

    # ----- closing -----

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._dirty:
            answer = QMessageBox.question(
                self, "Unsaved settings", "Save the settings before quitting?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            )
            if answer == QMessageBox.StandardButton.Cancel or (
                answer == QMessageBox.StandardButton.Save and not self._save()
            ):
                event.ignore()
                return
        if self._worker is not None:
            request_cancel()
            self._worker.wait(30_000)
        logging.getLogger().removeHandler(self._log_handler)
        event.accept()


def run_gui() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = ControlPanel()
    window.show()
    return app.exec()

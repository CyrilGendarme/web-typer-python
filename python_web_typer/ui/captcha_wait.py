import logging
import sys

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

__all__ = ["CaptchaWaitWindow", "wait_for_captcha"]

logger = logging.getLogger(__name__)


class CaptchaWaitWindow(QWidget):
    captcha_result_signal = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Captcha spotted")
        self.setGeometry(100, 100, 300, 150)
        layout = QVBoxLayout()

        self.label = QLabel("Is the CAPTCHA solved?", self)
        layout.addWidget(self.label)

        self.button_yes = QPushButton("Yes", self)
        self.button_yes.clicked.connect(self.on_yes_clicked)
        layout.addWidget(self.button_yes)

        self.button_no = QPushButton("No", self)
        self.button_no.clicked.connect(self.on_no_clicked)
        layout.addWidget(self.button_no)

        self.setLayout(layout)

    def on_yes_clicked(self):
        self.captcha_result_signal.emit(True)
        self.close()

    def on_no_clicked(self):
        self.captcha_result_signal.emit(False)
        self.close()


def wait_for_captcha() -> bool:
    """
    Open the CAPTCHA popup window and block until the user answers.

    Returns:
        bool: True if the user confirmed the CAPTCHA is solved, False otherwise
        (including when the window is closed without answering).
    """

    # Reuse the existing QApplication: creating a second one crashes Qt
    app = QApplication.instance() or QApplication(sys.argv)

    result = False

    def on_result(solved: bool) -> None:
        nonlocal result
        result = solved

    window = CaptchaWaitWindow()
    window.captcha_result_signal.connect(on_result)
    window.show()

    # Blocks until the window is closed
    app.exec()

    logger.info("Captcha result: %s", result)
    return result

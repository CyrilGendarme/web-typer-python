import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal, QObject


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


def wait_for_captcha():
    """Open the CAPTCHA popup window and block execution until user response."""

    # Initialize QApplication only once (inside wait_for_captcha function)
    app = QApplication(sys.argv)

    # Create the CAPTCHA window (this is where user interacts)
    window = CaptchaWaitWindow()

    # Connect the signal to a function (this function will execute when user clicks a button)
    window.captcha_result_signal.connect(
        lambda result: print(f"Captcha result: {result}")
    )

    # Show the window to the user
    window.show()

    # Start the event loop and block further code execution until the window is closed
    app.exec()

    return window

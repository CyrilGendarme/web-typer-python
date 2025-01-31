import sys
import threading
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel
from PyQt6.QtCore import QEventLoop, QTimer, pyqtSignal


class CaptchaWaitWindow(QWidget):
    # Custom signal to return the result
    captcha_result_signal = pyqtSignal(bool)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Captcha spotted")
        self.setGeometry(100, 100, 300, 150)

        # Create layout and add widgets (buttons, labels)
        layout = QVBoxLayout()

        self.label = QLabel("Is it ok now?", self)
        layout.addWidget(self.label)

        self.button_yes = QPushButton("Yes", self)
        self.button_yes.clicked.connect(self.on_yes_clicked)
        layout.addWidget(self.button_yes)

        self.button_no = QPushButton("No", self)
        self.button_no.clicked.connect(self.on_no_clicked)
        layout.addWidget(self.button_no)

        # Set the layout to the window
        self.setLayout(layout)

        self._result = None
        self._loop = QEventLoop()

    def on_yes_clicked(self):
        self._result = True
        self.captcha_result_signal.emit(self._result)
        self._loop.quit()

    def on_no_clicked(self):
        self._result = False
        self.captcha_result_signal.emit(self._result)
        self._loop.quit()

    def get_result(self):
        return self._result

    def exec_(self):
        self.show()
        self._loop.exec()


# Function to call captcha wait window in a thread
def wait_for_captcha():
    # Create the application in the main thread
    app = QApplication(sys.argv)

    window = CaptchaWaitWindow()

    # Connect the signal to get the result
    window.captcha_result_signal.connect(lambda value: print(f"Result: {value}"))

    window.exec_()  # Run the window's event loop

    return window.get_result()


def main():
    # Run the captcha wait window in a separate thread to make it non-blocking
    def run_captcha_in_thread():
        captcha_result = wait_for_captcha()
        print(f"Captcha result: {captcha_result}")

    captcha_thread = threading.Thread(target=run_captcha_in_thread)
    captcha_thread.start()

    # Simulate other work in the main thread
    print("Simulating work...")

    captcha_thread.join()  # Wait for the captcha thread to finish

    print("Work done!")


if __name__ == "__main__":
    main()

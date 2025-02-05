import os
import subprocess
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from config import DEBUG


def get_headless_webdriver():
    """Launch a headless Chrome WebDriver with custom options."""
    options = Options()
    if not DEBUG:
        options.add_argument("--headless")  # Run browser in headless mode
        options.add_argument("--disable-gpu")  # Disable GPU (optional)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )  # Mimic a real browser

    driver = webdriver.Chrome(options=options)
    return driver


def attach_to_open_chrome(debugger_address="127.0.0.1:9222"):
    """Attach Selenium WebDriver to an already open Chrome window."""
    options = Options()
    options.debugger_address = debugger_address  # Connect to the running browser

    try:
        driver = webdriver.Chrome(options=options)
        print("Successfully attached to the existing Chrome window.")
        return driver
    except Exception as e:
        print(f"Error attaching to Chrome: {e}")
        return None


def launch_chrome_with_debugging(
    chrome_path="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    user_data_dir="C:\\selenium\\ChromeProfile",
    debug_port=9222,
):
    """Launches Chrome with remote debugging enabled."""

    # Ensure the profile directory exists
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)

    # Command to launch Chrome
    command = f'"{chrome_path}" --remote-debugging-port={debug_port} --user-data-dir="{user_data_dir}"'

    try:
        # Launch Chrome in a non-blocking way
        subprocess.Popen(command, shell=True)
        print(f"Launched Chrome with remote debugging on port {debug_port}")

        # Wait for Chrome to start
        time.sleep(3)
    except Exception as e:
        print(f"Failed to launch Chrome: {e}")

import sys
import platform

current_platform = platform.system()
if current_platform == "Windows":
    import pygetwindow as gw
elif current_platform == "Linux":
    import subprocess
else:
    print("Unsupported OS:", current_platform)
    sys.exit(1)


def is_file_selector_open(TARGET_WINDOW_TITLES):
    if current_platform == "Windows":

        windows = gw.getWindowsWithTitle("")
        for window in windows:
            for target in TARGET_WINDOW_TITLES:
                if target.lower() in window.title.lower():
                    return window
        return None

    elif current_platform == "Linux":

        try:
            output = subprocess.check_output(["wmctrl", "-l"]).decode()
            for line in output.splitlines():
                for target in TARGET_WINDOW_TITLES:
                    if target.lower() in line.lower():
                        return line
        except Exception as e:
            print(f"[ERROR] Linux window detection failed: {e}")
        return None


def bring_window_to_front(window):
    if current_platform == "Windows":
        if window:
            window.activate()
            window.maximize()  # Optional, ensure visibility
            # time.sleep(0.5)

    elif current_platform == "Linux":
        try:
            window_id = window.split()[0]
            subprocess.call(["wmctrl", "-i", "-a", window_id])
            # time.sleep(0.5)
        except Exception as e:
            print(f"[ERROR] Failed to bring window to front on Linux: {e}")

import time
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup, Tag
from datetime import datetime, date
from decimal import Decimal
from dataclasses import  dataclass
import re

from ..webpage_interactions.simulate_typing import simulate_typing
from ..webpage_interactions.pick_webpage_element import (
    ElementSelectorMethod,
    pick_element_by_class,
    pick_element_by_css_selector,
    pick_element_by_id,
    pick_element_by_name,
    pick_element,
)
from ..webpage_interactions.simulate_click import simulate_click
import csv


#
#
# Here are the core functions
#
def click_element(
    driver: WebDriver, method: ElementSelectorMethod, identifier: str, nth: int = 0
):
    """
    Clicks on a webpage element based on the specified selection method.

    Args:
        driver (WebDriver): Selenium WebDriver instance.
        method (ElementSelectorMethod): The method used to locate the element (Enum value).
        identifier (str): The actual value for the selected method (ID, class, CSS selector, etc.).
        nth (int, optional): Index of the element if multiple exist (default is 0).

    Returns:
        None: Clicks the element if found, otherwise prints an error message.
    """
    element = pick_element(driver, method, identifier, nth)
    if element:
        simulate_click(driver, element)
    else:
        print(f"Could not find element {identifier} using {method.name}")


# core
def type_into_element(
    driver: WebDriver,
    method: ElementSelectorMethod,
    identifier: str,
    text: str,
    nth: int = 0,
):
    """
    Finds a webpage element and types the given text into it.

    Args:
        driver (WebDriver): Selenium WebDriver instance.
        method (ElementSelectorMethod): The method used to locate the element (Enum value).
        identifier (str): The actual value for the selected method (ID, class, CSS selector, etc.).
        text (str): The text to be typed into the selected element.
        nth (int, optional): Index of the element if multiple exist (default is 0).

    Returns:
        None: Types the given text if the element is found, otherwise prints an error message.
    """
    element = pick_element(driver, method, identifier, nth)
    if element:
        simulate_typing(driver, element, text)
    else:
        print(f"Could not find element {identifier} using {method.name}")


# core
def drag_and_drop_file(
    driver: WebDriver,
    method_file_input: ElementSelectorMethod,
    method_drop_zone: ElementSelectorMethod,
    file_input_selector: str,
    drop_zone_selector: str,
    file_path: str,
    nth_file_input: int = 0,
    nth_drop_zone: int = 0,
):
    """
    Simulates dragging and dropping a file into a drop zone.

    Args:
        driver (WebDriver): Selenium WebDriver instance.
        method_file_input (ElementSelectorMethod): Method to locate the file input.
        method_drop_zone (ElementSelectorMethod): Method to locate the drop zone.
        file_input_selector (str): Selector for the hidden file input.
        drop_zone_selector (str): Selector for the drop zone.
        file_path (str): Absolute path of the file to be uploaded.
        nth_file_input (int, optional): Index of file input if multiple exist (default: 0).
        nth_drop_zone (int, optional): Index of drop zone if multiple exist (default: 0).
    """

    # Locate elements
    file_input = pick_element(
        driver, method_file_input, file_input_selector, nth_file_input
    )
    drop_zone = pick_element(
        driver, method_drop_zone, drop_zone_selector, nth_drop_zone
    )

    if not file_input:
        print(
            f"Error: File input element not found using {method_file_input} - {file_input_selector}"
        )
        return

    if not drop_zone:
        print(
            f"Warning: Drop zone element not found using {method_drop_zone} - {drop_zone_selector}"
        )
        print("Proceeding with direct file input upload.")

    # Send file to hidden input
    file_input.send_keys(file_path)

    # If drop zone exists, attempt a visual drag-and-drop
    if drop_zone:
        try:
            action = ActionChains(driver)
            action.click_and_hold(file_input).move_to_element(
                drop_zone
            ).release().perform()
            print("Drag-and-drop simulation executed.")
        except Exception as e:
            print(f"Drag-and-drop action failed: {e}")

    print("File upload process completed.")


# core
def sleep(delay):
    time.sleep(delay)


#
#
# Example in local main, kept to make it work but we prefer generic stuff
#
@dataclass
class InterestRate:
    bank: str
    tenor: str
    effective_date: date
    value_percent: Decimal

def read_table(table: Tag) -> list[list[str]]:
    table_rows = []
    for table_row in table.select("tr"):
        cells = table_row.find_all("td")

        if len(cells) > 0:
            cell_values = []

            for cell in cells:
                cell_values.append(cell.text.strip())

            table_rows.append(cell_values)
    return table_rows


def extract_number(text) -> Decimal | None:
    """
    Extract the first string number of the form:
    -4
    15.177
    1,915.0
    """
    pattern = r"[-+]?(?:\d+(?:,\d\d\d)*(?:\.\d*)?|\.\d+)"
    number_match = re.search(pattern, text)
    if number_match:
        num_str = number_match.group(0)
        clean_num_str = num_str.replace(",", "")
        return Decimal(clean_num_str)
    else:
        return None


def getInterestRateTableData(driver, CSV_FILE):
    page_html = BeautifulSoup(driver.page_source, features="lxml")
    tables = page_html.find_all("table", attrs={"class": "jrPage"})
    if len(tables) < 2:
        raise Exception("Expected at least 2 tables on the page, found only", len(tables))

    table = tables[1]  # Index 1 = Second table

    table_rows = read_table(table)

    # print("\n\n")
    # print("---------- DEBUG 1 ----------")
    # for row in table_rows:
    #     print(row)

    header_idx = -1
    note_idx = -1
    date_idx = -1

    for idx, line in enumerate(table_rows):
        firstCell = line[0]
        if header_idx < 0 and firstCell.startswith("TERM"):
            header_idx = idx
        elif date_idx < 0 and firstCell.startswith("Effective date"):
            date_idx = idx
        elif note_idx < 1 and firstCell.startswith("Note"):
            note_idx = idx

    effective_date_str = table_rows[date_idx][0]
    effective_date_str = (
        effective_date_str.removeprefix("Effective date").removeprefix(":").strip()
    )
    effective_date = datetime.strptime(effective_date_str, "%m/%d/%Y")

    if type(effective_date) is not datetime:
        # log.critical("Unable to parse date", effective_date_str)
        raise Exception("Unable to parse date", effective_date_str)

    interest_rate_rows: list[InterestRate] = []
    for line in table_rows[header_idx + 1 : note_idx]:
        term = line[0]
        value_str: str = line[1]
        number_value = extract_number(value_str)
        if number_value:
            interest_rate_rows.append(
                InterestRate(
                    "State Bank of Vietnam", term, effective_date, number_value
                )
            )
        # else:
            # log.warn(f"Ignore line, value {value_str} is not a number", line)

    # print("\n\n")
    # print("---------- DEBUG 2 ----------")
    # print(interest_rate_rows)
    # print("\n\n")

    # Save the result to a CSV file
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["bank", "tenor", "effective_date", "value_percent"])
        for row in interest_rate_rows:
            writer.writerow([row.bank, row.tenor, row.effective_date, row.value_percent])

    print(f"Interest rates saved to {CSV_FILE}")

    return interest_rate_rows
    
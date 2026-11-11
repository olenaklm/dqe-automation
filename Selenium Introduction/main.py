import argparse
import csv
import logging
import sys
import time
from pathlib import Path
from typing import List, Tuple

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


WAIT_TIMEOUT = 15

# CSV headers for the doughnut chart data.
DOUGHNUT_HEADERS = ["Facility Type", "Min Average Time Spent"]


class ChromeDriverContext:
    """
    A class-based context manager for creating and closing Chrome WebDriver.
    """

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver = None

    def __enter__(self):
        options = Options()

        # Window size is important for correctly sized chart screenshots.
        options.add_argument("--window-size=1600,1200")
        options.add_argument("--disable-notifications")
        options.add_argument("--allow-file-access-from-files")
        options.add_argument("--disable-popup-blocking")

        if self.headless:
            options.add_argument("--headless=new")

        # Selenium Manager automatically finds a compatible ChromeDriver.
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(1)

        return self.driver

    def __exit__(self, exc_type, exc_value, traceback):
        if self.driver is not None:
            try:
                self.driver.quit()
            except WebDriverException as error:
                logging.warning("Could not close ChromeDriver correctly: %s", error)


def get_text(element) -> str:
    """
    Gets element text including SVG elements,
    where Selenium's .text may return an empty string.
    """
    return (element.get_attribute("textContent") or "").strip()


def write_csv(path: Path, headers: List[str], rows: List[List[str]]) -> None:
    """
    Saves data to CSV using UTF-8 with BOM encoding.
    This encoding is convenient for opening CSV files in Excel on Windows.
    """
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)

    logging.info("Created file: %s", path)


def wait_for_table(driver):
    """
    Waits until the table becomes visible.
    """
    return WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.visibility_of_element_located((By.CLASS_NAME, "table"))
    )


def extract_table(driver) -> Tuple[List[str], List[List[str]]]:
    """
    Extracts headers and rows from the report table.

    Locators used:
    - By.CLASS_NAME for the table root;
    - By.CSS_SELECTOR for table columns;
    - By.ID for column headers;
    - By.XPATH for table cells.
    """
    table = wait_for_table(driver)

    # CSS Selector is used to find all columns inside the table.
    columns = table.find_elements(By.CSS_SELECTOR, ".y-column")

    if not columns:
        raise NoSuchElementException(
            "No columns with class 'y-column' were found in the table."
        )

    headers = []
    columns_data = []

    for column_index, column in enumerate(columns, start=1):
        try:
            # ID locator is used to find the column header.
            header_element = column.find_element(By.ID, "header")
            header = get_text(header_element)

            if not header:
                header = f"Column {column_index}"

            headers.append(header)

            # XPath locator is used to find text cells inside a column.
            cells = column.find_elements(
                By.XPATH,
                ".//*[contains(concat(' ', normalize-space(@class), ' '), ' cell-text ')]",
            )

            values = [get_text(cell) for cell in cells]

            # In some reports, the header may also be returned as a cell-text element.
            # Remove only the first matching header value to avoid deleting real data.
            if header in values:
                values.remove(header)

            columns_data.append(values)

        except NoSuchElementException as error:
            logging.warning(
                "Could not process table column %s: %s",
                column_index,
                error,
            )
            headers.append(f"Column {column_index}")
            columns_data.append([])

    max_row_count = max((len(column) for column in columns_data), default=0)

    rows = []
    for row_index in range(max_row_count):
        row = []

        for column in columns_data:
            value = column[row_index] if row_index < len(column) else ""
            row.append(value)

        rows.append(row)

    return headers, rows


def save_table_to_csv(driver, output_dir: Path) -> None:
    """
    Extracts table data and saves it as table.csv.
    """
    try:
        headers, rows = extract_table(driver)
        write_csv(output_dir / "table.csv", headers, rows)

        logging.info(
            "Table was saved. Columns: %s, rows: %s",
            len(headers),
            len(rows),
        )

    except (TimeoutException, NoSuchElementException, WebDriverException) as error:
        logging.exception("Error while processing the table: %s", error)
        raise


def wait_for_doughnut(driver):
    """
    Waits until the Plotly pie layer becomes available.
    """
    return WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located((By.CLASS_NAME, "pielayer"))
    )


def get_doughnut_rows(driver) -> List[List[str]]:
    """
    Extracts visible labels from the doughnut chart.

    Only real slice labels are used:
    text.slicetext[data-notex='1']

    tspan[0] is the category.
    tspan[1] is the value.
    """
    doughnut = wait_for_doughnut(driver)

    labels = doughnut.find_elements(
        By.CSS_SELECTOR,
        "text.slicetext[data-notex='1']",
    )

    rows = []

    for label in labels:
        try:
            # Ignore hidden labels after legend filters are toggled.
            if not label.is_displayed():
                continue

            tspans = label.find_elements(By.TAG_NAME, "tspan")

            if len(tspans) < 2:
                continue

            category = get_text(tspans[0])
            value = get_text(tspans[1])

            if category:
                rows.append([category, value])

        except StaleElementReferenceException:
            logging.warning(
                "The SVG label changed while reading it. The row was skipped."
            )

    return rows


def save_doughnut_screenshot(driver, output_path: Path) -> None:
    """
    Saves a screenshot of the chart.

    First, the script tries to capture the parent SVG element.
    If it fails, it captures the pie layer.
    As a final fallback, it captures the entire browser window.
    """
    try:
        doughnut = wait_for_doughnut(driver)

        try:
            chart_svg = doughnut.find_element(
                By.XPATH,
                "./ancestor::*[local-name()='svg'][1]",
            )
            chart_svg.screenshot(str(output_path))

        except (NoSuchElementException, WebDriverException):
            doughnut.screenshot(str(output_path))

    except WebDriverException as error:
        logging.warning(
            "Could not capture only the chart. Saving the entire browser window: %s",
            error,
        )
        driver.save_screenshot(str(output_path))

    logging.info("Created screenshot: %s", output_path)


def save_doughnut_stage(driver, output_dir: Path, stage_number: int) -> None:
    """
    Saves files for the current chart state:
    screenshotN.png and doughnutN.csv.
    """
    screenshot_path = output_dir / f"screenshot{stage_number}.png"
    csv_path = output_dir / f"doughnut{stage_number}.csv"

    try:
        save_doughnut_screenshot(driver, screenshot_path)
        rows = get_doughnut_rows(driver)

    except (TimeoutException, NoSuchElementException, WebDriverException) as error:
        logging.exception(
            "Could not fully extract chart data for stage %s: %s",
            stage_number,
            error,
        )
        rows = []

    # When all legend items are disabled, rows may be empty.
    # The CSV file is still created with the required headers.
    write_csv(csv_path, DOUGHNUT_HEADERS, rows)


def get_legend_items(driver):
    """
    Finds the chart legend and all filter items.
    """
    legend = WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located((By.CLASS_NAME, "scrollbox"))
    )

    items = legend.find_elements(By.CLASS_NAME, "traces")

    if not items:
        raise NoSuchElementException(
            "No legend elements with class 'traces' were found."
        )

    return items


def wait_for_chart_update(driver) -> None:
    """
    Waits for the Plotly chart to refresh after clicking a legend item.
    """
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located((By.CLASS_NAME, "pielayer"))
    )

    # Plotly normally uses a short animation after toggling a legend item.
    time.sleep(0.8)


def click_legend_item(driver, index: int) -> None:
    """
    Clicks one legend item.

    Legend items are searched again before every click because Plotly
    can redraw the DOM and make previous element references stale.
    """
    items = get_legend_items(driver)

    if index >= len(items):
        raise IndexError(
            f"Legend item with index {index} was not found. "
            f"Available items: {len(items)}."
        )

    item = items[index]

    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
            item,
        )

        item.click()

    except (ElementClickInterceptedException, WebDriverException):
        # Alternative click method for Plotly and SVG elements.
        ActionChains(driver).move_to_element(item).click().perform()

    wait_for_chart_update(driver)


def process_doughnut_chart(driver, output_dir: Path) -> None:
    """
    Processes the doughnut chart.

    Stage 0 is the initial state with all filters enabled.
    Stages 1..N are states after sequentially clicking every legend item.

    The final CSV file can contain only headers if all filters are disabled.
    """
    wait_for_doughnut(driver)

    # Save the initial chart state before applying any filters.
    save_doughnut_stage(driver, output_dir, 0)

    try:
        legend_items = get_legend_items(driver)
        filters_count = len(legend_items)

        logging.info("Found filter options: %s", filters_count)

    except (TimeoutException, NoSuchElementException) as error:
        logging.warning(
            "Legend filters were not found. Only doughnut0.csv was created: %s",
            error,
        )
        return

    # Click every legend item sequentially.
    # Each following state accumulates disabled filters:
    # all enabled -> one disabled -> two disabled -> ... -> all disabled.
    for index in range(filters_count):
        stage_number = index + 1

        try:
            click_legend_item(driver, index)
            logging.info(
                "Applied filter %s out of %s.",
                stage_number,
                filters_count,
            )

        except (
            TimeoutException,
            NoSuchElementException,
            StaleElementReferenceException,
            ElementClickInterceptedException,
            WebDriverException,
            IndexError,
        ) as error:
            logging.exception(
                "Could not apply filter %s: %s",
                stage_number,
                error,
            )

        # Save the current chart state even if the filter click failed.
        save_doughnut_stage(driver, output_dir, stage_number)


def parse_arguments():
    """
    Parses command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Selenium automation for report.html"
    )

    parser.add_argument(
        "--report",
        default="report.html",
        help="Path to the local report.html file. Default: report.html",
    )

    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Directory for CSV files and screenshots. "
            "By default, files are saved next to report.html."
        ),
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chrome without opening a browser window.",
    )

    return parser.parse_args()


def main():
    """
    Main program entry point.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    args = parse_arguments()

    report_path = Path(args.report).expanduser().resolve()

    if not report_path.exists():
        logging.error("report.html file was not found: %s", report_path)
        sys.exit(1)

    if args.output:
        output_dir = Path(args.output).expanduser().resolve()
    else:
        output_dir = report_path.parent

    output_dir.mkdir(parents=True, exist_ok=True)

    logging.info("HTML report: %s", report_path)
    logging.info("Output directory: %s", output_dir)

    # as_uri() converts a Windows path into a valid file:/// URL.
    report_url = report_path.as_uri()

    try:
        with ChromeDriverContext(headless=args.headless) as driver:
            driver.get(report_url)

            save_table_to_csv(driver, output_dir)
            process_doughnut_chart(driver, output_dir)

    except WebDriverException as error:
        logging.exception("Selenium / ChromeDriver error: %s", error)
        sys.exit(1)

    logging.info("Automation completed successfully.")


if __name__ == "__main__":
    main()
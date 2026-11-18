import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple

import pandas as pd
import pyarrow.dataset as ds
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By


COLUMN_ALIASES = {
    "facilitytype": "facility_type",
    "facility_type": "facility_type",
    "visitdate": "visit_date",
    "visit_date": "visit_date",
    "averagetimespent": "average_time_spent",
    "average_time_spent": "average_time_spent",
    "avgtimespent": "average_time_spent",
    "avg_time_spent": "average_time_spent",
}


def get_file_uri(file_path: str) -> str:
    """
    Converts a local file path to a valid file:/// URI.
    """
    return Path(file_path).expanduser().resolve().as_uri()


def get_element_text(element: Any) -> str:
    """
    Returns text from a Selenium element.
    textContent is used because Selenium .text may be empty for some elements.
    """
    return (element.get_attribute("textContent") or "").strip()


def normalize_column_name(column_name: str) -> str:
    """
    Converts HTML and Parquet column names to a shared format.
    """
    normalized = str(column_name).strip().lower()
    normalized = normalized.replace("avg", "average")
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")

    compact_name = normalized.replace("_", "")

    if compact_name in COLUMN_ALIASES:
        return COLUMN_ALIASES[compact_name]

    if normalized in COLUMN_ALIASES:
        return COLUMN_ALIASES[normalized]

    return normalized


def read_custom_report_table(table_element: Any) -> pd.DataFrame:
    """
    Reads the custom report table structure.

    Expected elements:
    - table root: class="table"
    - columns: class="y-column"
    - headers: id="header"
    - cells: class="cell-text"
    """
    columns = table_element.find_elements(By.CSS_SELECTOR, ".y-column")

    if not columns:
        raise NoSuchElementException(
            "No elements with class 'y-column' were found inside the table."
        )

    headers = []
    columns_data = []

    for index, column in enumerate(columns, start=1):
        try:
            header_element = column.find_element(By.ID, "header")
            header = get_element_text(header_element)
        except NoSuchElementException:
            header = f"column_{index}"

        cells = column.find_elements(By.CSS_SELECTOR, ".cell-text")
        values = [get_element_text(cell) for cell in cells]

        # Some report layouts may include the header among cell-text values.
        if header in values:
            values.remove(header)

        headers.append(header)
        columns_data.append(values)

    row_count = max((len(column) for column in columns_data), default=0)
    rows = []

    for row_index in range(row_count):
        row = []

        for column in columns_data:
            value = column[row_index] if row_index < len(column) else ""
            row.append(value)

        rows.append(row)

    return pd.DataFrame(rows, columns=headers)


def read_standard_html_table(table_element: Any) -> pd.DataFrame:
    """
    Reads a standard HTML table with tr, th, and td elements.
    """
    header_elements = table_element.find_elements(By.CSS_SELECTOR, "thead th")

    if not header_elements:
        header_elements = table_element.find_elements(
            By.CSS_SELECTOR,
            "tr:first-child th, tr:first-child td",
        )

    headers = [get_element_text(element) for element in header_elements]

    body_rows = table_element.find_elements(By.CSS_SELECTOR, "tbody tr")

    if not body_rows:
        all_rows = table_element.find_elements(By.CSS_SELECTOR, "tr")
        body_rows = all_rows[1:] if len(all_rows) > 1 else []

    rows = []

    for row_element in body_rows:
        cells = row_element.find_elements(By.CSS_SELECTOR, "td")
        row = [get_element_text(cell) for cell in cells]

        if row:
            rows.append(row)

    return pd.DataFrame(rows, columns=headers)


def read_html_table_data(table_element: Any) -> pd.DataFrame:
    """
    Reads a located HTML table into a Pandas DataFrame.

    Supports both:
    - custom report table structure;
    - standard HTML table structure.
    """
    custom_columns = table_element.find_elements(By.CSS_SELECTOR, ".y-column")

    if custom_columns:
        dataframe = read_custom_report_table(table_element)
    else:
        dataframe = read_standard_html_table(table_element)

    if dataframe.empty:
        raise AssertionError("The HTML report table is empty.")

    return dataframe


def find_date_column(dataframe: pd.DataFrame) -> Optional[str]:
    """
    Finds a date column in the Parquet DataFrame.
    """
    possible_names = {
        "visit_date",
        "visitdate",
        "date",
        "report_date",
        "reportdate",
    }

    for column in dataframe.columns:
        normalized = normalize_column_name(column)

        if normalized in possible_names:
            return column

    return None


def read_partitioned_parquet_dataset(
    parquet_folder: str,
    filter_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Reads a partitioned Parquet dataset into a Pandas DataFrame.

    If filter_date is specified, data is filtered by the detected date column.
    filter_date must use YYYY-MM-DD format.
    """
    parquet_path = Path(parquet_folder).expanduser().resolve()

    if not parquet_path.exists():
        raise FileNotFoundError(
            f"Parquet folder was not found: {parquet_path}"
        )

    parquet_files = list(parquet_path.rglob("*.parquet"))

    if not parquet_files:
        raise FileNotFoundError(
            f"No .parquet files were found in: {parquet_path}"
        )

    # Hive partitioning supports folders such as visit_date=2025-06-19.
    dataset = ds.dataset(
        str(parquet_path),
        format="parquet",
        partitioning="hive",
    )

    dataframe = dataset.to_table().to_pandas()

    if dataframe.empty:
        raise AssertionError("The Parquet dataset is empty.")

    if filter_date is None or str(filter_date).strip() == "":
        return dataframe

    filter_date = str(filter_date).strip()

    try:
        expected_date = datetime.strptime(filter_date, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError(
            "FILTER_DATE must use YYYY-MM-DD format. "
            f"Received: {filter_date}"
        ) from error

    date_column = find_date_column(dataframe)

    if date_column is None:
        raise ValueError(
            "A date filter was provided, but no date column was found. "
            f"Available columns: {list(dataframe.columns)}"
        )

    parsed_dates = pd.to_datetime(
        dataframe[date_column],
        errors="coerce",
    ).dt.date

    filtered_dataframe = dataframe.loc[
        parsed_dates == expected_date
    ].copy()

    if filtered_dataframe.empty:
        raise AssertionError(
            f"No Parquet rows were found for FILTER_DATE={filter_date}."
        )

    return filtered_dataframe


def normalize_cell_value(value: Any, column_name: str) -> str:
    """
    Converts values to a common comparable string format.
    """
    if pd.isna(value):
        return "<NULL>"

    if column_name == "visit_date":
        parsed_date = pd.to_datetime(value, errors="coerce")

        if not pd.isna(parsed_date):
            return parsed_date.strftime("%Y-%m-%d")

    if isinstance(value, bool):
        return str(value).lower()

    if isinstance(value, (int, float)):
        numeric_value = float(value)

        if numeric_value.is_integer():
            return str(int(numeric_value))

        return format(numeric_value, ".15g")

    text_value = str(value).strip()

    try:
        numeric_value = float(text_value)

        if numeric_value.is_integer():
            return str(int(numeric_value))

        return format(numeric_value, ".15g")
    except ValueError:
        return text_value


def prepare_dataframe_for_comparison(
    dataframe: pd.DataFrame,
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Normalizes column names, values, and row order before comparison.
    """
    prepared = dataframe.copy()

    prepared.columns = [
        normalize_column_name(column)
        for column in prepared.columns
    ]

    duplicate_columns = prepared.columns[
        prepared.columns.duplicated()
    ].tolist()

    if duplicate_columns:
        return prepared, duplicate_columns

    for column in prepared.columns:
        prepared[column] = prepared[column].apply(
            lambda value: normalize_cell_value(value, column)
        )

    prepared = prepared.sort_values(
        by=list(prepared.columns),
        kind="stable",
    ).reset_index(drop=True)

    return prepared, []


def format_counter_difference(
    counter: Counter,
    columns: List[str],
    title: str,
) -> str:
    """
    Formats missing or extra rows into a readable text report.
    """
    if not counter:
        return ""

    rows = []

    for values, count in counter.items():
        row = dict(zip(columns, values))
        row["occurrences"] = count
        rows.append(row)

    difference_dataframe = pd.DataFrame(rows)

    if len(difference_dataframe) > 50:
        difference_dataframe = difference_dataframe.head(50)
        suffix = "\nOnly the first 50 differences are shown."
    else:
        suffix = ""

    return (
        f"{title}:\n"
        f"{difference_dataframe.to_string(index=False)}"
        f"{suffix}"
    )


def compare_dataframes_exactly(
    html_dataframe: pd.DataFrame,
    parquet_dataframe: pd.DataFrame,
) -> str:
    """
    Compares HTML and Parquet DataFrames.

    Returns an empty string when data matches.
    Returns a detailed mismatch report when data differs.

    Row order is ignored, but all values and duplicate rows are compared.
    """
    html_prepared, html_duplicates = prepare_dataframe_for_comparison(
        html_dataframe
    )
    parquet_prepared, parquet_duplicates = prepare_dataframe_for_comparison(
        parquet_dataframe
    )

    differences = []

    if html_duplicates:
        differences.append(
            f"Duplicate normalized columns in HTML table: {html_duplicates}"
        )

    if parquet_duplicates:
        differences.append(
            f"Duplicate normalized columns in Parquet dataset: {parquet_duplicates}"
        )

    html_columns = list(html_prepared.columns)
    parquet_columns = list(parquet_prepared.columns)

    if html_columns != parquet_columns:
        differences.append(
            "Column mismatch:\n"
            f"HTML columns: {html_columns}\n"
            f"Parquet columns: {parquet_columns}"
        )
        return "\n\n".join(differences)

    html_counter = Counter(
        map(
            tuple,
            html_prepared.itertuples(index=False, name=None),
        )
    )

    parquet_counter = Counter(
        map(
            tuple,
            parquet_prepared.itertuples(index=False, name=None),
        )
    )

    html_only = html_counter - parquet_counter
    parquet_only = parquet_counter - html_counter

    html_only_message = format_counter_difference(
        html_only,
        html_columns,
        "Rows present only in the HTML report",
    )

    parquet_only_message = format_counter_difference(
        parquet_only,
        parquet_columns,
        "Rows present only in the Parquet dataset",
    )

    if html_only_message:
        differences.append(html_only_message)

    if parquet_only_message:
        differences.append(parquet_only_message)

    return "\n\n".join(differences)
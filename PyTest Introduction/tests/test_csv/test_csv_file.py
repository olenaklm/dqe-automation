import pytest
import re


EMAIL_PATTERN = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
)


def test_file_not_empty(path_to_file, csv_data):
    """
    Validate that:
    1. The CSV file exists.
    2. The file is not physically empty.
    3. The file has at least one data row.
    """

    assert path_to_file.exists(), (
        f"CSV file was not found. Expected path: {path_to_file}"
    )

    assert path_to_file.stat().st_size > 0, (
        f"CSV file is physically empty: {path_to_file}"
    )

    assert not csv_data.empty, (
        "CSV file contains no data rows. "
        "The file may be empty or contain headers only."
    )


@pytest.mark.validate_csv
@pytest.mark.xfail(
    reason="Known training-data issue: duplicate rows may exist in the CSV file."
)
def test_duplicates(csv_data):
    """
    Validate that the CSV file has no fully duplicate rows.

    This test is intentionally marked as xfail according to
    the homework requirements.
    """

    duplicate_rows = csv_data.loc[
        csv_data.duplicated(keep=False)
    ].copy()

    duplicate_rows["csv_row_number"] = duplicate_rows.index + 2

    assert duplicate_rows.empty, (
        "Duplicate rows were found in the CSV file. "
        f"Duplicate records: {duplicate_rows.to_dict(orient='records')}"
    )


@pytest.mark.validate_csv
def test_validate_schema(
    validate_schema,
    actual_schema,
    expected_schema
):
    """
    Validate that the CSV columns exactly match the required schema.
    """

    assert validate_schema, (
        "CSV schema is incorrect. "
        f"Expected schema: {expected_schema}. "
        f"Actual schema: {actual_schema}."
    )


@pytest.mark.validate_csv
@pytest.mark.skip(
    reason="Skipped according to homework requirements."
)
def test_age_column_valid(csv_data):
    """
    Validate that age values are whole numbers between 0 and 100.

    The test is implemented but skipped as required by the task.
    """

    age_values = csv_data["age"]

    numeric_age = age_values.apply(
        lambda value: None
        if str(value).strip() == ""
        else _convert_to_number(value)
    )

    invalid_rows = csv_data.loc[
        numeric_age.isna()
        | ~numeric_age.between(0, 100)
        | numeric_age.mod(1).ne(0),
        ["id", "age"]
    ].copy()

    invalid_rows["csv_row_number"] = invalid_rows.index + 2

    assert invalid_rows.empty, (
        "Age values must be whole numbers from 0 to 100. "
        f"Invalid records: {invalid_rows.to_dict(orient='records')}"
    )


def _convert_to_number(value):
    """
    Converts a value to float.

    Returns None when conversion is impossible.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@pytest.mark.validate_csv
def test_email_column_valid(csv_data):
    """
    Validate that each email has a basic valid email format.
    """

    invalid_records = []

    for index, row in csv_data.iterrows():
        email = str(row["email"]).strip()

        if not EMAIL_PATTERN.fullmatch(email):
            invalid_records.append(
                {
                    "csv_row_number": index + 2,
                    "id": row["id"],
                    "email": email,
                }
            )

    assert not invalid_records, (
        "Invalid email addresses were found in the CSV file. "
        f"Invalid records: {invalid_records}"
    )


@pytest.mark.parametrize(
    "record_id, expected_is_active",
    [
        (1, False),
        (2, True),
    ],
    ids=[
        "id_1_should_be_inactive",
        "id_2_should_be_active",
    ]
)
def test_active_players(csv_data, record_id, expected_is_active):
    """
    Parameterized validation:

    - id=1 must have is_active=False;
    - id=2 must have is_active=True.
    """

    matching_rows = csv_data.loc[
        csv_data["id"].astype(str).str.strip() == str(record_id)
    ]

    assert len(matching_rows) == 1, (
        f"Expected exactly one row for id={record_id}, "
        f"but found {len(matching_rows)} rows."
    )

    actual_value = str(
        matching_rows.iloc[0]["is_active"]
    ).strip().lower()

    expected_value = str(expected_is_active).lower()

    assert actual_value == expected_value, (
        f"Incorrect is_active value for id={record_id}. "
        f"Expected: {expected_value}. "
        f"Actual: {actual_value}."
    )


def test_active_player(csv_data):
    """
    Validate id=2 without using pytest.mark.parametrize.

    This test has no explicit mark, so the PyTest hook in conftest.py
    automatically adds the custom 'unmarked' mark.
    """

    matching_rows = csv_data.loc[
        csv_data["id"].astype(str).str.strip() == "2"
    ]

    assert len(matching_rows) == 1, (
        "Expected exactly one row for id=2, "
        f"but found {len(matching_rows)} rows."
    )

    actual_value = str(
        matching_rows.iloc[0]["is_active"]
    ).strip().lower()

    assert actual_value == "true", (
        "Incorrect is_active value for id=2. "
        f"Expected: true. "
        f"Actual: {actual_value}."
    )

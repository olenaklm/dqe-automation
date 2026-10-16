from pathlib import Path

import pytest
import pandas as pd


# Fixture to get the path to the CSV file
@pytest.fixture(scope="session")
def path_to_file():
    """
    Returns the absolute path to the tested CSV file.
    """
    return (
        Path(__file__).resolve().parents[1]
        / "src"
        / "data"
        / "data.csv"
    )


# Fixture to read the CSV file
@pytest.fixture(scope="session")
def csv_data(path_to_file):
    """
    Reads the CSV file and returns its content as a pandas DataFrame.

    Parameter:
        path_to_file: path received from the path_to_file fixture.
    """
    try:
        return pd.read_csv(path_to_file)
    except pd.errors.EmptyDataError:
        # Allows test_file_not_empty to fail with a clear assertion message
        # instead of producing an unhandled pandas exception.
        return pd.DataFrame()


# Fixture to get the actual CSV schema
@pytest.fixture(scope="session")
def actual_schema(csv_data):
    """
    Returns column names found in the CSV file.
    """
    return list(csv_data.columns)


# Fixture to define the expected CSV schema
@pytest.fixture(scope="session")
def expected_schema():
    """
    Returns column names required by the task.
    """
    return ["id", "name", "age", "email", "is_active"]


# Fixture to validate the schema of the file
@pytest.fixture(scope="session")
def validate_schema(actual_schema, expected_schema):
    """
    Compares actual and expected schemas.

    Parameters:
        actual_schema: schema received from the CSV file;
        expected_schema: schema required by the task.

    Returns:
        True if schemas match exactly; otherwise False.
    """
    return actual_schema == expected_schema


# Pytest hook to mark unmarked tests with a custom mark
def pytest_collection_modifyitems(config, items):
    """
    Adds custom mark 'unmarked' to every test that has no explicitly
    assigned PyTest marks.
    """
    for item in items:
        if not item.own_markers:
            item.add_marker(pytest.mark.unmarked)
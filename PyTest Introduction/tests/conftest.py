# import pytest
# import pandas as pd

# Fixture to read the CSV file


# Fixture to validate the schema of the file


# Pytest hook to mark unmarked tests with a custom mark

import pytest
import pandas as pd
import os

def pytest_addoption(parser):
    parser.addoption(
        "--csv-path",
        action="store",
        default="src/data/data.csv",
        help="Path to the CSV file for tests"
    )

@pytest.fixture(scope="session")
def csv_path(request):
    # Get the path from the pytest option or by default
    rel_path = request.config.getoption("--csv-path")
    abs_path = os.path.abspath(rel_path)
    return abs_path

@pytest.fixture(scope="session")
def csv_read(csv_path):
    df = pd.read_csv(csv_path)
    return df

@pytest.fixture(scope="session")
def expected_schema():
    return ["id", "name", "age", "email", "is_active"]

@pytest.fixture(scope="session")
def actual_schema(csv_read):
    return list(csv_read.columns)

@pytest.fixture
def validate_schema():
    def _validate(actual_schema, expected_schema):
        assert set(actual_schema) == set(expected_schema), (
            f"The scheme does not match: {actual_schema} != {expected_schema}"
        )
    return _validate

def pytest_collection_modifyitems(session, config, items):
    for item in items:
        if not item.own_markers:
            item.add_marker(pytest.mark.unmarked)
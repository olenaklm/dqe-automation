# import pytest
# import pandas as pd

# Fixture to read the CSV file


# Fixture to validate the schema of the file


# Pytest hook to mark unmarked tests with a custom mark

import pytest
import pandas as pd

def pytest_collection_modifyitems(session, config, items):
    for item in items:
        if not item.own_markers:
            item.add_marker(pytest.mark.unmarked)

@pytest.fixture(scope="session")
def csv_df():
    path = "src/data/data.csv"
    df = pd.read_csv(path)
    return df

@pytest.fixture(scope="session")
def expected_schema():
    return ["id", "name", "age", "email", "is_active"]

@pytest.fixture(scope="session")
def actual_schema(csv_df):
    return list(csv_df.columns)
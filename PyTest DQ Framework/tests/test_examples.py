import pandas as pd
import pytest


@pytest.mark.example
def test_example_data_quality_checks(data_quality_library):
    """
    Technical framework example.

    This test validates reusable DataQualityLibrary methods without using
    production PostgreSQL queries or production Parquet datasets.
    """
    source_data = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["Anna", "John", "Maria"],
        }
    )

    target_data = pd.DataFrame(
        {
            "id": [3, 1, 2],
            "name": ["Maria", "Anna", "John"],
        }
    )

    data_quality_library.check_dataset_is_not_empty(target_data)

    data_quality_library.check_data_completeness(
        source_data,
        target_data,
    )

    data_quality_library.check_count(
        source_data,
        target_data,
    )

    data_quality_library.check_duplicates(target_data)

    data_quality_library.check_not_null_values(
        target_data,
        ["id", "name"],
    )

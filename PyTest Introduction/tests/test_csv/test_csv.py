import pytest
import re

@pytest.mark.validate_csv
def test_file_not_empty(csv_df):
    assert not csv_df.empty, "CSV-file is empty"

@pytest.mark.validate_csv
def test_schema(actual_schema, expected_schema):
    assert set(actual_schema) == set(expected_schema), f"The file schema isn't correct: {actual_schema} != {expected_schema}"

@pytest.mark.validate_csv
@pytest.mark.skip(reason="Age verification is temporarily disabled")
def test_age_valid(csv_df):
    invalid_ages = csv_df[~csv_df['age'].between(0, 100)]
    assert invalid_ages.empty, f"Incorrect age values: {invalid_ages['age'].tolist()}"

@pytest.mark.validate_csv
def test_email_format(csv_df):
    pattern = r"[^@]+@[^@]+\.[^@]+"
    invalid_emails = csv_df[~csv_df['email'].str.match(pattern)]
    assert invalid_emails.empty, f"Incorrect email addresses: {invalid_emails['email'].tolist()}"

@pytest.mark.validate_csv
@pytest.mark.xfail(reason="Duplicates are expected")
def test_no_duplicates(csv_df):
    duplicates = csv_df[csv_df.duplicated()]
    assert duplicates.empty, f"Duplicates found: {duplicates}"

@pytest.mark.parametrize("id, is_active", [(1, False), (2, True)])
def test_is_active(csv_df, id, is_active):
    row = csv_df[csv_df['id'] == id]
    assert not row.empty, f"Row with id={id} not found"
    actual = row.iloc[0]['is_active']
    assert str(actual) == str(is_active), f"id={id}: is_active should be {is_active}, not {actual}"

def test_is_active_id2(csv_df):
    row = csv_df[csv_df['id'] == 2]
    assert not row.empty, "Row with id=2 not found"
    actual = row.iloc[0]['is_active']
    assert str(actual) == "True", f"id=2: is_active should be True, а not {actual}"
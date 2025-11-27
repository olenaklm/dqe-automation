import pytest
import re

@pytest.mark.validate_csv
def test_file_not_empty(csv_read):
    assert not csv_read.empty, "CSV-file is empty"

@pytest.mark.validate_csv
def test_schema(actual_schema, expected_schema, validate_schema):
    validate_schema(actual_schema, expected_schema)

@pytest.mark.validate_csv
@pytest.mark.skip(reason="Age verification is temporarily disabled")
def test_age_valid(csv_read):
    invalid_ages = csv_read[~csv_read['age'].between(0, 100)]
    assert invalid_ages.empty, f"Incorrect age values: {invalid_ages['age'].tolist()}"

@pytest.mark.validate_csv
def test_email_format(csv_read):
    pattern = r"[^@]+@[^@]+\.[^@]+"
    invalid_emails = csv_read[~csv_read['email'].str.match(pattern)]
    assert invalid_emails.empty, f"Incorrect email addresses: {invalid_emails['email'].tolist()}"

@pytest.mark.validate_csv
@pytest.mark.xfail(reason="Duplicates are expected")
def test_no_duplicates(csv_read):
    duplicates = csv_read[csv_read.duplicated()]
    assert duplicates.empty, f"Duplicates found: {duplicates}"

@pytest.mark.parametrize("id, is_active", [(1, False), (2, True)])
def test_is_active(csv_read, id, is_active):
    row = csv_read[csv_read['id'] == id]
    actual = row.iloc[0]['is_active']
    assert str(actual) == str(is_active), f"id={id}: is_active should be {is_active}, not {actual}"

def test_is_active_id2(csv_read):
    row = csv_read[csv_read['id'] == 2]
    actual = row.iloc[0]['is_active']
    assert str(actual) == "True", f"id=2: is_active should be True, not {actual}"    
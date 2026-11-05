from pathlib import Path
import sys
from typing import Generator

import pytest


FRAMEWORK_ROOT = Path(__file__).resolve().parents[1]

if str(FRAMEWORK_ROOT) not in sys.path:
    sys.path.insert(0, str(FRAMEWORK_ROOT))


from src.connectors.file_system.parquet_reader import ParquetReader
from src.connectors.postgres.postgres_connector import (
    PostgresConnectorContextManager,
)
from src.data_quality.data_quality_validation_library import (
    DataQualityLibrary,
)


def pytest_addoption(parser):
    """
    Register command-line options required for PostgreSQL connection.
    """
    database_group = parser.getgroup("database")

    database_group.addoption(
        "--db_host",
        action="store",
        default=None,
        help="PostgreSQL host name or IP address.",
    )

    database_group.addoption(
        "--db_port",
        action="store",
        default=None,
        help="PostgreSQL port number.",
    )

    database_group.addoption(
        "--db_name",
        action="store",
        default=None,
        help="PostgreSQL database name.",
    )

    database_group.addoption(
        "--db_user",
        action="store",
        default=None,
        help="PostgreSQL user name.",
    )

    database_group.addoption(
        "--db_password",
        action="store",
        default=None,
        help="PostgreSQL password.",
    )


def _get_required_option(request, option_name: str) -> str:
    """
    Return a required pytest CLI option or stop pytest with a clear error.
    """
    value = request.config.getoption(option_name)

    if value is None or not str(value).strip():
        raise pytest.UsageError(
            f"Required pytest option is missing: --{option_name}"
        )

    return str(value).strip()


@pytest.fixture(scope="session")
def db_connection(request) -> Generator[PostgresConnectorContextManager, None, None]:
    """
    Create one PostgreSQL connection for the complete PyTest session.

    Database connection values must be passed through pytest CLI arguments.
    """
    db_host = _get_required_option(request, "db_host")
    db_name = _get_required_option(request, "db_name")
    db_user = _get_required_option(request, "db_user")
    db_password = _get_required_option(request, "db_password")
    db_port_value = _get_required_option(request, "db_port")

    try:
        db_port = int(db_port_value)
    except ValueError as exc:
        raise pytest.UsageError(
            f"--db_port must be an integer, received: {db_port_value}"
        ) from exc

    with PostgresConnectorContextManager(
        db_host=db_host,
        db_port=db_port,
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
    ) as connection:
        yield connection


@pytest.fixture(scope="session")
def parquet_reader() -> ParquetReader:
    """
    Return shared ParquetReader instance.
    """
    return ParquetReader()


@pytest.fixture(scope="session")
def data_quality_library() -> DataQualityLibrary:
    """
    Return shared DataQualityLibrary instance.
    """
    return DataQualityLibrary()

from typing import Any, Dict, Optional

import pandas as pd
import psycopg2


class PostgresConnectorContextManager:
    """
    PostgreSQL connector implemented as a context manager.

    The connector is intended to be used with a with statement:

        with PostgresConnectorContextManager(...) as db_connection:
            data = db_connection.get_data_sql("SELECT ...")
    """

    def __init__(
        self,
        db_host: str = "localhost",
        db_name: str = "",
        db_user: str = "",
        db_password: str = "",
        db_port: int = 5432,
        **connection_kwargs: Any,
    ) -> None:
        """
        Initialize PostgreSQL connection settings.

        Args:
            db_host: PostgreSQL host.
            db_name: PostgreSQL database name.
            db_user: PostgreSQL user name.
            db_password: PostgreSQL password.
            db_port: PostgreSQL port.
            **connection_kwargs: Additional psycopg2 connection parameters.
        """
        self.db_host = db_host
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.db_port = db_port
        self.connection_kwargs: Dict[str, Any] = connection_kwargs
        self.connection = None

    def __enter__(self) -> "PostgresConnectorContextManager":
        """
        Open PostgreSQL connection and return connector instance.
        """
        self.connection = psycopg2.connect(
            host=self.db_host,
            dbname=self.db_name,
            user=self.db_user,
            password=self.db_password,
            port=self.db_port,
            **self.connection_kwargs,
        )

        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_value: Optional[BaseException],
        exc_traceback: Any,
    ) -> bool:
        """
        Commit successful transaction or rollback failed transaction,
        then always close the PostgreSQL connection.
        """
        if self.connection is None:
            return False

        try:
            if exc_type is None:
                self.connection.commit()
            else:
                self.connection.rollback()
        finally:
            self.connection.close()
            self.connection = None

        return False

    def get_data_sql(
        self,
        sql: str,
        params: Optional[tuple] = None,
    ) -> pd.DataFrame:
        """
        Execute a SQL query and return its result as a pandas DataFrame.

        Args:
            sql: SQL SELECT query.
            params: Optional parameters for a parameterized SQL query.

        Returns:
            DataFrame containing SQL query results.

        Raises:
            RuntimeError: If method is called outside active context manager.
            psycopg2.Error: If PostgreSQL cannot execute the query.
        """
        if self.connection is None:
            raise RuntimeError(
                "Database connection is not active. "
                "Use PostgresConnectorContextManager inside a with statement."
            )

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)

                if cursor.description is None:
                    raise ValueError(
                        "get_data_sql requires a SQL query that returns data, "
                        "such as SELECT."
                    )

                columns = [
                    column[0]
                    for column in cursor.description
                ]

                rows = cursor.fetchall()

            return pd.DataFrame(
                rows,
                columns=columns,
            )
        except Exception:
            self.connection.rollback()
            raise

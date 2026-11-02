import pandas as pd
import psycopg2


class PostgresConnectorContextManager:
    def __init__(
        self,
        db_host: str = "localhost",
        db_name: str = "",
        db_user: str = "",
        db_password: str = "",
        db_port: int = 5432,
        **connection_kwargs,
    ):
        self.db_host = db_host
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.db_port = db_port
        self.connection_kwargs = connection_kwargs
        self.connection = None

    def __enter__(self):
        self.connection = psycopg2.connect(
            host=self.db_host,
            dbname=self.db_name,
            user=self.db_user,
            password=self.db_password,
            port=self.db_port,
            **self.connection_kwargs,
        )
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        try:
            if self.connection is not None:
                if exc_type is None:
                    self.connection.commit()
                else:
                    self.connection.rollback()
                self.connection.close()
        finally:
            self.connection = None
        return False

    def get_data_sql(self, sql, params=None):
        if self.connection is None:
            self.__enter__()

        try:
            with self.connection.cursor() as cursor:
                if params is None:
                    cursor.execute(sql)
                else:
                    cursor.execute(sql, params)
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()

            return pd.DataFrame(rows, columns=columns)
        except Exception:
            if self.connection is not None:
                self.connection.rollback()
            raise

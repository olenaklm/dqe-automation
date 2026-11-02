from typing import Optional, Sequence

import pandas as pd


class DataQualityLibrary:
    """
    A reusable library for performing Data Quality checks on pandas DataFrames.

    The methods are designed for use in PyTest tests. Each failed check raises
    AssertionError with a descriptive message.
    """

    @staticmethod
    def _validate_dataframe(data, label: str) -> pd.DataFrame:
        """
        Validate that data is a non-None pandas DataFrame.
        """
        if data is None:
            raise AssertionError(f"{label} is None.")

        if not isinstance(data, pd.DataFrame):
            raise AssertionError(
                f"{label} must be a pandas DataFrame, "
                f"got {type(data).__name__}."
            )

        return data

    @staticmethod
    def _normalize_for_comparison(
        data: pd.DataFrame,
        columns: Sequence[str],
    ) -> pd.DataFrame:
        """
        Select comparison columns, normalize NULL values and sort rows.

        Sorting makes source/target comparison independent from row order.
        """
        frame = data.loc[:, list(columns)].copy()

        for column in frame.columns:
            frame[column] = (
                frame[column]
                .astype(object)
                .where(pd.notna(frame[column]), None)
            )

        sort_key = frame.apply(
            lambda row: tuple(
                "" if pd.isna(value) else str(value)
                for value in row.tolist()
            ),
            axis=1,
        )

        normalized = (
            frame.assign(_dq_sort_key=sort_key)
            .sort_values(by="_dq_sort_key", kind="mergesort")
            .drop(columns=["_dq_sort_key"])
            .reset_index(drop=True)
        )

        return normalized

    def check_dataset_is_not_empty(self, data) -> None:
        """
        Fail if the dataset is missing or contains zero rows.
        """
        df = self._validate_dataframe(data, "Dataset")

        assert not df.empty, (
            "Dataset is empty. Expected a non-empty DataFrame."
        )

    def check_data_completeness(
        self,
        source_data,
        target_data,
    ) -> None:
        """
        Validate that expected PostgreSQL data matches actual Parquet data.

        The comparison ignores row order but checks all mapped source columns,
        row values, and duplicate row occurrences.
        """
        source_df = self._validate_dataframe(
            source_data,
            "source_data",
        )
        target_df = self._validate_dataframe(
            target_data,
            "target_data",
        )

        source_columns = list(source_df.columns)
        target_columns = list(target_df.columns)

        missing_columns = [
            column
            for column in source_columns
            if column not in target_columns
        ]

        if missing_columns:
            raise AssertionError(
                "Target data is missing expected columns: "
                f"{missing_columns}. "
                f"Source columns: {source_columns}. "
                f"Target columns: {target_columns}."
            )

        ordered_source = self._normalize_for_comparison(
            source_df,
            source_columns,
        )
        ordered_target = self._normalize_for_comparison(
            target_df,
            source_columns,
        )

        try:
            pd.testing.assert_frame_equal(
                ordered_source,
                ordered_target,
                check_dtype=False,
                check_exact=True,
            )
        except AssertionError as exc:
            raise AssertionError(
                "Data completeness check failed. "
                "Expected PostgreSQL data does not match actual Parquet data "
                f"after normalizing row order. Details: {exc}"
            ) from exc

    def check_count(self, source_data, target_data) -> None:
        """
        Compare expected PostgreSQL and actual Parquet row counts.
        """
        source_df = self._validate_dataframe(
            source_data,
            "source_data",
        )
        target_df = self._validate_dataframe(
            target_data,
            "target_data",
        )

        expected_count = len(source_df)
        actual_count = len(target_df)

        assert expected_count == actual_count, (
            "Row count mismatch. "
            f"Expected PostgreSQL row count: {expected_count}. "
            f"Actual Parquet row count: {actual_count}."
        )

    def check_duplicates(
        self,
        data,
        column_names: Optional[Sequence[str]] = None,
    ) -> None:
        """
        Fail when duplicate records are found.

        If column_names is provided, duplicate detection is based on those
        columns. Otherwise, all DataFrame columns are used.
        """
        df = self._validate_dataframe(data, "Dataset")

        if column_names is not None:
            column_names = list(column_names)

            missing_columns = [
                column
                for column in column_names
                if column not in df.columns
            ]

            if missing_columns:
                raise AssertionError(
                    "Cannot check duplicates because requested columns are "
                    f"missing: {missing_columns}. "
                    f"Available columns: {list(df.columns)}."
                )

            duplicate_mask = df.duplicated(
                subset=column_names,
                keep=False,
            )
        else:
            duplicate_mask = df.duplicated(keep=False)

        duplicate_count = int(duplicate_mask.sum())

        if duplicate_count == 0:
            return

        duplicate_sample = (
            df.loc[duplicate_mask]
            .head(10)
            .to_dict(orient="records")
        )

        checked_columns = (
            list(column_names)
            if column_names is not None
            else list(df.columns)
        )

        raise AssertionError(
            "Duplicate rows detected. "
            f"Duplicate row count: {duplicate_count}. "
            f"Columns used for uniqueness: {checked_columns}. "
            f"Sample duplicate records: {duplicate_sample}"
        )

    def check_not_null_values(
        self,
        data,
        columns: Optional[Sequence[str]] = None,
    ) -> None:
        """
        Validate that requested columns exist and contain no NULL or NaN values.

        If columns is omitted, all DataFrame columns are validated.
        """
        df = self._validate_dataframe(data, "Dataset")

        if columns is None:
            requested_columns = list(df.columns)
        else:
            requested_columns = list(columns)

        missing_columns = [
            column
            for column in requested_columns
            if column not in df.columns
        ]

        if missing_columns:
            raise AssertionError(
                "Requested columns are missing from the DataFrame: "
                f"{missing_columns}. "
                f"Available columns: {list(df.columns)}."
            )

        null_counts = {
            column: int(df[column].isna().sum())
            for column in requested_columns
            if int(df[column].isna().sum()) > 0
        }

        if null_counts:
            details = ", ".join(
                f"{column}={count}"
                for column, count in null_counts.items()
            )

            raise AssertionError(
                "NULL or NaN values found in required columns: "
                f"{details}."
            )

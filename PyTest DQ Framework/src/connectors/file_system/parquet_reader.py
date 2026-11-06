from __future__ import annotations

from pathlib import Path
from typing import List, Union

import pandas as pd


class ParquetReader:
    """
    Reusable helper for loading one or more Parquet files into a pandas DataFrame.
    """

    def process(
        self,
        path: Union[str, Path],
        include_subfolders: bool = True,
    ) -> pd.DataFrame:
        """
        Read one Parquet file or merge multiple Parquet files into one DataFrame.

        Args:
            path: Path to a Parquet file or a directory containing Parquet files.
            include_subfolders: If True and path is a directory, recursively
                search nested directories for Parquet files.

        Returns:
            A pandas DataFrame containing the combined Parquet data.

        Raises:
            FileNotFoundError: If the provided path does not exist.
            ValueError: If a provided file is not a Parquet file, if the path
                is unsupported, or if no Parquet files are found.
        """
        file_path = Path(path)

        if not file_path.exists():
            raise FileNotFoundError(
                f"Parquet path does not exist: {file_path}"
            )

        if file_path.is_file():
            if file_path.suffix.lower() != ".parquet":
                raise ValueError(
                    f"File is not a Parquet file: {file_path}"
                )

            return pd.read_parquet(
                file_path,
                engine="pyarrow",
            )

        if not file_path.is_dir():
            raise ValueError(
                f"Unsupported Parquet path: {file_path}"
            )

        parquet_files = self._find_parquet_files(
            directory=file_path,
            include_subfolders=include_subfolders,
        )

        if not parquet_files:
            raise ValueError(
                f"No Parquet files found in directory: {file_path}"
            )

        frames = [
            pd.read_parquet(
                parquet_file,
                engine="pyarrow",
            )
            for parquet_file in parquet_files
        ]

        return pd.concat(
            frames,
            ignore_index=True,
        )

    def _find_parquet_files(
        self,
        directory: Path,
        include_subfolders: bool,
    ) -> List[Path]:
        """
        Return sorted Parquet file paths from the provided directory.

        Args:
            directory: Directory in which Parquet files are searched.
            include_subfolders: If True, search recursively.

        Returns:
            Sorted list of paths to Parquet files.
        """
        if include_subfolders:
            candidate_paths = directory.rglob("*")
        else:
            candidate_paths = directory.glob("*")

        parquet_files = [
            item
            for item in candidate_paths
            if item.is_file() and item.suffix.lower() == ".parquet"
        ]

        return sorted(
            parquet_files,
            key=lambda item: str(item),
        )

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Union

import pandas as pd


class ParquetReader:
    """Reusable helper for loading one or more Parquet files into a pandas DataFrame."""

    def process(self, path: Union[str, Path], include_subfolders: bool = True) -> pd.DataFrame:
        """
        Read one Parquet file or merge multiple Parquet files into a single DataFrame.

        Args:
            path: Path to a Parquet file or directory.
            include_subfolders: If True and path is a directory, search recursively for files.

        Returns:
            A pandas DataFrame containing the combined Parquet data.

        Raises:
            FileNotFoundError: If the provided path does not exist.
            ValueError: If a directory contains no Parquet files or a file is not a Parquet file.
        """
        file_path = Path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"Parquet path does not exist: {file_path}")

        if file_path.is_file():
            if file_path.suffix.lower() != ".parquet":
                raise ValueError(f"File is not a Parquet file: {file_path}")
            return pd.read_parquet(file_path)

        if not file_path.is_dir():
            raise ValueError(f"Unsupported Parquet path: {file_path}")

        parquet_files = self._find_parquet_files(file_path, include_subfolders)

        if not parquet_files:
            raise ValueError(f"No Parquet files found in directory: {file_path}")

        frames = [pd.read_parquet(parquet_file) for parquet_file in parquet_files]
        if not frames:
            raise ValueError(f"No Parquet files found in directory: {file_path}")

        return pd.concat(frames, ignore_index=True)

    def _find_parquet_files(self, directory: Path, include_subfolders: bool) -> List[Path]:
        """Return sorted Parquet file paths for the provided directory."""
        if include_subfolders:
            parquet_files = list(directory.rglob("*.parquet"))
        else:
            parquet_files = list(directory.glob("*.parquet"))

        return sorted(parquet_files, key=lambda item: str(item))

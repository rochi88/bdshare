# -*- coding: utf-8 -*-
"""
bdshare.util.store
~~~~~~~~~~~~~~~~~~
Data Storage Manager

Features:
- Multiple file format support (CSV, Excel, Parquet, JSON, Feather)
- Automatic directory creation
- Comprehensive error handling
- Type hints and documentation
- File existence checks
- Compression options
- Round-trip loading via Store.from_file()
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional, Union, get_args

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported values, derived once from the Literal types
# ---------------------------------------------------------------------------
SupportedFormat   = Literal["csv", "excel", "parquet", "json", "feather"]
CompressionOption = Literal["gzip", "bz2", "zip", "xz", None]

_FORMATS     = get_args(SupportedFormat)    # ('csv', 'excel', 'parquet', 'json', 'feather')
_COMPRESSION = get_args(CompressionOption)  # ('gzip', 'bz2', 'zip', 'xz', None)

_EXT_MAP = {
    "excel": "xlsx",  # .xlsx on disk, 'excel' as format name
}


class Store:
    """
    A robust data storage manager for pandas DataFrames.

    Parameters
    ----------
    data : pd.DataFrame
        The pandas DataFrame to be stored.
    name : str, optional
        Base filename without extension. Defaults to a ``YYYYMMDD-HHMMSS``
        timestamp.
    path : str or Path, optional
        Directory for output files. Defaults to the current working directory.

    Examples
    --------
    Basic save::

        from bdshare import get_current_trade_data
        from bdshare.util import Store

        df = get_current_trade_data()
        Store(df).save()                            # timestamped CSV in cwd
        Store(df, name="trades").save()             # trades.csv in cwd
        Store(df, name="trades", path="/tmp").save("parquet")

    Multi-format::

        Store(df, name="snapshot").save_multiple(["csv", "parquet"])

    Round-trip::

        store = Store.from_file("snapshot.csv")
        print(store.data.head())
    """

    def __init__(
        self,
        data: pd.DataFrame,
        name: Optional[str] = None,
        path: Optional[Union[str, Path]] = None,
    ):
        if not isinstance(data, pd.DataFrame):
            raise TypeError(f"Expected pandas DataFrame, got {type(data).__name__}")

        self.data = data
        self.name = name or datetime.now().strftime("%Y%m%d-%H%M%S")
        self.path = Path(path) if path else Path.cwd()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_format(self, fmt: str) -> None:
        if fmt not in _FORMATS:
            raise ValueError(
                f"Unsupported format {fmt!r}. Choose from: {_FORMATS}"
            )

    def _validate_compression(self, compression: Optional[str]) -> None:
        if compression not in _COMPRESSION:
            raise ValueError(
                f"Unsupported compression {compression!r}. "
                f"Choose from: {_COMPRESSION}"
            )

    def _build_path(self, fmt: str) -> Path:
        ext = _EXT_MAP.get(fmt, fmt)
        return self.path / f"{self.name}.{ext}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(
        self,
        fmt: SupportedFormat = "csv",
        compression: CompressionOption = None,
        index: bool = False,
        **kwargs,
    ) -> Path:
        """
        Save the DataFrame to disk in the specified format.

        Parameters
        ----------
        fmt : str
            Output format: ``'csv'``, ``'excel'``, ``'parquet'``,
            ``'json'``, or ``'feather'``.
        compression : str or None
            Compression codec (``'gzip'``, ``'bz2'``, ``'zip'``, ``'xz'``).
            Not applicable to Excel or Feather.
        index : bool
            Whether to write the row index. Default ``False``.
        **kwargs
            Forwarded to the underlying pandas writer.

        Returns
        -------
        Path
            Absolute path of the saved file.

        Raises
        ------
        ValueError
            If *fmt* or *compression* is not supported.
        IOError
            If the file cannot be written.
        """
        self._validate_format(fmt)
        self._validate_compression(compression)

        try:
            self.path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error("Failed to create directory %s: %s", self.path, exc)
            raise

        file_path = self._build_path(fmt)

        try:
            if fmt == "csv":
                self.data.to_csv(file_path, index=index,
                                 compression=compression, **kwargs)
            elif fmt == "excel":
                self.data.to_excel(file_path, index=index, **kwargs)
            elif fmt == "parquet":
                self.data.to_parquet(file_path, index=index,
                                     compression=compression or "snappy", **kwargs)
            elif fmt == "json":
                self.data.to_json(file_path, **kwargs)
            elif fmt == "feather":
                self.data.to_feather(file_path, **kwargs)

            logger.info("Saved %d rows to %s", len(self.data), file_path)
            return file_path.resolve()

        except Exception as exc:
            logger.error("Failed to save %s: %s", file_path, exc)
            raise IOError(f"Failed to save file: {exc}") from exc

    def save_multiple(
        self,
        formats: Optional[List[SupportedFormat]] = None,
        compression: CompressionOption = None,
        **kwargs,
    ) -> List[Path]:
        """
        Save the DataFrame in multiple formats in one call.

        Parameters
        ----------
        formats : list of str, optional
            Formats to write. Defaults to ``['csv']``.
        compression : str or None
            Compression applied to every format that supports it.
        **kwargs
            Forwarded to each underlying pandas writer.

        Returns
        -------
        list of Path
            Paths of all saved files, in the same order as *formats*.
        """
        if formats is None:
            formats = ["csv"]
        return [self.save(fmt, compression, **kwargs) for fmt in formats]

    def get_file_size(self, fmt: SupportedFormat = "csv") -> int:
        """
        Return the size in bytes of a previously saved file, or 0 if absent.

        Parameters
        ----------
        fmt : str
            Format whose file to measure.
        """
        self._validate_format(fmt)
        return self._build_path(fmt).stat().st_size if self._build_path(fmt).exists() else 0

    # ------------------------------------------------------------------
    # Class method — round-trip loading
    # ------------------------------------------------------------------

    @classmethod
    def from_file(
        cls,
        file_path: Union[str, Path],
        fmt: Optional[str] = None,
        **kwargs,
    ) -> "Store":
        """
        Create a Store instance by loading data from an existing file.

        The format is inferred from the file extension when *fmt* is not
        supplied. ``xlsx`` and ``xls`` are treated as ``'excel'``.

        Parameters
        ----------
        file_path : str or Path
            Path to the file to load.
        fmt : str, optional
            Explicit format override.
        **kwargs
            Forwarded to the underlying pandas reader.

        Returns
        -------
        Store
            New Store instance wrapping the loaded DataFrame.

        Raises
        ------
        ValueError
            If the format cannot be inferred or is not supported.
        """
        file_path = Path(file_path)

        if fmt is None:
            ext = file_path.suffix.lstrip(".").lower()
            fmt = "excel" if ext in {"xlsx", "xls"} else ext

        if fmt not in _FORMATS:
            raise ValueError(
                f"Cannot infer a supported format from extension "
                f"{file_path.suffix!r}. Pass fmt= explicitly."
            )

        readers = {
            "csv":     pd.read_csv,
            "excel":   pd.read_excel,
            "parquet": pd.read_parquet,
            "json":    pd.read_json,
            "feather": pd.read_feather,
        }

        try:
            data = readers[fmt](file_path, **kwargs)
            logger.info("Loaded %d rows from %s", len(data), file_path)
            return cls(data=data, name=file_path.stem, path=file_path.parent)
        except Exception as exc:
            logger.error("Failed to load %s: %s", file_path, exc)
            raise

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Store(shape={self.data.shape}, "
            f"name={self.name!r}, "
            f"path={str(self.path)!r})"
        )

    def __len__(self) -> int:
        return len(self.data)
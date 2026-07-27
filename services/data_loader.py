from __future__ import annotations

import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Tuple

import pandas as pd
import streamlit as st
from sqlalchemy import text

from services.database import get_engine


# ============================================================
# CONFIGURATION
# ============================================================

# Persistent cache folder.
# The folder survives Streamlit reruns and application restarts.
PARQUET_CACHE_DIR = Path("data_cache/revenue")
PARQUET_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Data refreshes once every morning, so a longer memory cache is suitable.
# 21,600 seconds = 6 hours.
STREAMLIT_CACHE_TTL = 21_600

# Prevent two requests from writing the same Parquet file simultaneously.
_FILE_LOCK = threading.Lock()


# ============================================================
# COMMON SQL QUERIES
# ============================================================

REVENUE_DATA_QUERY = text("""
    EXEC dbo.GetRevenueDataFromCache
        @StartDate = :start_date,
        @EndDate   = :end_date,
        @ViewType  = :view_type
""")


REVENUE_CACHE_VERSION_QUERY = text("""
    SELECT
        MAX(LoadedAt) AS CacheVersion
    FROM dbo.RevenueDataCache
""")


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _normalise_view_type(view_type: str) -> str:
    """
    Convert the supplied view type into the value expected by SQL Server.

    Examples:
        origin      -> ORIGIN
        Destination -> DESTINATION
    """
    value = str(view_type or "origin").strip().upper()

    if value not in {"ORIGIN", "DESTINATION"}:
        raise ValueError(
            "view_type must be either 'origin' or 'destination'."
        )

    return value


def _safe_filename_part(value: object) -> str:
    """
    Convert a value into a safe filename component.
    """
    text_value = str(value).strip()
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text_value)


def _normalise_cache_version(cache_version: object) -> str:
    """
    Convert SQL LoadedAt into a stable string suitable for filenames
    and Streamlit cache keys.
    """
    if cache_version is None or pd.isna(cache_version):
        return "unknown"

    timestamp = pd.Timestamp(cache_version)

    return timestamp.strftime("%Y%m%d_%H%M%S_%f")


def _get_parquet_path(
    start_date: str,
    end_date: str,
    view_type: str,
    cache_version: object,
) -> Path:
    """
    Build a unique Parquet filename.

    Because cache_version is part of the filename, a new SQL refresh
    automatically creates a new Parquet file.
    """
    normalised_view = _normalise_view_type(view_type)
    version_text = _normalise_cache_version(cache_version)

    start_text = _safe_filename_part(start_date)
    end_text = _safe_filename_part(end_date)

    filename = (
        f"revenue_"
        f"{normalised_view}_"
        f"{start_text}_"
        f"{end_text}_"
        f"{version_text}.parquet"
    )

    return PARQUET_CACHE_DIR / filename


def _optimise_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reduce memory usage after loading SQL data.

    This does not change calculations or business logic.
    Only low-cardinality text fields are converted to category.
    """
    if df is None or df.empty:
        return df

    category_columns = [
        "COMPNAME",
        "zone",
        "circle",
        "branch",
        "isagency",
        "GRTYPE",
        "LOADTYPE",
        "COUNTRY",
        "ShipmentStatus",
        "SLAStatus",
        "ViewType",
    ]

    for column in category_columns:
        if column in df.columns:
            try:
                df[column] = df[column].astype("category")
            except (TypeError, ValueError):
                # Preserve the original column when category conversion fails.
                pass

    return df


# ============================================================
# SQL CACHE VERSION
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_revenue_cache_version():
    """
    Return the latest SQL refresh timestamp.

    Cached for five minutes because this query is used only to determine
    whether the persistent Parquet files are still current.
    """
    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(REVENUE_CACHE_VERSION_QUERY).scalar()

    return result


# ============================================================
# DIRECT SQL FETCH
# ============================================================

def _fetch_from_sql(
    start_date: str,
    end_date: str,
    view_type: str,
) -> pd.DataFrame:
    """
    Fetch one period directly from SQL Server.

    This is the expensive operation. It runs only when the corresponding
    Parquet cache file does not already exist.
    """
    normalised_view = _normalise_view_type(view_type)
    engine = get_engine()

    with engine.connect() as conn:
        df = pd.read_sql_query(
            REVENUE_DATA_QUERY,
            conn,
            params={
                "start_date": start_date,
                "end_date": end_date,
                "view_type": normalised_view,
            },
        )

    return _optimise_dataframe(df)


# ============================================================
# PARQUET PERSISTENT CACHE
# ============================================================

def _load_or_create_parquet(
    start_date: str,
    end_date: str,
    view_type: str,
    cache_version: object,
) -> pd.DataFrame:
    """
    Load data from a persistent Parquet file.

    When no current file exists:
        1. Fetch data from SQL Server.
        2. Write the result to a temporary Parquet file.
        3. Atomically rename the temporary file.
        4. Return the DataFrame.

    The SQL business logic and Python calculations remain unchanged.
    """
    parquet_path = _get_parquet_path(
        start_date=start_date,
        end_date=end_date,
        view_type=view_type,
        cache_version=cache_version,
    )

    # Fast path: persistent file already exists.
    if parquet_path.exists():
        return pd.read_parquet(parquet_path)

    # Lock only the file creation section.
    # Other already-created files remain readable.
    with _FILE_LOCK:

        # Another request may have created it while this request was waiting.
        if parquet_path.exists():
            return pd.read_parquet(parquet_path)

        df = _fetch_from_sql(
            start_date=start_date,
            end_date=end_date,
            view_type=view_type,
        )

        temporary_path = parquet_path.with_suffix(
            f".{os.getpid()}.tmp.parquet"
        )

        try:
            df.to_parquet(
                temporary_path,
                index=False,
                engine="pyarrow",
                compression="snappy",
            )

            # Atomic replacement avoids partially written cache files.
            os.replace(temporary_path, parquet_path)

        finally:
            if temporary_path.exists():
                temporary_path.unlink(missing_ok=True)

        return df


# ============================================================
# SINGLE-PERIOD LOADER
# ============================================================

@st.cache_data(
    ttl=STREAMLIT_CACHE_TTL,
    show_spinner=False,
    max_entries=20,
)
def load_booking_data(
    start_date: str,
    end_date: str,
    view_type: str = "origin",
    cache_version: object = None,
) -> pd.DataFrame:
    """
    Load one financial period.

    Cache sequence:
        Streamlit memory cache
            -> persistent Parquet cache
                -> SQL Server only when required

    cache_version should normally be MAX(LoadedAt) from RevenueDataCache.
    """
    if cache_version is None:
        cache_version = get_revenue_cache_version()

    return _load_or_create_parquet(
        start_date=start_date,
        end_date=end_date,
        view_type=view_type,
        cache_version=cache_version,
    )


# ============================================================
# CURRENT FY + PREVIOUS FY LOADER
# ============================================================

@st.cache_data(
    ttl=STREAMLIT_CACHE_TTL,
    show_spinner=False,
    max_entries=12,
)
def load_booking_data_pair(
    start_date: str,
    end_date: str,
    prev_start: str,
    prev_end: str,
    view_type: str = "origin",
    cache_version: object = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load current FY and previous FY in parallel.

    On the first request after the daily SQL refresh:
        - both periods are fetched simultaneously;
        - each result is saved as Parquet.

    On later requests or after a Streamlit restart:
        - both periods are read from Parquet;
        - SQL Server is not called again.

    All filtering and aggregation can continue in Python exactly as before.
    """
    if cache_version is None:
        cache_version = get_revenue_cache_version()

    normalised_view = _normalise_view_type(view_type)

    with ThreadPoolExecutor(max_workers=2) as executor:

        current_future = executor.submit(
            _load_or_create_parquet,
            start_date,
            end_date,
            normalised_view,
            cache_version,
        )

        previous_future = executor.submit(
            _load_or_create_parquet,
            prev_start,
            prev_end,
            normalised_view,
            cache_version,
        )

        current_df = current_future.result()
        previous_df = previous_future.result()

    return current_df, previous_df


# ============================================================
# DATE RANGE FUNCTION
# ============================================================

def get_date_range(fin_year: str) -> Tuple[str, str]:
    """
    Convert financial year text into inclusive start and end dates.

    Example:
        2025-2026
        -> 2025-04-01, 2026-03-31
    """
    try:
        start_year_text, end_year_text = fin_year.split("-")

        start_year = int(start_year_text)
        end_year = int(end_year_text)

    except (ValueError, AttributeError) as exc:
        raise ValueError(
            "Financial year must be in 'YYYY-YYYY' format."
        ) from exc

    return (
        f"{start_year}-04-01",
        f"{end_year}-03-31",
    )


# ============================================================
# OPTIONAL CACHE MAINTENANCE
# ============================================================

def clear_old_revenue_parquet_files(
    keep_latest_versions: int = 2,
) -> int:
    """
    Delete older Parquet versions so the cache folder does not grow forever.

    The function keeps the newest files according to modification time.
    It does not affect SQL Server data.

    Returns:
        Number of files deleted.
    """
    files = sorted(
        PARQUET_CACHE_DIR.glob("revenue_*.parquet"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    # Four files per cache version are normally expected:
    # current/previous FY x origin/destination.
    number_to_keep = max(keep_latest_versions, 1) * 4

    deleted_count = 0

    for file_path in files[number_to_keep:]:
        try:
            file_path.unlink()
            deleted_count += 1
        except OSError:
            pass

    return deleted_count

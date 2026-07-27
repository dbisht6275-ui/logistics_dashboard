from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Tuple

import pandas as pd
import streamlit as st
from sqlalchemy import text

from services.database import get_engine


CACHE_FOLDER = Path("data_cache/revenue")
CACHE_FOLDER.mkdir(parents=True, exist_ok=True)

MEMORY_CACHE_TTL = 24 * 60 * 60


def _normalise_view_type(view_type: str) -> str:
    value = str(view_type or "origin").strip().upper()

    if value not in {"ORIGIN", "DESTINATION"}:
        raise ValueError("View type must be ORIGIN or DESTINATION.")

    return value


def _cache_file(
    start_date,
    end_date,
    view_type,
    cache_version,
) -> Path:

    view = _normalise_view_type(view_type)

    version = (
        pd.Timestamp(cache_version).strftime("%Y%m%d_%H%M%S")
        if cache_version
        else "unknown"
    )

    return CACHE_FOLDER / (
        f"revenue_{view}_{start_date}_{end_date}_{version}.parquet"
    )


@st.cache_data(ttl=300, show_spinner=False)
def get_revenue_cache_version() -> str:
    engine = get_engine()

    query = text("""
        SELECT MAX(LoadedAt)
        FROM dbo.RevenueDataCache
    """)

    with engine.connect() as conn:
        value = conn.execute(query).scalar()

    if value is None:
        return "NO_VERSION"

    return pd.Timestamp(value).isoformat()


def _fetch_from_sql(
    start_date,
    end_date,
    view_type,
) -> pd.DataFrame:

    engine = get_engine()

    query = text("""
        EXEC dbo.GetRevenueDataFromCache
            @StartDate = :start_date,
            @EndDate   = :end_date,
            @ViewType  = :view_type
    """)

    started = time.perf_counter()

    with engine.connect() as conn:
        df = pd.read_sql_query(
            query,
            conn,
            params={
                "start_date": start_date,
                "end_date": end_date,
                "view_type": _normalise_view_type(view_type),
            },
        )

    elapsed = time.perf_counter() - started

    print(
        f"SQL revenue load: "
        f"{start_date} to {end_date}, "
        f"rows={len(df):,}, "
        f"time={elapsed:.2f} seconds"
    )

    return df


def _load_period(
    start_date,
    end_date,
    view_type,
    cache_version,
) -> pd.DataFrame:

    path = _cache_file(
        start_date,
        end_date,
        view_type,
        cache_version,
    )

    if path.exists():
        started = time.perf_counter()

        df = pd.read_parquet(path)

        print(
            f"Parquet revenue load: "
            f"{path.name}, "
            f"rows={len(df):,}, "
            f"time={time.perf_counter() - started:.2f} seconds"
        )

        return df

    df = _fetch_from_sql(
        start_date,
        end_date,
        view_type,
    )

    temporary_path = path.with_suffix(".tmp.parquet")

    df.to_parquet(
        temporary_path,
        engine="pyarrow",
        compression="snappy",
        index=False,
    )

    temporary_path.replace(path)

    return df


@st.cache_data(
    ttl=MEMORY_CACHE_TTL,
    show_spinner=False,
    max_entries=16,
)
def load_booking_data_pair(
    start_date,
    end_date,
    prev_start,
    prev_end,
    view_type="origin",
) -> Tuple[pd.DataFrame, pd.DataFrame]:

    cache_version = get_revenue_cache_version()
    view_type = _normalise_view_type(view_type)

    with ThreadPoolExecutor(max_workers=2) as executor:

        current_future = executor.submit(
            _load_period,
            start_date,
            end_date,
            view_type,
            cache_version,
        )

        previous_future = executor.submit(
            _load_period,
            prev_start,
            prev_end,
            view_type,
            cache_version,
        )

        current_df = current_future.result()
        previous_df = previous_future.result()

    return current_df, previous_df


@st.cache_data(
    ttl=MEMORY_CACHE_TTL,
    show_spinner=False,
    max_entries=16,
)
def load_booking_data(
    start_date,
    end_date,
    view_type="origin",
):

    cache_version = get_revenue_cache_version()

    return _load_period(
        start_date,
        end_date,
        view_type,
        cache_version,
    )


def get_date_range(fin_year):
    start_year = int(fin_year.split("-")[0])
    end_year = int(fin_year.split("-")[1])

    return (
        f"{start_year}-04-01",
        f"{end_year}-03-31",
    )

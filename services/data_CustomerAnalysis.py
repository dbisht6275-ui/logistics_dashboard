import time

import pandas as pd
import streamlit as st
from sqlalchemy import text

from services.database import get_engine


_CACHE_TTL_SECONDS = 24 * 60 * 60

_CUSTOMER_QUERY = text("""
    EXEC dbo.GetRevenueDataFromCache
        @StartDate = :start_date,
        @EndDate   = :end_date,
        @ViewType  = :view_type
""")


def _fetch_customer_data(start_date, end_date, view_type):
    started = time.perf_counter()
    engine = get_engine()

    with engine.connect() as conn:
        df = pd.read_sql_query(
            _CUSTOMER_QUERY,
            conn,
            params={
                "start_date": start_date,
                "end_date": end_date,
                "view_type": str(view_type).strip().upper(),
            },
        )

    print(
        f"[Customer Analysis] {start_date} -> {end_date} | "
        f"{view_type.upper()} | Rows={len(df):,} | "
        f"{time.perf_counter()-started:.2f}s"
    )

    return df


def load_booking_data(start_date, end_date, view_type="origin"):
    """Fetch one period without retaining a second raw DataFrame cache.

    Customer Analysis owns the cleaned multi-period cache. Caching the raw
    result here as well duplicated every large result in memory.
    """
    return _fetch_customer_data(start_date, end_date, view_type)


def load_booking_data_pair(
    start_date,
    end_date,
    prev_start,
    prev_end,
    view_type="origin",
):
    current_df = _fetch_customer_data(start_date, end_date, view_type)
    previous_df = _fetch_customer_data(prev_start, prev_end, view_type)

    return current_df, previous_df


def get_date_range(fin_year):
    start_year, end_year = map(int, str(fin_year).split("-"))

    return (
        f"{start_year}-04-01",
        f"{end_year}-03-31",
    )

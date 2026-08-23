import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import streamlit as st
from sqlalchemy import text

from services.database import get_engine


_CACHE_TTL_SECONDS = 24 * 60 * 60
_REVENUE_QUERY = text("""
    EXEC dbo.GetRevenueDataFromCache
        @StartDate = :start_date,
        @EndDate   = :end_date,
        @ViewType  = :view_type
""")


def _fetch_booking_data(start_date, end_date, view_type):
    started = time.perf_counter()
    engine = get_engine()

    with engine.connect() as conn:
        df = pd.read_sql_query(
            _REVENUE_QUERY,
            conn,
            params={
                "start_date": start_date,
                "end_date": end_date,
                "view_type": str(view_type).strip().upper(),
            },
        )

    print(
        f"[Revenue Loader] {start_date} to {end_date} | "
        f"view={str(view_type).upper()} | rows={len(df):,} | "
        f"seconds={time.perf_counter() - started:.2f}"
    )
    return df


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False, max_entries=2)
def load_booking_data(start_date, end_date, view_type="origin"):
    return _fetch_booking_data(start_date, end_date, view_type)


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False, max_entries=1)
def load_booking_data_pair(
    start_date,
    end_date,
    prev_start,
    prev_end,
    view_type="origin",
):
    """Load current FY and previous FY concurrently, then cache both for one day."""
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="revenue-load") as executor:
        current_future = executor.submit(
            _fetch_booking_data, start_date, end_date, view_type
        )
        previous_future = executor.submit(
            _fetch_booking_data, prev_start, prev_end, view_type
        )
        current_df = current_future.result()
        previous_df = previous_future.result()

    return current_df, previous_df


def get_date_range(fin_year):
    try:
        start_year, end_year = map(int, str(fin_year).split("-"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Financial year must be in YYYY-YYYY format") from exc

    return f"{start_year}-04-01", f"{end_year}-03-31"

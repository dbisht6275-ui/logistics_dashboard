import streamlit as st
import pandas as pd
from sqlalchemy import text
from concurrent.futures import ThreadPoolExecutor
from services.database import get_engine


@st.cache_data(ttl=1800)
def load_booking_data(start_date, end_date, view_type="origin"):

    engine = get_engine()

    query = text("""
        EXEC dbo.RevenueDataForPythonDashboard
            @StartDate=:start_date,
            @EndDate=:end_date,
            @ViewType=:view_type
    """)

    with engine.connect() as conn:
        df = pd.read_sql(
            query,
            conn,
            params={
                "start_date": start_date,
                "end_date": end_date,
                "view_type": view_type.upper()
            }
        )

    return df


@st.cache_data(ttl=1800)
def load_booking_data_pair(start_date, end_date, prev_start, prev_end, view_type="origin"):
    """
    Fetches the current-period data AND the previous-year (LY) data
    AT THE SAME TIME using two threads, instead of one after another.

    Since these are two independent DB round-trips (each opens its own
    connection from the pool), running them in parallel roughly halves
    the total wait time compared to calling load_booking_data() twice
    back-to-back.
    """

    def _fetch(s, e):
        engine = get_engine()
        query = text("""
            EXEC dbo.RevenueDataForPythonDashboard
                @StartDate=:start_date,
                @EndDate=:end_date,
                @ViewType=:view_type
        """)
        with engine.connect() as conn:
            return pd.read_sql(
                query,
                conn,
                params={
                    "start_date": s,
                    "end_date": e,
                    "view_type": view_type.upper()
                }
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        current_future = executor.submit(_fetch, start_date, end_date)
        prev_future = executor.submit(_fetch, prev_start, prev_end)

        current_df = current_future.result()
        prev_df = prev_future.result()

    return current_df, prev_df


# -------- DATE RANGE FUNCTION --------

def get_date_range(fin_year):
    start_year = int(fin_year.split("-")[0])
    end_year = int(fin_year.split("-")[1])

    return (
        f"{start_year}-04-01",
        f"{end_year}-03-31"
    )

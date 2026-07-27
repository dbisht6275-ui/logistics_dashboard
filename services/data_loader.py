import time
from typing import Tuple
import pandas as pd
import streamlit as st
from sqlalchemy import text
from services.database import get_engine

# The SQL cache table is refreshed once every morning.  A longer Streamlit
# cache is safe because the cache key also contains MAX(LoadedAt), so the
# dashboard automatically reloads when the morning refresh creates new data.
DATA_CACHE_TTL_SECONDS = 24 * 60 * 60
VERSION_CACHE_TTL_SECONDS = 300

@st.cache_data(ttl=VERSION_CACHE_TTL_SECONDS, show_spinner=False)
def get_revenue_cache_version():
    """Return the latest refresh timestamp from dbo.RevenueDataCache."""
    engine = get_engine()

    query = text("""
        SELECT MAX(LoadedAt) AS CacheVersion
        FROM dbo.RevenueDataCache
    """)

    with engine.connect() as conn:
        value = conn.execute(query).scalar()

    # Streamlit cache keys are more stable with a plain string than with a
    # driver-specific datetime object.
    if value is None:
        return "NO_VERSION"

    return pd.Timestamp(value).isoformat()


def _normalise_view_type(view_type: str) -> str:
    value = str(view_type or "origin").strip().upper()

    if value not in {"ORIGIN", "DESTINATION"}:
        raise ValueError("view_type must be ORIGIN or DESTINATION")

    return value


def _normalise_date(value) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)

    if pd.isna(timestamp):
        raise ValueError(f"Invalid date value: {value}")

    return timestamp.normalize()


@st.cache_data(ttl=DATA_CACHE_TTL_SECONDS, show_spinner=False, max_entries=12)
def _load_two_year_data(
    combined_start: str,
    combined_end: str,
    view_type: str,
    cache_version: str,
) -> pd.DataFrame:
    """
    Load current FY and previous FY in one SQL call.

    cache_version is intentionally unused inside the SQL statement.  It is part
    of the function signature so Streamlit automatically invalidates this cache
    after dbo.RevenueDataCache is refreshed at 5 AM.
    """
    del cache_version

    engine = get_engine()
    normalised_view = _normalise_view_type(view_type)

    query = text("""
        EXEC dbo.GetRevenueDataFromCache
            @StartDate = :start_date,
            @EndDate   = :end_date,
            @ViewType  = :view_type
    """)

    started_at = time.perf_counter()

    with engine.connect() as conn:
        df = pd.read_sql_query(
            query,
            conn,
            params={
                "start_date": combined_start,
                "end_date": combined_end,
                "view_type": normalised_view,
            },
        )

    elapsed = time.perf_counter() - started_at
    print(
        f"Revenue cache load completed: view={normalised_view}, "
        f"rows={len(df):,}, seconds={elapsed:.2f}"
    )

    if "grdt" not in df.columns:
        raise KeyError("The stored procedure result does not contain grdt")

    # Convert only once. The overview page repeatedly uses this column for
    # trend calculations and financial-year splitting.
    df["grdt"] = pd.to_datetime(df["grdt"], errors="coerce")

    return df


@st.cache_data(ttl=DATA_CACHE_TTL_SECONDS, show_spinner=False, max_entries=12)
def load_booking_data_pair(
    start_date,
    end_date,
    prev_start,
    prev_end,
    view_type="origin",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Return current-period and previous-period detail data.

    Important performance change:
    - Old code opened two SQL connections and executed the large stored
      procedure twice at the same time.
    - New code executes the procedure only once for the combined two-year
      range, then splits the result in memory.

    All dashboard filtering and aggregation remain in Python.
    """
    current_start_ts = _normalise_date(start_date)
    current_end_ts = _normalise_date(end_date)
    previous_start_ts = _normalise_date(prev_start)
    previous_end_ts = _normalise_date(prev_end)

    combined_start = min(current_start_ts, previous_start_ts)
    combined_end = max(current_end_ts, previous_end_ts)

    cache_version = get_revenue_cache_version()

    combined_df = _load_two_year_data(
        combined_start.strftime("%Y-%m-%d"),
        combined_end.strftime("%Y-%m-%d"),
        _normalise_view_type(view_type),
        cache_version,
    )

    # Inclusive financial-year end dates, matching the stored procedure.
    current_mask = combined_df["grdt"].between(
        current_start_ts,
        current_end_ts + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1),
    )
    previous_mask = combined_df["grdt"].between(
        previous_start_ts,
        previous_end_ts + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1),
    )

    # Copies protect the cached combined dataframe from later in-place changes
    # made by the overview page (Month, Quarter, compname standardisation, etc.).
    current_df = combined_df.loc[current_mask].copy()
    previous_df = combined_df.loc[previous_mask].copy()

    return current_df, previous_df


@st.cache_data(ttl=DATA_CACHE_TTL_SECONDS, show_spinner=False, max_entries=12)
def load_booking_data(start_date, end_date, view_type="origin"):
    """Load one period while using the same refresh-aware cache strategy."""
    cache_version = get_revenue_cache_version()

    df = _load_two_year_data(
        _normalise_date(start_date).strftime("%Y-%m-%d"),
        _normalise_date(end_date).strftime("%Y-%m-%d"),
        _normalise_view_type(view_type),
        cache_version,
    )

    return df.copy()


# -------- DATE RANGE FUNCTION --------

def get_date_range(fin_year):
    start_year = int(fin_year.split("-")[0])
    end_year = int(fin_year.split("-")[1])

    return (
        f"{start_year}-04-01",
        f"{end_year}-03-31",
    )

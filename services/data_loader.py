import streamlit as st
import pandas as pd
from sqlalchemy import text

from services.database import get_engine


def _prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply basic data-type cleanup after reading the cache table.

    This does not change dashboard calculations. It only ensures that
    date and numeric columns have consistent pandas data types.
    """

    if df.empty:
        return df

    date_columns = [
        "grdt",
        "expecteddeliverydt",
        "deliverydt",
        "lastdespdt",
        "LoadedAt",
    ]

    numeric_columns = [
        "aweight",
        "cweight",
        "FIN_MONTH",
        "REVENUE",
        "TransitDays",
        "DispatchToDeliveryDays",
        "DelayDays",
        "IsDelivered",
        "IsWithinSLA",
        "IsLate",
    ]

    for column in date_columns:
        if column in df.columns:
            df[column] = pd.to_datetime(
                df[column],
                errors="coerce",
            )

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    return df


def _get_latest_loaded_at(engine, view_type: str):
    """
    Get the latest LoadedAt timestamp for a given view_type.
    Separate function to avoid subquery in main query.
    """
    query = text("""
        SELECT MAX(LoadedAt) as LatestLoadedAt
        FROM dbo.RevenueDataCache
        WHERE ViewType = :view_type
    """)
    
    with engine.connect() as conn:
        result = pd.read_sql(query, conn, params={"view_type": view_type.strip().upper()})
    
    if result.empty or pd.isna(result['LatestLoadedAt'].iloc[0]):
        return None
    
    return result['LatestLoadedAt'].iloc[0]


@st.cache_data(ttl=1800, show_spinner=False)
def load_booking_data(
    start_date,
    end_date,
    view_type="origin",
):
    """
    Load one period of booking/revenue data from RevenueDataCache.
    
    OPTIMIZED: Pre-calculates latest LoadedAt separately to avoid
    subquery on every row. Removes string functions for index usage.
    """

    engine = get_engine()
    view_type_clean = str(view_type).strip().upper()
    
    # Get latest LoadedAt first
    latest_loaded = _get_latest_loaded_at(engine, view_type_clean)
    
    if latest_loaded is None:
        return pd.DataFrame()
    
    # Simple query with index-friendly conditions
    query = text("""
        SELECT C.*
        FROM dbo.RevenueDataCache AS C
        WHERE C.ViewType = :view_type
          AND C.grdt >= CAST(:start_date AS date)
          AND C.grdt < DATEADD(DAY, 1, CAST(:end_date AS date))
          AND C.LoadedAt = :latest_dt
    """)

    params = {
        "view_type": view_type_clean,
        "start_date": start_date,
        "end_date": end_date,
        "latest_dt": latest_loaded,
    }

    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params=params)

    return _prepare_dataframe(df)


@st.cache_data(ttl=1800, show_spinner=False)
def load_booking_data_pair(
    start_date,
    end_date,
    prev_start,
    prev_end,
    view_type="origin",
):
    """
    Load current-period and previous-period data in one database query.

    OPTIMIZED: Pre-calculates latest LoadedAt separately to avoid
    subquery. Removes string functions for index usage.

    Returns:
        current_df, prev_df
    """

    engine = get_engine()
    view_type_clean = str(view_type).strip().upper()
    
    # Get latest LoadedAt first
    latest_loaded = _get_latest_loaded_at(engine, view_type_clean)
    
    if latest_loaded is None:
        empty_df = pd.DataFrame()
        return empty_df, empty_df

    query = text("""
        SELECT
            C.*,
            CASE
                WHEN C.grdt >= CAST(:start_date AS date)
                 AND C.grdt < DATEADD(DAY, 1, CAST(:end_date AS date))
                THEN 'CURRENT'

                WHEN C.grdt >= CAST(:prev_start AS date)
                 AND C.grdt < DATEADD(DAY, 1, CAST(:prev_end AS date))
                THEN 'PREVIOUS'
            END AS __PERIOD
        FROM dbo.RevenueDataCache AS C
        WHERE C.ViewType = :view_type
          AND (
                (
                    C.grdt >= CAST(:start_date AS date)
                    AND C.grdt < DATEADD(DAY, 1, CAST(:end_date AS date))
                )
                OR
                (
                    C.grdt >= CAST(:prev_start AS date)
                    AND C.grdt < DATEADD(DAY, 1, CAST(:prev_end AS date))
                )
              )
          AND C.LoadedAt = :latest_dt
    """)

    params = {
        "start_date": start_date,
        "end_date": end_date,
        "prev_start": prev_start,
        "prev_end": prev_end,
        "view_type": view_type_clean,
        "latest_dt": latest_loaded,
    }

    with engine.connect() as conn:
        combined_df = pd.read_sql(query, conn, params=params)

    combined_df = _prepare_dataframe(combined_df)

    if combined_df.empty:
        empty_df = combined_df.drop(
            columns=["__PERIOD"],
            errors="ignore",
        )

        return empty_df.copy(), empty_df.copy()

    current_df = (
        combined_df.loc[
            combined_df["__PERIOD"] == "CURRENT"
        ]
        .drop(
            columns=["__PERIOD"],
            errors="ignore",
        )
        .reset_index(drop=True)
    )

    prev_df = (
        combined_df.loc[
            combined_df["__PERIOD"] == "PREVIOUS"
        ]
        .drop(
            columns=["__PERIOD"],
            errors="ignore",
        )
        .reset_index(drop=True)
    )

    return current_df, prev_df


# -------- DATE RANGE FUNCTION --------

def get_date_range(fin_year):
    """
    Convert a financial year such as 2025-2026 into:

        2025-04-01
        2026-03-31
    """

    start_year = int(fin_year.split("-")[0])
    end_year = int(fin_year.split("-")[1])

    return (
        f"{start_year}-04-01",
        f"{end_year}-03-31",
    )

import streamlit as st
import pandas as pd
from sqlalchemy import text

from services.database import get_engine


def _prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply basic data-type cleanup after reading the cache table.
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
            df[column] = pd.to_datetime(df[column], errors="coerce")

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    return df


@st.cache_data(ttl=1800, show_spinner=False)
def load_booking_data(
    start_date,
    end_date,
    view_type="origin",
):
    """
    Load booking/revenue data from RevenueDataCache.
    
    SUPER OPTIMIZED:
    - No LoadedAt filtering (table already has latest data from 5 AM scheduler)
    - Simple ViewType + date range query
    - Index uses SEEK not SCAN
    """

    engine = get_engine()
    view_type_clean = str(view_type).strip().upper()

    # Simplest possible query
    query = text("""
        SELECT C.*
        FROM dbo.RevenueDataCache AS C
        WHERE C.ViewType = :view_type
          AND C.grdt >= CAST(:start_date AS date)
          AND C.grdt < DATEADD(DAY, 1, CAST(:end_date AS date))
    """)

    params = {
        "view_type": view_type_clean,
        "start_date": start_date,
        "end_date": end_date,
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
    Load current-period and previous-period data in one query.
    
    SUPER OPTIMIZED:
    - No LoadedAt filtering
    - Period separation with CASE
    """

    engine = get_engine()
    view_type_clean = str(view_type).strip().upper()

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
    """)

    params = {
        "start_date": start_date,
        "end_date": end_date,
        "prev_start": prev_start,
        "prev_end": prev_end,
        "view_type": view_type_clean,
    }

    with engine.connect() as conn:
        combined_df = pd.read_sql(query, conn, params=params)

    combined_df = _prepare_dataframe(combined_df)

    if combined_df.empty:
        empty_df = combined_df.drop(columns=["__PERIOD"], errors="ignore")
        return empty_df.copy(), empty_df.copy()

    current_df = (
        combined_df.loc[combined_df["__PERIOD"] == "CURRENT"]
        .drop(columns=["__PERIOD"], errors="ignore")
        .reset_index(drop=True)
    )

    prev_df = (
        combined_df.loc[combined_df["__PERIOD"] == "PREVIOUS"]
        .drop(columns=["__PERIOD"], errors="ignore")
        .reset_index(drop=True)
    )

    return current_df, prev_df


# -------- DATE RANGE FUNCTION --------

def get_date_range(fin_year):
    """
    Convert a financial year such as 2025-2026 into date range
    """
    start_year = int(fin_year.split("-")[0])
    end_year = int(fin_year.split("-")[1])

    return (
        f"{start_year}-04-01",
        f"{end_year}-03-31",
    )

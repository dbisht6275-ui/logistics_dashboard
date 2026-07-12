"""
services/data_outstanding.py
============================

Data layer for the Outstanding Analysis page.

Uses the common database connection from:

    services/database.py

The page can import:

    from services.data_outstanding import (
        get_outstanding_data,
        clean_data,
        DEFAULT_PARAMS,
        get_date_range,
    )
"""

from datetime import date

import pandas as pd
import streamlit as st
from sqlalchemy import text

from services.database import get_engine


# --------------------------------------------------------------------------
# OUTSTANDING DATA
# --------------------------------------------------------------------------

@st.cache_data(
    ttl=1800,
    show_spinner="Fetching outstanding data..."
)
def get_outstanding_data(
    branch,
    grtype,
    from_dt,
    to_dt,
    as_on_dt,
    custcode,
    invoiceno,
    user,
):
    """
    Fetch outstanding data from the Alloutstanding_BI stored procedure.

    Example:

        EXEC dbo.Alloutstanding_BI
            '00000',
            'C',
            '2025-04-01',
            '2026-03-31',
            '2026-03-31',
            '0000',
            '',
            'SYST'
    """

    engine = get_engine()

    query = text("""
        EXEC dbo.Alloutstanding_BI
            @Branch=:branch,
            @Type=:grtype,
            @FromDate=:from_dt,
            @ToDate=:to_dt,
            @AsOnDate=:as_on_dt,
            @CustCode=:custcode,
            @InvoiceNo=:invoiceno,
            @User=:user
    """)

    params = {
        "branch": branch,
        "grtype": grtype,
        "from_dt": _format_date(from_dt),
        "to_dt": _format_date(to_dt),
        "as_on_dt": _format_date(as_on_dt),
        "custcode": custcode,
        "invoiceno": invoiceno,
        "user": user,
    }

    with engine.connect() as conn:
        df = pd.read_sql(
            query,
            conn,
            params=params,
        )

    return clean_data(df)


# --------------------------------------------------------------------------
# DATE HELPERS
# --------------------------------------------------------------------------

def _format_date(value):
    """
    Convert date, datetime or string values into YYYY-MM-DD format.
    """

    if value is None:
        return None

    if isinstance(value, str):
        return value

    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")

    return str(value)


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


# --------------------------------------------------------------------------
# CLEANING AND DERIVED COLUMNS
# --------------------------------------------------------------------------

def age_bucket(days):
    """
    Convert outstanding days into ageing buckets.
    """

    try:
        days = float(days)
    except (TypeError, ValueError):
        days = 0

    if days <= 30:
        return "0-30"

    if days <= 60:
        return "31-60"

    if days <= 90:
        return "61-90"

    return "Above 90"


def clean_data(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names, fix data types and add age_bucket.
    """

    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()

    # Normalize column names
    df.columns = [
        str(column).strip().lower()
        for column in df.columns
    ]

    # Clean text columns
    text_columns = [
        "zonename",
        "branchname",
        "custname",
        "custcode",
        "grtype",
        "documenttype",
        "invoiceno",
    ]

    for column in text_columns:
        if column in df.columns:
            df[column] = (
                df[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

    # Convert date columns
    date_columns = [
        "asondt",
        "invoicedt",
        "submissiondt",
        "duedt",
    ]

    for column in date_columns:
        if column in df.columns:
            df[column] = pd.to_datetime(
                df[column],
                errors="coerce",
            )

    # Convert numeric columns
    numeric_columns = [
        "billamount",
        "recdamount",
        "balance",
        "onaccrecd",
        "netbalance",
        "outstandingdays",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            ).fillna(0)

    # Create ageing bucket
    if "outstandingdays" in df.columns:
        df["age_bucket"] = (
            df["outstandingdays"]
            .apply(age_bucket)
        )
    else:
        df["age_bucket"] = "0-30"

    return df


# --------------------------------------------------------------------------
# DEFAULT REPORT PARAMETERS
# --------------------------------------------------------------------------

DEFAULT_PARAMS = {
    "branch": "00000",
    "grtype": "C",
    "from_dt": date(2025, 4, 1),
    "to_dt": date(2026, 3, 31),
    "as_on_dt": date(2026, 3, 31),
    "custcode": "0000",
    "invoiceno": "",
    "user": "SYST",
}
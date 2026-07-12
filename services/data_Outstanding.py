"""
services/data_outstanding.py
=============================
Data layer for the "Outstanding Analysis" page.
Connects to SQL Server and calls the `Alloutstanding_BI` stored procedure.

Import from the page file:

    from services.data_outstanding import get_engine, get_outstanding_data, clean_data, DEFAULT_PARAMS

"""

from datetime import date

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# --------------------------------------------------------------------------
# ENGINE
# --------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_engine(server: str, database: str, username: str, password: str,
                driver: str = "ODBC Driver 17 for SQL Server"):
    """
    Build a SQLAlchemy engine using URL.create so that special characters
    in the username/password (@, #, %, etc.) don't break the connection
    string.
    """
    conn_url = URL.create(
        "mssql+pyodbc",
        username=username,
        password=password,
        host=server,
        database=database,
        query={"driver": driver, "TrustServerCertificate": "yes"},
    )
    return create_engine(conn_url, pool_pre_ping=True, fast_executemany=True)


# --------------------------------------------------------------------------
# SP CALL: Alloutstanding_BI
# --------------------------------------------------------------------------
@st.cache_data(show_spinner="Fetching data from Alloutstanding_BI ...", ttl=600)
def get_outstanding_data(_engine, branch, grtype, from_dt, to_dt, as_on_dt,
                          custcode, invoiceno, user):
    """
    Calls:
        EXEC Alloutstanding_BI @Branch, @Type, @FromDate, @ToDate,
                                @AsOnDate, @CustCode, @InvoiceNo, @User

    Example (matches what you ran manually):
        EXEC Alloutstanding_BI '00000','C','2025-04-01','2026-03-31',
                                '2026-03-31','0000','','SYST'

    NOTE: rename p1..p8 below to the real @parameter names declared in the
    stored procedure if they differ from this placeholder order.
    """
    query = text(
        """
        EXEC Alloutstanding_BI
            :p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8
        """
    )
    params = {
        "p1": branch,
        "p2": grtype,
        "p3": from_dt,
        "p4": to_dt,
        "p5": as_on_dt,
        "p6": custcode,
        "p7": invoiceno,
        "p8": user,
    }
    with _engine.connect() as conn:
        df = pd.read_sql(query, conn, params=params)
    return clean_data(df)


# --------------------------------------------------------------------------
# CLEANING / DERIVED COLUMNS
# --------------------------------------------------------------------------
def age_bucket(days):
    if days <= 30:
        return "0-30"
    elif days <= 60:
        return "31-60"
    elif days <= 90:
        return "61-90"
    else:
        return "Above 90"


def clean_data(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes column names, fixes dtypes, and adds an `age_bucket` column
    derived from `outstandingdays`.
    """
    df = df_raw.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    date_cols = [c for c in ["asondt", "invoicedt", "submissiondt", "duedt"] if c in df.columns]
    for c in date_cols:
        df[c] = pd.to_datetime(df[c], errors="coerce")

    num_cols = [
        c for c in ["billamount", "recdamount", "balance", "onaccrecd", "netbalance", "outstandingdays"]
        if c in df.columns
    ]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    if "outstandingdays" in df.columns:
        df["age_bucket"] = df["outstandingdays"].apply(age_bucket)

    return df


def load_from_excel(uploaded_file) -> pd.DataFrame:
    """Load the same report structure from a manually exported Excel file."""
    return clean_data(pd.read_excel(uploaded_file))


# --------------------------------------------------------------------------
# DEFAULT SP PARAMETERS (used to pre-fill the page's parameter form)
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
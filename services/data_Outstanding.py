from datetime import date
import pandas as pd
import streamlit as st
from sqlalchemy import text
from services.database import get_engine

@st.cache_data(ttl=3600, show_spinner="Fetching outstanding data...")
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
    """Run dbo.Alloutstanding_BI using the shared database engine."""

    engine = get_engine()

    query = text("""
        EXEC dbo.Alloutstanding_BI
            :branch,
            :grtype,
            :from_dt,
            :to_dt,
            :as_on_dt,
            :custcode,
            :invoiceno,
            :user
    """)

    params = {
        "branch": str(branch).strip(),
        "grtype": str(grtype).strip(),
        "from_dt": _format_date(from_dt),
        "to_dt": _format_date(to_dt),
        "as_on_dt": _format_date(as_on_dt),
        "custcode": str(custcode).strip(),
        "invoiceno": str(invoiceno).strip(),
        "user": str(user).strip(),
    }

    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params=params)

    return clean_data(df)


def _format_date(value):
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def age_bucket(days):
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
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    date_cols = [
        c for c in ["asondt", "invoicedt", "submissiondt", "duedt"]
        if c in df.columns
    ]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    num_cols = [
        c for c in [
            "billamount", "recdamount", "balance", "onaccrecd",
            "netbalance", "outstandingdays"
        ]
        if c in df.columns
    ]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    text_cols = [
        c for c in [
            "zonename", "branchname", "custname", "custcode",
            "grtype", "documenttype", "invoiceno"
        ]
        if c in df.columns
    ]
    for col in text_cols:
        df[col] = df[col].fillna("").astype(str).str.strip()

    if "outstandingdays" in df.columns:
        df["age_bucket"] = df["outstandingdays"].apply(age_bucket)
    else:
        df["age_bucket"] = "0-30"

    return df


def get_date_range(fin_year):
    start_year = int(fin_year.split("-")[0])
    end_year = int(fin_year.split("-")[1])
    return f"{start_year}-04-01", f"{end_year}-03-31"


DEFAULT_PARAMS = {
    "branch": "00000",
    "grtype": "C",
    "from_dt": date(1980, 1, 1),
    "to_dt": date(2026, 3, 31),
    "as_on_dt": date(2026, 3, 31),
    "custcode": "0000",
    "invoiceno": "",
    "user": "SYST",
}

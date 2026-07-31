import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import streamlit as st
from sqlalchemy import text
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from services.database import get_engine


# =========================
# CONFIG
# =========================
_CACHE_TTL_SECONDS = 24 * 60 * 60

_CUSTOMER_QUERY = text("""
    EXEC dbo.GetRevenueDataFromCache
        @StartDate = :start_date,
        @EndDate   = :end_date,
        @ViewType  = :view_type
""")


# =========================
# HELPERS
# =========================
def _normalize_view_type(view_type: str) -> str:
    vt = str(view_type).strip().upper()
    return "ORIGIN" if vt == "ORIGIN" else "DESTINATION"


def _find_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c

    normalized = {
        str(col).replace("_", "").replace(" ", "").lower(): col
        for col in df.columns
    }

    for c in candidates:
        key = c.replace("_", "").replace(" ", "").lower()
        if key in normalized:
            return normalized[key]

    return None


# =========================
# CORE FETCH (SP BASED)
# =========================
@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(5),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _fetch_customer_data(start_date, end_date, view_type):

    started = time.perf_counter()
    engine = get_engine()

    view_type = _normalize_view_type(view_type)

    with engine.connect() as conn:
        df = pd.read_sql_query(
            _CUSTOMER_QUERY,
            conn,
            params={
                "start_date": start_date,
                "end_date": end_date,
                "view_type": view_type,
            },
        )

    print(
        f"[Customer Loader] {start_date} → {end_date} | "
        f"{view_type} | rows={len(df)} | "
        f"time={time.perf_counter() - started:.2f}s"
    )

    return _build_customer_summary(df, view_type)


# =========================
# TRANSFORM (IMPORTANT)
# =========================
def _build_customer_summary(df, view_type):

    if df is None or df.empty:
        return pd.DataFrame()

    # ---- column mapping ----
    zone_col = _find_col(df, ["zone"])
    circle_col = _find_col(df, ["circle"])
    branch_col = _find_col(df, ["branch"])
    load_col = _find_col(df, ["loadtype"])
    revenue_col = _find_col(df, ["revenue"])
    grno_col = _find_col(df, ["grno"])
    awt_col = _find_col(df, ["aweight"])
    cwt_col = _find_col(df, ["cweight"])
    exp_col = _find_col(df, ["expecteddeliverydt"])
    del_col = _find_col(df, ["deliverydt"])
    date_col = _find_col(df, ["grdt"])

    if view_type == "ORIGIN":
        code_col = _find_col(df, ["cngrcode"])
        name_col = _find_col(df, ["consignor", "customer"])
        code_name = "cngrcode"
        name_name = "Consignor"
    else:
        code_col = _find_col(df, ["cngecode"])
        name_col = _find_col(df, ["consignee", "receiver"])
        code_name = "ConsigneeCode"
        name_name = "Consignee"

    # ---- working df ----
    work = pd.DataFrame()

    work["Zone"] = df[zone_col]
    work["Circle"] = df[circle_col]
    work["Branch"] = df[branch_col]
    work["LoadType"] = df[load_col]
    work["Revenue"] = pd.to_numeric(df[revenue_col], errors="coerce").fillna(0)

    work["ActualWeight"] = pd.to_numeric(df[awt_col], errors="coerce").fillna(0)
    work["ChargeWeight"] = pd.to_numeric(df[cwt_col], errors="coerce").fillna(0)

    work[code_name] = df[code_col]
    work[name_name] = df[name_col].fillna("Unknown")

    # ---- shipment count ----
    work["_cnt"] = 1

    # ---- financial year + month ----
    grdt = pd.to_datetime(df[date_col], errors="coerce")
    work["YR"] = grdt.dt.year.where(grdt.dt.month >= 4, grdt.dt.year - 1)
    work["FIN_MONTH"] = ((grdt.dt.month - 4) % 12) + 1

    # ---- delay ----
    exp = pd.to_datetime(df[exp_col], errors="coerce")
    dlv = pd.to_datetime(df[del_col], errors="coerce")
    work["_delay"] = (dlv - exp).dt.days

    # ---- GROUP BY ----
    group_cols = [
        "YR", "FIN_MONTH",
        "Zone", "Circle", "Branch",
        code_name, name_name,
        "LoadType"
    ]

    result = (
        work.groupby(group_cols, dropna=False)
        .agg(
            ShipmentCount=("_cnt", "sum"),
            ActualWeight=("ActualWeight", "sum"),
            ChargeWeight=("ChargeWeight", "sum"),
            Revenue=("Revenue", "sum"),
            AvgDelayDays=("_delay", "mean"),
            MaxDelayDays=("_delay", "max"),
        )
        .reset_index()
    )

    return result


# =========================
# PUBLIC FUNCTIONS (SAME NAME)
# =========================
@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False, max_entries=20)
def load_booking_data(start_date, end_date, view_type="origin"):
    return _fetch_customer_data(start_date, end_date, view_type)


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False, max_entries=12)
def load_booking_data_pair(
    start_date,
    end_date,
    prev_start,
    prev_end,
    view_type="origin",
):
    with ThreadPoolExecutor(max_workers=2) as executor:
        cur_future = executor.submit(_fetch_customer_data, start_date, end_date, view_type)
        prev_future = executor.submit(_fetch_customer_data, prev_start, prev_end, view_type)

        return cur_future.result(), prev_future.result()


# =========================
# DATE RANGE
# =========================
def get_date_range(fin_year):
    start_year, end_year = map(int, str(fin_year).split("-"))
    return f"{start_year}-04-01", f"{end_year}-03-31"

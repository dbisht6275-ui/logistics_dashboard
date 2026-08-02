import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import streamlit as st
from sqlalchemy import text

from services.database import get_engine
from services.data_loader import load_booking_data


_CACHE_TTL_SECONDS = 24 * 60 * 60

_PNL_QUERY = text("""
    EXEC dbo.GREENTRANSWEB_GRWISEPNLDETAIL_PYTHONDASHBOARD
        @prmbranchcode = :branch_code,
        @prmfromdt     = :from_date,
        @prmtodt       = :to_date,
        @prmgrno       = :grno
""")


def _normalise_column_name(value):
    return str(value).strip().replace("_", "").replace(" ", "").casefold()


def _find_column(df, candidates):
    column_map = {_normalise_column_name(col): col for col in df.columns}
    for candidate in candidates:
        found = column_map.get(_normalise_column_name(candidate))
        if found is not None:
            return found
    return None


def _clean_grno(series):
    return series.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)


def _fetch_pnl_sp_data(start_date, end_date):
    started = time.perf_counter()
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql_query(
            _PNL_QUERY,
            conn,
            params={
                "branch_code": "00000",
                "from_date": str(start_date),
                "to_date": str(end_date),
                "grno": "",
            },
        )
    print(
        f"[P&L SP Loader] {start_date} to {end_date} | rows={len(df):,} | "
        f"seconds={time.perf_counter() - started:.2f}"
    )
    return df


def _prepare_revenue_data(df):
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    gr_col = _find_column(out, ["GRNO", "grno", "gr_no", "grnumber"])
    revenue_col = _find_column(out, ["REVENUE", "revenue", "freight"])
    if gr_col is None or revenue_col is None:
        raise ValueError(f"Revenue data requires GRNO and REVENUE. Available: {list(out.columns)}")
    out = out.rename(columns={gr_col: "grno", revenue_col: "REVENUE"})
    out["grno"] = _clean_grno(out["grno"])
    out["REVENUE"] = pd.to_numeric(out["REVENUE"], errors="coerce").fillna(0.0)
    return out


def _prepare_pnl_sp_data(df):
    aliases = {
        "GRNO": ["GRNO", "grno", "gr_no", "grnumber"],
        "DELIVERYINCOME": ["DELIVERYINCOME", "delivery_income"],
        "OTHERCHARGES": ["OTHERCHARGES", "other_charges"],
        "ADDITIONALFREIGHT": ["ADDITIONALFREIGHT", "additional_freight"],
        "OTHERINCOME": ["OTHERINCOME", "other_income"],
        "RAW_EXPENSE": ["EXPENSE", "expense", "raw_expense"],
    }
    if df is None or df.empty:
        return pd.DataFrame(columns=["grno", "DELIVERYINCOME", "OTHERCHARGES", "ADDITIONALFREIGHT", "OTHERINCOME", "RAW_EXPENSE"])
    out = df.copy()
    rename_map = {}
    for target, candidates in aliases.items():
        source = _find_column(out, candidates)
        if source is None:
            if target == "OTHERCHARGES":
                out[target] = 0.0
                continue
            raise ValueError(f"P&L SP did not return {target}. Available: {list(out.columns)}")
        rename_map[source] = target
    out = out.rename(columns=rename_map).rename(columns={"GRNO": "grno"})
    out["grno"] = _clean_grno(out["grno"])
    numeric = ["DELIVERYINCOME", "OTHERCHARGES", "ADDITIONALFREIGHT", "OTHERINCOME", "RAW_EXPENSE"]
    for col in numeric:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
    return out.groupby("grno", as_index=False, dropna=False)[numeric].sum()


def _merge_revenue_and_pnl(revenue_df, pnl_sp_df):
    revenue = _prepare_revenue_data(revenue_df)
    pnl_data = _prepare_pnl_sp_data(pnl_sp_df)
    if revenue.empty:
        return revenue
    revenue = revenue.drop(columns=[c for c in ["EXPENSE", "PNL", "RAW_EXPENSE", "DELIVERYINCOME", "OTHERCHARGES", "ADDITIONALFREIGHT", "OTHERINCOME"] if c in revenue.columns], errors="ignore")
    result = revenue.merge(pnl_data, on="grno", how="left", validate="many_to_one")
    for col in ["DELIVERYINCOME", "OTHERCHARGES", "ADDITIONALFREIGHT", "OTHERINCOME", "RAW_EXPENSE"]:
        result[col] = pd.to_numeric(result[col], errors="coerce").fillna(0.0)
    result["EXPENSE"] = result["RAW_EXPENSE"] - (result["ADDITIONALFREIGHT"] + result["DELIVERYINCOME"] + result["OTHERINCOME"])
    result["PNL"] = result["REVENUE"] + result["DELIVERYINCOME"] + result["ADDITIONALFREIGHT"] + result["OTHERINCOME"] - result["RAW_EXPENSE"]
    return result


def _fetch_complete_period(start_date, end_date, view_type):
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="pnl-period") as executor:
        revenue_future = executor.submit(load_booking_data, start_date, end_date, view_type)
        pnl_future = executor.submit(_fetch_pnl_sp_data, start_date, end_date)
        revenue_df = revenue_future.result()
        pnl_sp_df = pnl_future.result()
    return _merge_revenue_and_pnl(revenue_df, pnl_sp_df)


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False, max_entries=12)
def load_pnl_data(start_date, end_date, view_type="origin"):
    return _fetch_complete_period(start_date, end_date, view_type)


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False, max_entries=8)
def load_pnl_data_pair(start_date, end_date, prev_start, prev_end, view_type="origin"):
    """Load current FY and previous FY P&L concurrently."""
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="pnl-pair") as executor:
        current_future = executor.submit(_fetch_complete_period, start_date, end_date, view_type)
        previous_future = executor.submit(_fetch_complete_period, prev_start, prev_end, view_type)
        return current_future.result(), previous_future.result()

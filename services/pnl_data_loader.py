import time

import pandas as pd
import streamlit as st
from sqlalchemy import text

from services.database import get_engine
from services.data_loader import load_booking_data, get_date_range


_CACHE_TTL_SECONDS = 24 * 60 * 60

# Temporary testing period for the slow P&L stored procedure.
_TEST_PNL_START_DATE = "2026-04-01"
_TEST_PNL_END_DATE = "2027-03-31"

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
    return (
        series.astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )


def _fetch_pnl_sp_data():
    started = time.perf_counter()
    engine = get_engine()

    with engine.connect() as conn:
        df = pd.read_sql_query(
            _PNL_QUERY,
            conn,
            params={
                "branch_code": "00000",
                "from_date": _TEST_PNL_START_DATE,
                "to_date": _TEST_PNL_END_DATE,
                "grno": "",
            },
        )

    print(
        f"[P&L SP Loader] {_TEST_PNL_START_DATE} to {_TEST_PNL_END_DATE} | "
        f"rows={len(df):,} | seconds={time.perf_counter() - started:.2f}"
    )
    return df


def _prepare_revenue_data(df):
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    gr_col = _find_column(out, ["GRNO", "grno", "gr_no", "grnumber"])
    revenue_col = _find_column(out, ["REVENUE", "revenue", "freight"])

    if gr_col is None:
        raise ValueError(
            "Revenue data does not contain a GRNO column. "
            f"Available columns: {list(out.columns)}"
        )

    if revenue_col is None:
        raise ValueError(
            "Revenue data does not contain a REVENUE column. "
            f"Available columns: {list(out.columns)}"
        )

    rename_map = {}
    if gr_col != "grno":
        rename_map[gr_col] = "grno"
    if revenue_col != "REVENUE":
        rename_map[revenue_col] = "REVENUE"

    out = out.rename(columns=rename_map)
    out["grno"] = _clean_grno(out["grno"])
    out["REVENUE"] = pd.to_numeric(out["REVENUE"], errors="coerce").fillna(0.0)

    return out


def _prepare_pnl_sp_data(df):
    required_columns = {
        "GRNO": ["GRNO", "grno", "gr_no", "grnumber"],
        "DELIVERYINCOME": ["DELIVERYINCOME", "delivery_income"],
        "OTHERCHARGES": ["OTHERCHARGES", "other_charges"],
        "ADDITIONALFREIGHT": ["ADDITIONALFREIGHT", "additional_freight"],
        "OTHERINCOME": ["OTHERINCOME", "other_income"],
        "RAW_EXPENSE": ["EXPENSE", "expense", "raw_expense"],
    }

    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "grno",
                "DELIVERYINCOME",
                "OTHERCHARGES",
                "ADDITIONALFREIGHT",
                "OTHERINCOME",
                "RAW_EXPENSE",
            ]
        )

    out = df.copy()
    rename_map = {}

    for target, candidates in required_columns.items():
        source = _find_column(out, candidates)
        if source is None:
            if target == "OTHERCHARGES":
                out[target] = 0.0
                continue
            raise ValueError(
                f"P&L stored procedure did not return {target}. "
                f"Available columns: {list(out.columns)}"
            )
        if source != target:
            rename_map[source] = target

    out = out.rename(columns=rename_map)
    out = out.rename(columns={"GRNO": "grno"})
    out["grno"] = _clean_grno(out["grno"])

    numeric_columns = [
        "DELIVERYINCOME",
        "OTHERCHARGES",
        "ADDITIONALFREIGHT",
        "OTHERINCOME",
        "RAW_EXPENSE",
    ]

    for column in numeric_columns:
        out[column] = pd.to_numeric(out[column], errors="coerce").fillna(0.0)

    # One GR can have more than one row in the SP output, so aggregate first.
    return (
        out.groupby("grno", as_index=False, dropna=False)[numeric_columns]
        .sum()
    )


def _merge_revenue_and_pnl(revenue_df, pnl_sp_df):
    revenue = _prepare_revenue_data(revenue_df)
    pnl_data = _prepare_pnl_sp_data(pnl_sp_df)

    if revenue.empty:
        return revenue

    # Remove old calculation columns, if any, before adding the new P&L values.
    revenue = revenue.drop(
        columns=[
            col
            for col in [
                "EXPENSE",
                "PNL",
                "RAW_EXPENSE",
                "DELIVERYINCOME",
                "OTHERCHARGES",
                "ADDITIONALFREIGHT",
                "OTHERINCOME",
            ]
            if col in revenue.columns
        ],
        errors="ignore",
    )

    result = revenue.merge(
        pnl_data,
        on="grno",
        how="left",
        validate="many_to_one",
    )

    calculation_columns = [
        "DELIVERYINCOME",
        "OTHERCHARGES",
        "ADDITIONALFREIGHT",
        "OTHERINCOME",
        "RAW_EXPENSE",
    ]

    for column in calculation_columns:
        result[column] = pd.to_numeric(
            result[column], errors="coerce"
        ).fillna(0.0)

    # Expense formula:
    # EXPENSE - (ADDITIONALFREIGHT + DELIVERYINCOME + OTHERINCOME)
    result["EXPENSE"] = (
        result["RAW_EXPENSE"]
        - (
            result["ADDITIONALFREIGHT"]
            + result["DELIVERYINCOME"]
            + result["OTHERINCOME"]
        )
    )

    # P&L formula:
    # (FREIGHT + DELIVERYINCOME + ADDITIONALFREIGHT + OTHERINCOME) - EXPENSE
    # Existing REVENUE is being used as FREIGHT.
    result["PNL"] = (
        result["REVENUE"]
        + result["DELIVERYINCOME"]
        + result["ADDITIONALFREIGHT"]
        + result["OTHERINCOME"]
        - result["RAW_EXPENSE"]
    )

    return result


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False, max_entries=6)
def load_pnl_data(start_date, end_date, view_type="origin"):
    """
    Load revenue data for the selected period and merge it with the temporary
    FY 2026-27 P&L stored-procedure result.

    During testing, select FY 2026-2027 in the dashboard so both periods match.
    """
    revenue_df = load_booking_data(start_date, end_date, view_type)
    pnl_sp_df = _fetch_pnl_sp_data()
    return _merge_revenue_and_pnl(revenue_df, pnl_sp_df)


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False, max_entries=6)
def load_pnl_data_pair(
    start_date,
    end_date,
    prev_start,
    prev_end,
    view_type="origin",
):
    """
    Return current-year P&L data and an empty previous-year dataframe.

    Previous-year P&L is intentionally not loaded during testing because the
    stored procedure is slow.
    """
    del prev_start, prev_end

    current_df = load_pnl_data(start_date, end_date, view_type)
    previous_df = current_df.iloc[0:0].copy()

    return current_df, previous_df

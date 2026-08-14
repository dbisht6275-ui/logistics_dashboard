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


def _normalise_view_type(view_type):
    value = str(view_type or "origin").strip().upper()
    aliases = {
        "ORIGIN": "ORIGIN",
        "O": "ORIGIN",
        "ORIG": "ORIGIN",
        "DESTINATION": "DESTINATION",
        "DEST": "DESTINATION",
        "D": "DESTINATION",
    }
    normalised = aliases.get(value)
    if normalised is None:
        raise ValueError(
            f"Invalid view type: {view_type!r}. Allowed values are Origin and Destination."
        )
    return normalised


def _find_column(df, candidates):
    if df is None:
        return None
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
    gr_col = _find_column(out, ["GRNO", "grno", "gr_no", "grnumber", "gr_number"])
    revenue_col = _find_column(
        out,
        ["REVENUE", "revenue", "freight", "business", "totalfreight", "total_freight"],
    )

    if gr_col is None or revenue_col is None:
        raise ValueError(
            "Revenue data requires GRNO and REVENUE/FREIGHT columns. "
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
    out = out[
        out["grno"].notna()
        & out["grno"].ne("")
        & out["grno"].str.lower().ne("nan")
    ].copy()
    return out


def _prepare_pnl_sp_data(df):
    aliases = {
        "GRNO": ["GRNO", "grno", "gr_no", "grnumber", "gr_number"],
        "REVENUE": ["REVENUE", "revenue", "freight", "business", "totalfreight", "total_freight"],
        "DELIVERYINCOME": ["DELIVERYINCOME", "delivery_income"],
        "OTHERCHARGES": ["OTHERCHARGES", "other_charges"],
        "ADDITIONALFREIGHT": ["ADDITIONALFREIGHT", "additional_freight"],
        "OTHERINCOME": ["OTHERINCOME", "other_income"],
        "RAW_EXPENSE": ["EXPENSE", "expense", "raw_expense"],
    }
    output_columns = [
        "grno",
        "REVENUE",
        "DELIVERYINCOME",
        "OTHERCHARGES",
        "ADDITIONALFREIGHT",
        "OTHERINCOME",
        "RAW_EXPENSE",
    ]
    if df is None or df.empty:
        return pd.DataFrame(columns=output_columns)

    out = df.copy()
    rename_map = {}
    for target, candidates in aliases.items():
        source = _find_column(out, candidates)
        if source is None:
            if target == "OTHERCHARGES":
                out[target] = 0.0
                continue
            raise ValueError(
                f"P&L SP did not return {target}. Available columns: {list(out.columns)}"
            )
        rename_map[source] = target

    out = out.rename(columns=rename_map).rename(columns={"GRNO": "grno"})
    out["grno"] = _clean_grno(out["grno"])

    numeric_columns = [
        "REVENUE",
        "DELIVERYINCOME",
        "OTHERCHARGES",
        "ADDITIONALFREIGHT",
        "OTHERINCOME",
        "RAW_EXPENSE",
    ]
    for column in numeric_columns:
        out[column] = pd.to_numeric(out[column], errors="coerce").fillna(0.0)

    out = out[
        out["grno"].notna()
        & out["grno"].ne("")
        & out["grno"].str.lower().ne("nan")
    ].copy()

    return out.groupby("grno", as_index=False, dropna=False)[numeric_columns].sum()


def _merge_revenue_and_pnl(revenue_df, pnl_sp_df):
    revenue = _prepare_revenue_data(revenue_df)
    pnl_data = _prepare_pnl_sp_data(pnl_sp_df)
    if revenue.empty:
        return revenue

    revenue = revenue.drop(
        columns=[
            column
            for column in [
                "REVENUE",
                "EXPENSE",
                "PNL",
                "RAW_EXPENSE",
                "DELIVERYINCOME",
                "OTHERCHARGES",
                "ADDITIONALFREIGHT",
                "OTHERINCOME",
            ]
            if column in revenue.columns
        ],
        errors="ignore",
    )

    result = revenue.merge(pnl_data, on="grno", how="left", validate="many_to_one")

    numeric_columns = [
        "REVENUE",
        "DELIVERYINCOME",
        "OTHERCHARGES",
        "ADDITIONALFREIGHT",
        "OTHERINCOME",
        "RAW_EXPENSE",
    ]
    for column in numeric_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0.0)

    result["EXPENSE"] = result["RAW_EXPENSE"] - (
        result["ADDITIONALFREIGHT"]
        + result["DELIVERYINCOME"]
        + result["OTHERINCOME"]
    )
    result["PNL"] = (
        result["REVENUE"]
        + result["DELIVERYINCOME"]
        + result["ADDITIONALFREIGHT"]
        + result["OTHERINCOME"]
        - result["RAW_EXPENSE"]
    )
    return result


def _fetch_complete_period(start_date, end_date, view_type):
    normalised_view = _normalise_view_type(view_type)
    started = time.perf_counter()

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="pnl-period") as executor:
        revenue_future = executor.submit(
            load_booking_data,
            start_date,
            end_date,
            normalised_view,
        )
        pnl_future = executor.submit(_fetch_pnl_sp_data, start_date, end_date)
        revenue_df = revenue_future.result()
        pnl_sp_df = pnl_future.result()

    revenue_rows = len(revenue_df) if revenue_df is not None else 0
    pnl_rows = len(pnl_sp_df) if pnl_sp_df is not None else 0
    print(
        f"[P&L Period Debug] view={normalised_view} | dates={start_date} to {end_date} | "
        f"revenue_rows={revenue_rows:,} | pnl_rows={pnl_rows:,}"
    )

    if revenue_df is None or revenue_df.empty:
        print(
            f"[P&L Period Warning] Revenue loader returned no rows for "
            f"view={normalised_view}, period={start_date} to {end_date}"
        )
        return pd.DataFrame()

    result = _merge_revenue_and_pnl(revenue_df, pnl_sp_df)
    print(
        f"[P&L Period Complete] view={normalised_view} | merged_rows={len(result):,} | "
        f"seconds={time.perf_counter() - started:.2f}"
    )
    return result


def _fetch_both_views_period(start_date, end_date):
    """Fetch Origin + Destination revenue and the shared P&L SP only once.

    The stored procedure result is independent of view type, so reusing it avoids
    running the same heavy SP twice for the same reporting period.
    """
    started = time.perf_counter()

    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="pnl-both") as executor:
        origin_revenue_future = executor.submit(
            load_booking_data, start_date, end_date, "ORIGIN"
        )
        destination_revenue_future = executor.submit(
            load_booking_data, start_date, end_date, "DESTINATION"
        )
        pnl_future = executor.submit(_fetch_pnl_sp_data, start_date, end_date)

        origin_revenue = origin_revenue_future.result()
        destination_revenue = destination_revenue_future.result()
        pnl_sp_df = pnl_future.result()

    origin_df = (
        _merge_revenue_and_pnl(origin_revenue, pnl_sp_df)
        if origin_revenue is not None and not origin_revenue.empty
        else pd.DataFrame()
    )
    destination_df = (
        _merge_revenue_and_pnl(destination_revenue, pnl_sp_df)
        if destination_revenue is not None and not destination_revenue.empty
        else pd.DataFrame()
    )

    print(
        f"[P&L Both Views] {start_date} to {end_date} | "
        f"origin_rows={len(origin_df):,} | destination_rows={len(destination_df):,} | "
        f"seconds={time.perf_counter() - started:.2f}"
    )
    return origin_df, destination_df


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False, max_entries=8)
def load_pnl_sp_revenue_total(start_date, end_date):
    """Return total REVENUE directly from the P&L stored procedure.

    This is intentionally independent of booking-data/branch joins so the
    consolidated Business / Revenue KPI exactly matches the P&L SP.
    """
    df = _fetch_pnl_sp_data(start_date, end_date)
    if df is None or df.empty:
        return 0.0

    gr_col = _find_column(df, ["GRNO", "grno", "gr_no", "grnumber", "gr_number"])
    revenue_col = _find_column(
        df,
        ["REVENUE", "revenue", "freight", "business", "totalfreight", "total_freight"],
    )

    if revenue_col is None:
        raise ValueError(
            "P&L SP did not return REVENUE. "
            f"Available columns: {list(df.columns)}"
        )

    out = df.copy()
    out["_REVENUE"] = pd.to_numeric(out[revenue_col], errors="coerce").fillna(0.0)

    # The SP currently returns one row per GR. Keep this de-duplication guard
    # so the KPI remains correct even if detail rows are added later.
    if gr_col is not None:
        out["_GRNO"] = _clean_grno(out[gr_col])
        out = (
            out[
                out["_GRNO"].notna()
                & out["_GRNO"].ne("")
                & out["_GRNO"].str.lower().ne("nan")
            ]
            .groupby("_GRNO", as_index=False, dropna=False)["_REVENUE"]
            .first()
        )

    total = float(out["_REVENUE"].sum())
    print(
        f"[P&L SP Revenue KPI] {start_date} to {end_date} | "
        f"revenue={total:,.2f}"
    )
    return total


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False, max_entries=8)
def load_pnl_both_views(start_date, end_date):
    """Cached Origin + Destination P&L with one shared SP execution."""
    return _fetch_both_views_period(start_date, end_date)


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False, max_entries=12)
def load_pnl_data(start_date, end_date, view_type="origin"):
    return _fetch_complete_period(
        start_date,
        end_date,
        _normalise_view_type(view_type),
    )


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False, max_entries=8)
def load_pnl_data_pair(start_date, end_date, prev_start, prev_end, view_type="origin"):
    """Load current FY and previous FY P&L concurrently."""
    normalised_view = _normalise_view_type(view_type)
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="pnl-pair") as executor:
        current_future = executor.submit(
            _fetch_complete_period,
            start_date,
            end_date,
            normalised_view,
        )
        previous_future = executor.submit(
            _fetch_complete_period,
            prev_start,
            prev_end,
            normalised_view,
        )
        current_df = current_future.result()
        previous_df = previous_future.result()
    return current_df, previous_df

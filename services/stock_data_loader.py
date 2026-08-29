"""SQL Server loader for the Stock Operations dashboard."""

from __future__ import annotations

import time
from datetime import date

import pandas as pd
import streamlit as st
from sqlalchemy import text

from services.database import get_engine


CACHE_TTL_SECONDS = 60 * 60
STOCK_PROCEDURE = "dbo.greentransweb_branchstock_v5_sugam"

# Parameter names are fixed and values are bound separately.  This keeps the
# execution safe while matching the procedure supplied by the ERP team.
STOCK_QUERY = text(
    f"""
    EXEC {STOCK_PROCEDURE}
        @prmselectionstr       = :selection_str,
        @prmselectiontype      = :selection_type,
        @prmorgcode            = :origin_code,
        @prmdestcode           = :destination_code,
        @prmfromdt             = :from_date,
        @prmtodt               = :to_date,
        @prmasondt             = :as_on_date,
        @prmusercode           = :user_code,
        @prmmenucode           = :menu_code,
        @prmsessionid          = :session_id,
        @prmshowintransitstock = :show_in_transit,
        @prmexecutereport      = :execute_report,
        @prmgrnostr            = :gr_numbers,
        @prmcustomerstr        = :customers,
        @prmcngrstr            = :consignors,
        @prmcngestr            = :consignees,
        @prmstockcategorycode  = :stock_categories
    """
)


# SP output name -> dashboard's stable internal name.
COLUMN_ALIASES = {
    "sno": "serial_no",
    "branchcode": "branch_code",
    "branchname": "branch",
    "stocktype": "stock_type",
    "grno": "gr_no",
    "grdt": "gr_date",
    "originzone": "origin_zone",
    "origincircle": "origin_circle",
    "origin": "origin",
    "destzone": "destination_zone",
    "destcircle": "destination_circle",
    "destname": "destination",
    "viastation": "via_border",
    "goods": "goods",
    "valgoods": "goods_value",
    "bookedpckgs": "booked_packages",
    "balancepckgs": "balance_packages",
    "bookedaweight": "booked_actual_weight",
    "bookedcweight": "booked_charge_weight",
    "balanceaweight": "balance_actual_weight",
    "balancecweight": "balance_charge_weight",
    "pmark": "package_mark",
    "cngr": "consignor",
    "cngrdetail": "consignor_detail",
    "cnge": "consignee",
    "cngedetail": "consignee_detail",
    "topay": "topay",
    "advance": "advance",
    "stocktopay": "stock_topay",
    "paid": "paid",
    "tbb": "tbb",
    "servicetax": "service_tax",
    "tamount": "total_amount",
    "grtype": "gr_type",
    "transtatus": "tran_status",
    "deliverytype": "delivery_type",
    "productname": "product",
    "stockdays": "stock_days",
    "receivedt": "arrival_date",
    "receivetime": "arrival_time",
    "stocktime": "stock_time",
    "godownname": "godown",
    "ewaybillno": "eway_bill_no",
    "ewaybillvaliduptodt": "eway_valid_upto",
    "loadtype": "load_type",
    "deliverypoint": "delivery_point",
    "stockremarks": "remarks",
    "crmremarks": "crm_remarks",
    "mdoremarks": "mdo_remarks",
    "isdelivered": "is_delivered",
    "gatepassdt": "gatepass_date",
    "stockcategory": "stock_category",
    "reason": "reason",
    "reasoncategory": "reason_category",
    "reasoncode": "reason_code",
    "edd": "edd",
}

NUMERIC_COLUMNS = [
    "goods_value", "booked_packages", "balance_packages",
    "booked_actual_weight", "booked_charge_weight",
    "balance_actual_weight", "balance_charge_weight", "topay", "advance",
    "stock_topay", "paid", "tbb", "service_tax", "total_amount", "stock_days",
]
DATE_COLUMNS = ["gr_date", "arrival_date", "eway_valid_upto", "gatepass_date", "edd"]
TEXT_COLUMNS = [
    "branch", "stock_type", "origin_zone", "origin_circle", "origin",
    "destination_zone", "destination_circle", "destination", "via_border",
    "goods", "consignor", "consignee", "delivery_type", "product",
    "stock_time", "godown", "load_type", "delivery_point", "stock_category",
    "remarks", "reason", "reason_category",
]


def _runtime_parameters(start_date, end_date, as_on_date):
    """Build the exact parameter set required by the supplied procedure."""
    try:
        settings = dict(st.secrets.get("stock_dashboard", {}))
    except Exception:
        settings = {}

    return {
        "selection_str": str(settings.get("selection_str", "00000")),
        "selection_type": str(settings.get("selection_type", "C"))[:1],
        "origin_code": str(settings.get("origin_code", "ALL")),
        "destination_code": str(settings.get("destination_code", "ALL")),
        "from_date": pd.Timestamp(start_date).to_pydatetime(),
        "to_date": pd.Timestamp(end_date).to_pydatetime(),
        "as_on_date": pd.Timestamp(as_on_date).to_pydatetime(),
        "user_code": str(settings.get("user_code", "0000"))[:4],
        "menu_code": str(settings.get("menu_code", ""))[:30],
        "session_id": str(settings.get("session_id", "SYST"))[:18],
        # Y includes stock currently moving between branches.
        "show_in_transit": str(settings.get("show_in_transit", "Y"))[:1],
        "execute_report": "Y",
        "gr_numbers": None,
        "customers": None,
        "consignors": None,
        "consignees": None,
        # ALL lets the existing procedure include every stock category,
        # including the procedure's category-0 fallback.
        "stock_categories": str(settings.get("stock_categories", "ALL")),
    }


def _fetch_stock_data(start_date, end_date, as_on_date):
    started = time.perf_counter()
    params = _runtime_parameters(start_date, end_date, as_on_date)
    with get_engine().connect() as connection:
        raw_df = pd.read_sql_query(STOCK_QUERY, connection, params=params)

    print(
        f"[Stock Loader] {start_date} to {end_date} | as-on={as_on_date} | "
        f"rows={len(raw_df):,} | seconds={time.perf_counter() - started:.2f}"
    )
    return raw_df


def normalise_stock_data(raw_df, as_on_date=None):
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()

    df = raw_df.copy()
    df.columns = [str(column).strip().casefold() for column in df.columns]

    if "commandstatus" in df.columns:
        status = pd.to_numeric(df["commandstatus"], errors="coerce")
        failed = status.eq(-1)
        if failed.any():
            message = "Stored procedure returned an error."
            if "commandmessage" in df.columns:
                returned = df.loc[failed, "commandmessage"].dropna().astype(str)
                if not returned.empty:
                    message = returned.iloc[0]
            raise RuntimeError(message)

    df = df.rename(columns={key: value for key, value in COLUMN_ALIASES.items() if key in df.columns})
    required = {"branch_code", "branch", "stock_type", "gr_no"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(
            "Stored procedure output is missing required columns: " + ", ".join(missing)
        )

    df = df[df["gr_no"].notna() & df["branch"].notna()].copy()
    cleaned_branch_code = (
        df["branch_code"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )
    df = df[cleaned_branch_code.ne("")].copy()
    df["branch_code"] = cleaned_branch_code.loc[df.index].str.zfill(3)

    for column in NUMERIC_COLUMNS:
        if column not in df.columns:
            df[column] = 0.0
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0)

    for column in DATE_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NaT
        df[column] = pd.to_datetime(df[column], errors="coerce", dayfirst=True)

    for column in TEXT_COLUMNS:
        if column not in df.columns:
            df[column] = "Unknown"
        df[column] = (
            df[column].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
        )

    df["gr_no"] = df["gr_no"].astype(str).str.replace(r"\.0$", "", regex=True)
    df["age_band"] = pd.cut(
        df["stock_days"], bins=[-1, 7, 14, float("inf")],
        labels=["0-7 Days", "8-14 Days", "15+ Days"],
    ).astype(str)
    df["is_critical"] = df["stock_days"].ge(15)
    comparison_date = pd.Timestamp(as_on_date or pd.Timestamp.today()).normalize()
    df["is_edd_overdue"] = df["edd"].notna() & df["edd"].lt(comparison_date)
    return df.reset_index(drop=True)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False, max_entries=4)
def load_stock_data(
    start_date=None,
    end_date=None,
    as_on_date=None,
):
    """Execute the ERP stock procedure and return dashboard-ready data."""
    today = date.today()
    start_date = start_date or today.replace(day=1)
    end_date = end_date or today
    as_on_date = as_on_date or end_date
    raw_df = _fetch_stock_data(start_date, end_date, as_on_date)
    return normalise_stock_data(raw_df, as_on_date=as_on_date)

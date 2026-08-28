"""Data access and normalisation for the Stock Operations dashboard.

The dashboard currently defaults to the bundled Excel snapshot.  When the
production stored procedure is ready, configure the ``stock_dashboard`` block
in Streamlit Secrets and switch ``source`` to ``stored_procedure``.  The UI
does not need to change.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import text

from services.database import get_engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXCEL_PATH = PROJECT_ROOT / "data" / "BranchStockReport.xlsx"
CACHE_TTL_SECONDS = 60 * 60


COLUMN_ALIASES = {
    "S#": "serial_no",
    "Branch": "branch",
    "Stock Type": "stock_type",
    "GR #": "gr_no",
    "GR Date": "gr_date",
    "Origin Zone": "origin_zone",
    "Origin Circle": "origin_circle",
    "Origin": "origin",
    "Destination Zone": "destination_zone",
    "Destination Circle": "destination_circle",
    "Destination": "destination",
    "Via Border": "via_border",
    "Goods": "goods",
    "Goods Value": "goods_value",
    "Booked Pckgs": "booked_packages",
    "Balance Pckgs": "balance_packages",
    "Booked A. Weight": "booked_actual_weight",
    "Booked C. Weight": "booked_charge_weight",
    "Balance A. Weight": "balance_actual_weight",
    "Balance C. Weight": "balance_charge_weight",
    "Consignor": "consignor",
    "Consignee": "consignee",
    "Topay": "topay",
    "Advance": "advance",
    "Stock Topay": "stock_topay",
    "Paid": "paid",
    "TBB": "tbb",
    "Total Amount": "total_amount",
    "GR Type": "gr_type",
    "Tran Status": "tran_status",
    "Delivery Type": "delivery_type",
    "Product": "product",
    "Stock Days": "stock_days",
    "Arrival Date": "arrival_date",
    "Stock Time": "stock_time",
    "Godown": "godown",
    "Eway Bill #": "eway_bill_no",
    "Eway Valid Upto": "eway_valid_upto",
    "Load Type": "load_type",
    "Delivery Point": "delivery_point",
    "Is Delivered": "is_delivered",
    "Stock Category": "stock_category",
    "Remarks": "remarks",
    "Controllable": "controllable",
    "EDD": "edd",
}

NUMERIC_COLUMNS = [
    "goods_value", "booked_packages", "balance_packages",
    "booked_actual_weight", "booked_charge_weight",
    "balance_actual_weight", "balance_charge_weight", "topay", "advance",
    "stock_topay", "paid", "tbb", "total_amount", "stock_days",
]
DATE_COLUMNS = ["gr_date", "arrival_date", "eway_valid_upto", "edd"]
TEXT_COLUMNS = [
    "branch", "stock_type", "origin_zone", "origin_circle", "origin",
    "destination_zone", "destination_circle", "destination", "via_border",
    "goods", "consignor", "consignee", "delivery_type", "product",
    "stock_time", "godown", "load_type", "delivery_point", "controllable",
]


def _excel_header_row(path: Path) -> int:
    """Find the row containing the real stock-report header."""
    preview = pd.read_excel(path, header=None, nrows=15)
    for index, row in preview.iterrows():
        values = {str(value).strip() for value in row.dropna().tolist()}
        if {"Branch", "Stock Type", "GR #"}.issubset(values):
            return int(index)
    raise ValueError("Could not find Branch / Stock Type / GR # header row.")


def _load_excel(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Stock Excel file not found: {path}")
    return pd.read_excel(path, header=_excel_header_row(path))


def _stored_procedure_settings():
    try:
        return dict(st.secrets.get("stock_dashboard", {}))
    except Exception:
        return {}


def _load_stored_procedure(start_date=None, end_date=None) -> pd.DataFrame:
    settings = _stored_procedure_settings()
    procedure = str(settings.get("procedure", "")).strip()
    if not procedure:
        raise ValueError(
            "Set stock_dashboard.procedure in Streamlit Secrets before using "
            "the stored-procedure source."
        )
    if not re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?", procedure):
        raise ValueError("Stored-procedure name contains unsupported characters.")

    use_dates = bool(settings.get("use_date_parameters", False))
    if use_dates:
        query = text(
            f"EXEC {procedure} @StartDate = :start_date, @EndDate = :end_date"
        )
        params = {"start_date": start_date, "end_date": end_date}
    else:
        query = text(f"EXEC {procedure}")
        params = {}

    with get_engine().connect() as connection:
        return pd.read_sql_query(query, connection, params=params)


def normalise_stock_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Return a predictable schema for both Excel and stored-procedure data."""
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()

    df = raw_df.copy()
    df.columns = [str(column).strip() for column in df.columns]
    df = df.rename(columns={key: value for key, value in COLUMN_ALIASES.items() if key in df.columns})

    required = {"branch", "stock_type", "gr_no"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError("Stock data is missing required columns: " + ", ".join(missing))

    # The exported report contains a final totals row without a GR/branch.
    df = df[df["gr_no"].notna() & df["branch"].notna()].copy()

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
        df["stock_days"],
        bins=[-1, 7, 14, float("inf")],
        labels=["0-7 Days", "8-14 Days", "15+ Days"],
    ).astype(str)
    df["is_critical"] = df["stock_days"].ge(15)
    df["is_edd_overdue"] = df["edd"].notna() & df["edd"].lt(pd.Timestamp.today().normalize())
    return df.reset_index(drop=True)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False, max_entries=4)
def load_stock_data(source="excel", start_date=None, end_date=None, excel_path=None):
    """Load stock data through the selected backend and normalise it."""
    selected_source = str(source or "excel").strip().lower()
    if selected_source == "stored_procedure":
        raw_df = _load_stored_procedure(start_date=start_date, end_date=end_date)
    elif selected_source == "excel":
        raw_df = _load_excel(Path(excel_path) if excel_path else DEFAULT_EXCEL_PATH)
    else:
        raise ValueError(f"Unsupported stock source: {source}")
    return normalise_stock_data(raw_df)


def configured_stock_source():
    settings = _stored_procedure_settings()
    return str(settings.get("source", "excel")).strip().lower() or "excel"

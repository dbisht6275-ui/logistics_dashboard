import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import html
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from services.data_CustomerAnalysis import load_booking_data, get_date_range

# =====================================================
# Page Styling
# =====================================================
def apply_dashboard_style() -> None:
    st.markdown(
        """
        <style>
        /* ---------- Page spacing ---------- */
        .block-container {
            padding-top: 1.15rem !important;
            padding-bottom: 2rem !important;
        }

        /* ---------- Dashboard Heading ---------- */
        .dashboard-header {
            margin: 0 0 1rem 0;
            padding: 0;
        }
        .dashboard-title {
            margin: 0;
            color: #0f172a;
            font-size: 30px;
            font-weight: 800;
            line-height: 1.15;
            letter-spacing: -0.4px;
        }
        .dashboard-subtitle {
            margin-top: 6px;
            color: #64748b;
            font-size: 14px;
            font-weight: 400;
        }

        /* ---------- KPI Cards: same style as Overview Dashboard ---------- */
        .kpi-card {
            background: #ffffff;
            padding: 8px 9px;
            border-radius: 10px;
            border: 1px solid #e5e7eb;
            border-left: 4px solid var(--accent-color, #2563eb);
            box-shadow: 0 3px 10px rgba(0,0,0,0.08);
            min-height: 70px;
            position: relative;
            overflow: hidden;
            transition: transform 0.16s ease, box-shadow 0.16s ease;
        }
        .kpi-card:hover {
            transform: translateY(-1px);
            box-shadow: 0 5px 14px rgba(15,23,42,0.12);
        }
        .kpi-card-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 6px;
        }
        .kpi-title {
            color: var(--accent-color, #2563eb);
            font-size: 11px;
            font-weight: 800;
            line-height: 1.15;
            white-space: normal;
        }
        .kpi-icon {
            font-size: 18px;
            line-height: 1;
            flex: 0 0 auto;
        }
        .kpi-value {
            font-size: 17px;
            font-weight: 900;
            color: #0f172a;
            margin-top: 2px;
            line-height: 1.15;
            white-space: nowrap;
        }
        .kpi-delta {
            font-size: 10.5px;
            font-weight: 700;
            margin-top: 2px;
            line-height: 1.15;
            white-space: normal;
        }

        /* ---------- Section Headers ---------- */
        .section-header {
            font-size: 14px;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 6px;
            padding-bottom: 4px;
            border-bottom: 2px solid #e2e8f0;
        }

        /* ---------- Filter Row ---------- */
        div[data-testid="stHorizontalBlock"] > div {
            align-items: flex-end !important;
        }

        /* ---------- Export Button ---------- */
        div[data-testid="stDownloadButton"] button {
            background-color: #1e40af !important;
            color: white !important;
            font-weight: 600 !important;
            border-radius: 6px !important;
            padding: 8px 14px !important;
            width: 100% !important;
            font-size: 13px !important;
            border: none !important;
            margin-top: 4px;
        }
        div[data-testid="stDownloadButton"] button:hover {
            background-color: #1d4ed8 !important;
        }

        /* ============================================= */
        /*   DATAFRAME COMPACT + SMALL FONT (columns fit) */
        /* ============================================= */
        div[data-testid="stDataFrame"] {
            border-radius: 8px;
            overflow: hidden;
        }
        /* Cell + header font chhota */
        div[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"] * {
            font-size: 11px !important;
        }
        /* Header thoda bold */
        div[data-testid="stDataFrame"] thead tr th {
            font-size: 11px !important;
            font-weight: 700 !important;
            padding: 4px 6px !important;
        }
        /* Cell padding kam -> zyada columns fit */
        div[data-testid="stDataFrame"] tbody tr td {
            font-size: 11px !important;
            padding: 3px 6px !important;
        }
        /* Glide grid (newer Streamlit) ke liye bhi */
        .glideDataEditor {
            font-size: 11px !important;
        }
        

        /* ---------- Compact layout overrides: aligned with Overview ---------- */
        .block-container {
            max-width: 100% !important;
            padding: 0.35rem 0.75rem 0.75rem !important;
        }
        .block-container > div:first-child {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        div[data-testid="stVerticalBlock"] {
            gap: 0.35rem !important;
        }
        div[data-testid="stHorizontalBlock"] {
            gap: 0.50rem !important;
            align-items: flex-start !important;
        }
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            min-width: 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 11px !important;
            box-shadow: 0 3px 10px rgba(15,42,67,0.07) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding: 0.55rem 0.65rem !important;
        }

        /* ---------- Compact heading card ---------- */
        .dashboard-header {
            margin: 0 !important;
            padding: 2px 0 3px 4px !important;
        }
        .dashboard-title {
            margin: 0 !important;
            color: #102a43 !important;
            font-size: 19px !important;
            font-weight: 850 !important;
            line-height: 1.15 !important;
            letter-spacing: -0.3px !important;
        }
        .dashboard-subtitle {
            margin-top: 2px !important;
            color: #64748b !important;
            font-size: 11px !important;
            font-weight: 400 !important;
        }

        /* ---------- Compact filters and controls ---------- */
        div[data-testid="stSelectbox"] {
            padding: 2px 3px 4px !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            overflow: visible !important;
        }
        div[data-baseweb="select"] > div {
            min-height: 34px !important;
        }
        .stDownloadButton > button {
            min-height: 34px !important;
            border-radius: 9px !important;
            font-size: 12px !important;
            font-weight: 750 !important;
            white-space: nowrap !important;
        }

        /* ---------- Compact KPI row: dimensions inherited from Overview-style card ---------- */
        /* ---------- Compact insight sections ---------- */
        hr {
            margin-top: 0.35rem !important;
            margin-bottom: 0.35rem !important;
        }
        .section-header {
            margin-top: 0 !important;
            margin-bottom: 0.25rem !important;
        }
        [data-testid="stDataFrame"] {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }
        [data-testid="stPlotlyChart"] {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }
        div[data-testid="stTabs"] {
            margin-top: 0 !important;
        }
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 0.35rem !important;
            background: #ffffff !important;
            border-bottom: 1px solid #dbe3ec !important;
            padding: 0 0.15rem !important;
        }
        div[data-testid="stTabs"] button[data-baseweb="tab"] {
            background: #ffffff !important;
            background-image: none !important;
            border: none !important;
            border-radius: 0 !important;
            color: #475569 !important;
            box-shadow: none !important;
            font-weight: 650 !important;
            padding: 0.55rem 0.80rem !important;
        }
        div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
            background: #ffffff !important;
            background-image: none !important;
            color: #1d4ed8 !important;
            border-bottom: 3px solid #2563eb !important;
        }
        div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
            background-color: transparent !important;
        }
        h1, h2, h3, h4, h5, h6 {
            margin-top: 0.10rem !important;
            margin-bottom: 0.25rem !important;
        }

        /* ---------- Prevent KPI / insight overlap ---------- */
        .kpi-row-spacer {
            height: 12px;
            width: 100%;
            clear: both;
        }
        .insight-section-spacer {
            height: 12px;
            width: 100%;
            clear: both;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stPlotlyChart"] {
            overflow: hidden !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] .section-header {
            margin-bottom: 0.10rem !important;
        }

        @media (max-width: 1500px) {
            .block-container {
                padding-left: 0.45rem !important;
                padding-right: 0.45rem !important;
            }
            div[data-testid="stHorizontalBlock"] {
                gap: 0.35rem !important;
            }
            .dashboard-title {
                font-size: 18px !important;
            }
        }

        .dashboard-row-gap { height: 12px; min-height: 12px; width: 100%; clear: both; display:block; line-height:12px; font-size:1px; }
        .header-filter-summary { display:flex; flex-wrap:wrap; gap:6px; align-items:center; min-width:0; }
        .header-filter-chip { display:inline-flex; align-items:center; min-height:26px; padding:4px 11px; border:1px solid #bfdbfe; border-radius:999px; background:#f8fbff; color:#1d4ed8; font-size:10px; font-weight:650; white-space:nowrap; box-shadow:0 1px 3px rgba(37,99,235,.06); }
        .section-header {
            border-bottom:0 !important; padding-bottom:0 !important; margin-bottom:7px !important;
            color:#0f2744 !important; font-weight:650 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border:1px solid #dbe4ef !important; background:#ffffff !important;
        }

        .business-movement-title {
            color:#081a33 !important;
            font-weight:850 !important;
            font-size:15px !important;
            opacity:1 !important;
        }
        .kpi-row-spacer {
            height:16px !important;
            min-height:16px !important;
            display:block !important;
        }

        /* ---------- Overview-style filter slicers ---------- */
        .checkbox-slicer-label {
            display:block !important;
            height:22px !important;
            min-height:22px !important;
            margin:0 0 9px 2px !important;
            padding:0 !important;
            line-height:22px !important;
            color:#243b53 !important;
            font-size:10px !important;
            font-family:"Segoe UI",Arial,sans-serif !important;
            font-weight:400 !important;
            white-space:nowrap !important;
            overflow:hidden !important;
            text-overflow:ellipsis !important;
        }
        div[data-testid="stVerticalBlock"]:has(.checkbox-slicer-label) { gap:0 !important; }
        div[data-testid="stElementContainer"]:has(.checkbox-slicer-label) {
            min-height:31px !important;
            height:31px !important;
            margin:0 !important;
            padding:0 !important;
            overflow:visible !important;
        }
        div[data-testid="stPopover"] { width:100% !important; margin:0 !important; padding:0 !important; }
        div[data-testid="stPopover"] > div { width:100% !important; }
        div[data-testid="stPopover"] > div > button {
            width:100% !important;
            min-height:40px !important;
            height:40px !important;
            padding:0 9px !important;
            margin:0 !important;
            border:1px solid #cbd9ea !important;
            border-radius:10px !important;
            background:linear-gradient(180deg,#ffffff 0%,#f5f8fc 100%) !important;
            box-shadow:inset 0 1px 2px rgba(15,23,42,.06) !important;
            color:#102a43 !important;
            font-size:11px !important;
            font-weight:800 !important;
            justify-content:space-between !important;
            transform:none !important;
        }
        div[data-testid="stPopover"] > div > button:hover,
        div[data-testid="stPopover"] > div > button:focus {
            border-color:#cbd9ea !important;
            background:linear-gradient(180deg,#ffffff 0%,#f5f8fc 100%) !important;
            box-shadow:inset 0 1px 2px rgba(15,23,42,.06) !important;
            transform:none !important;
        }
        div[data-testid="stPopoverBody"] { max-height:360px !important; overflow-y:auto !important; }
        div[data-testid="stPopoverBody"] div[data-testid="stButton"] { width:auto !important; margin:0 !important; padding:0 !important; }
        div[data-testid="stPopoverBody"] div[data-testid="stButton"] > button {
            width:auto !important;
            min-width:0 !important;
            min-height:26px !important;
            height:26px !important;
            padding:2px 8px !important;
            margin:0 !important;
            border:1px solid #dbe4ef !important;
            border-radius:6px !important;
            background:#ffffff !important;
            color:#2563eb !important;
            box-shadow:none !important;
            transform:none !important;
            font-size:10px !important;
            font-weight:600 !important;
            line-height:1 !important;
        }
        div[data-testid="stPopoverBody"] div[data-testid="stButton"] > button:hover {
            border-color:#93c5fd !important;
            background:#eff6ff !important;
            color:#1d4ed8 !important;
        }
        div[data-testid="stPopoverBody"] div[data-testid="stMultiSelect"] { margin-top:7px !important; }
        div[data-testid="stPopoverBody"] div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
            min-height:36px !important;
            border:1px solid #cbd9ea !important;
            border-radius:8px !important;
            background:#ffffff !important;
            box-shadow:inset 0 1px 2px rgba(15,23,42,.05) !important;
        }
        @media (max-width:1500px) {
            .checkbox-slicer-label { min-height:21px !important; height:21px !important; line-height:21px !important; font-size:9px !important; }
            div[data-testid="stPopover"] > div > button { min-height:38px !important; height:38px !important; padding-left:7px !important; padding-right:6px !important; font-size:10px !important; }
        }



        /* ---------- Executive customer growth tables ---------- */
        .customer-rank-table {
            width: 100%;
            font-size: 11px;
            color: #0f2742;
        }
        .customer-rank-head,
        .customer-rank-row {
            display: grid;
            grid-template-columns: minmax(145px, 1.55fr) 0.92fr 0.92fr 1.20fr 0.92fr 0.82fr;
            align-items: center;
            column-gap: 10px;
        }
        .customer-rank-head {
            font-weight: 850;
            padding: 6px 4px 7px;
            border-bottom: 1px solid #dbe5f0;
            color: #17365d;
        }
        .customer-rank-row {
            min-height: 34px;
            padding: 4px;
            border-bottom: 1px solid #eef2f7;
        }
        .customer-rank-row:last-child { border-bottom: none; }

        /* ---------- Top customers CY vs LY compact table ---------- */
        .top-customer-table {
            width: 100%;
            font-size: 11px;
            color: #0f2742;
        }
        .top-customer-head,
        .top-customer-row {
            display: grid;
            grid-template-columns: minmax(170px, 1.55fr) minmax(150px, 1.25fr) 0.85fr 0.85fr 0.70fr;
            align-items: center;
            column-gap: 10px;
        }
        .top-customer-head {
            font-weight: 850;
            padding: 6px 4px 7px;
            border-bottom: 1px solid #dbe5f0;
            color: #17365d;
        }
        .top-customer-row {
            min-height: 34px;
            padding: 4px;
            border-bottom: 1px solid #eef2f7;
        }
        .top-customer-row:last-child { border-bottom: none; }
        .top-customer-scale {
            height: 9px;
            background: #edf2f7;
            border-radius: 2px;
            overflow: hidden;
        }
        .top-customer-scale-fill {
            height: 100%;
            background: #2f7de1;
            border-radius: 2px;
        }

        /* ---------- Lost customer compact table ---------- */
        .lost-customer-table {
            width: 100%;
            font-size: 11px;
            color: #0f2742;
        }
        .lost-customer-head,
        .lost-customer-row {
            display: grid;
            grid-template-columns: minmax(220px, 1.8fr) 1.05fr 1.05fr;
            align-items: center;
            column-gap: 10px;
        }
        .lost-customer-head {
            font-weight: 850;
            padding: 6px 4px 7px;
            border-bottom: 1px solid #dbe5f0;
            color: #17365d;
        }
        .lost-customer-row {
            min-height: 34px;
            padding: 4px;
            border-bottom: 1px solid #eef2f7;
        }
        .lost-customer-row:last-child { border-bottom: none; }
        .lost-customer-date {
            text-align: center;
            white-space: nowrap;
            color: #334155;
        }

        /* ---------- Regular customer consistency matrix ---------- */
        .regular-customer-wrap {
            width: 100%;
            overflow-x: auto;
            padding-bottom: 2px;
        }
        .regular-customer-table {
            min-width: 1180px;
            width: 100%;
            font-size: 10.5px;
            color: #0f2742;
        }
        .regular-customer-head,
        .regular-customer-row {
            display: grid;
            align-items: center;
            column-gap: 8px;
        }
        .regular-customer-head {
            font-weight: 850;
            padding: 7px 5px;
            border-bottom: 1px solid #cbd9e8;
            background: #f8fbff;
            color: #17365d;
            position: sticky;
            top: 0;
            z-index: 1;
        }
        .regular-customer-row {
            min-height: 35px;
            padding: 4px 5px;
            border-bottom: 1px solid #edf2f7;
        }
        .regular-customer-row:hover { background: #f8fbff; }
        .regular-customer-month {
            text-align: right;
            white-space: nowrap;
            color: #334155;
        }
        .regular-customer-total {
            text-align: right;
            white-space: nowrap;
            font-weight: 850;
            color: #15803d;
        }
        .regular-customer-consistency {
            text-align: center;
            white-space: nowrap;
            font-weight: 850;
            color: #15803d;
        }
        .regular-customer-muted {
            text-align: center;
            white-space: nowrap;
            color: #64748b;
        }
        .customer-name-cell {
            font-weight: 750;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .customer-num-cell {
            text-align: right;
            white-space: nowrap;
        }
        .customer-growth-cell {
            display: grid;
            grid-template-columns: minmax(44px, 1fr) 46px;
            gap: 6px;
            align-items: center;
            font-weight: 850;
        }
        .customer-growth-track {
            height: 9px;
            background: #edf2f7;
            border-radius: 2px;
            overflow: hidden;
        }
        .customer-growth-fill {
            height: 100%;
            border-radius: 2px;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )



# =====================================================
# Constants
# =====================================================
GREEN  = "#16a34a"
RED    = "#dc2626"
BLUE   = "#2563eb"
ORANGE = "#f59e0b"
PURPLE = "#7c3aed"

FINANCIAL_YEARS = [
    "Select FY",
    "2026-2027",
    "2025-2026",
    "2024-2025",
    "2023-2024",
    "2022-2023",
    "2021-2022",
    "2020-2021",
]

MONTH_ORDER = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
MONTH_MAP = {1: "Apr", 2: "May", 3: "Jun", 4: "Jul", 5: "Aug", 6: "Sep", 7: "Oct", 8: "Nov", 9: "Dec", 10: "Jan", 11: "Feb", 12: "Mar"}
QUARTER_ORDER = ["Q1", "Q2", "Q3", "Q4"]
QUARTER_MAP = {1: "Q1", 2: "Q1", 3: "Q1", 4: "Q2", 5: "Q2", 6: "Q2", 7: "Q3", 8: "Q3", 9: "Q3", 10: "Q4", 11: "Q4", 12: "Q4"}
TOP_N_OPTIONS = [10, 20, 30, 40]

# =====================================================
# Helper Functions
# =====================================================
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    rename_map = {
        "zone":         "Zone",
        "circle":       "Circle",
        "branch":       "Branch",
        "consignor":    "Consignor",
        "consignee":    "Consignee",
        "cngecode":     "ConsigneeCode",
        "shipmentcount":"ShipmentCount",
        "actualweight": "ActualWeight",
        "chargeweight": "ChargeWeight",
        "revenue":      "Revenue",
        "avgdelaydays": "AvgDelayDays",
        "maxdelaydays": "MaxDelayDays",
        "loadtype":     "LoadType",
        "fin_month":    "FIN_MONTH",
        "yr":           "YR",
        "bookingdate":  "BusinessDate",
        "booking_date": "BusinessDate",
        "grdt":         "BusinessDate",
        "grdate":       "BusinessDate",
        "gr_date":      "BusinessDate",
        "lrdate":       "BusinessDate",
        "lr_date":      "BusinessDate",
        "businessdate": "BusinessDate",
        "business_date":"BusinessDate",
    }
    for col in list(df.columns):
        lower_col = col.lower()
        if lower_col in rename_map and col != rename_map[lower_col]:
            df = df.rename(columns={col: rename_map[lower_col]})
    return df


def clean_booking_data(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize the stored-procedure output for Customer Analysis.

    The current procedure returns one GR/shipment row with:
      - grno      -> shipment identifier
      - aweight   -> available shipment weight
      - DelayDays -> shipment delay

    The dashboard expects summary-friendly columns. They are derived here so
    the UI and business calculations can continue without changing the SP.
    """
    df = normalize_columns(df)

    # The stored procedure returns `aweight` instead of the older weight names.
    if "ActualWeight" not in df.columns and "aweight" in df.columns:
        df["ActualWeight"] = df["aweight"]

    # Charge weight is not returned by the current SP. Until the SP exposes a
    # separate charge-weight field, use the available weight as the fallback.
    if "ChargeWeight" not in df.columns and "ActualWeight" in df.columns:
        df["ChargeWeight"] = df["ActualWeight"]

    # Each returned GR row represents one shipment. This allows grouped sums
    # to produce shipment counts throughout the existing dashboard.
    if "ShipmentCount" not in df.columns:
        df["ShipmentCount"] = 1

    # The SP returns row-level DelayDays. Existing grouped calculations need
    # average-delay and maximum-delay source columns.
    if "AvgDelayDays" not in df.columns and "DelayDays" in df.columns:
        df["AvgDelayDays"] = df["DelayDays"]

    if "MaxDelayDays" not in df.columns and "DelayDays" in df.columns:
        df["MaxDelayDays"] = df["DelayDays"]

    numeric_cols = [
        "YR", "FIN_MONTH", "ShipmentCount", "ActualWeight",
        "ChargeWeight", "Revenue", "AvgDelayDays", "MaxDelayDays",
        "aweight", "DelayDays",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Keep the actual GR/booking date when the stored procedure returns one.
    # Different database/SP versions may expose the same field under different
    # names (for example GRDT, GR_DATE, BookingDt, CNDate, DocketDate, etc.).
    # Detect those names without changing any business calculation.
    if "BusinessDate" not in df.columns:
        compact_date_names = {
            "grdt", "grdate", "grdatetime", "grbookdate", "grbookingdate",
            "bookingdt", "bookingdate", "bookingdatetime", "bkgdate", "bkgdt",
            "cndate", "cndt", "lrdate", "lrdt", "docketdate", "docketdt",
            "shipmentdate", "shipmentdt", "businessdate", "businessdt",
            "entrydate", "entrydt", "docdate", "documentdate",
        }
        detected_date_col = None
        for candidate in df.columns:
            compact = "".join(ch for ch in str(candidate).lower() if ch.isalnum())
            if compact in compact_date_names:
                detected_date_col = candidate
                break

        # As a final safe fallback, consider columns whose name explicitly contains
        # 'date' and accept one only when a meaningful share parses as datetimes.
        if detected_date_col is None:
            for candidate in df.columns:
                name = str(candidate).lower()
                if "date" not in name:
                    continue
                parsed = pd.to_datetime(df[candidate], errors="coerce")
                non_blank = df[candidate].notna().sum()
                if non_blank and parsed.notna().sum() / non_blank >= 0.50:
                    detected_date_col = candidate
                    break

        if detected_date_col is not None:
            df["BusinessDate"] = df[detected_date_col]

    if "BusinessDate" in df.columns:
        df["BusinessDate"] = pd.to_datetime(df["BusinessDate"], errors="coerce", dayfirst=True)

    return df


def get_revenue_conversion(conversion_type: str):
    """Display-only conversion. All business calculations remain in rupees."""
    return (100_000, "Lac") if conversion_type == "Lac" else (10_000_000, "Cr")


def money_display(value: float, conversion_type: str) -> str:
    divisor, unit = get_revenue_conversion(conversion_type)
    return f"Rs.{value / divisor:.2f} {unit}"


def growth_percentage(current: float, previous: float) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def format_delta(value: float) -> str:
    arrow = "up" if value >= 0 else "dn"
    sign  = "+" if value >= 0 else "-"
    return f"{sign}{abs(value):.1f}% vs PY"


def previous_financial_year(fin_year: str, years_back: int = 1) -> str:
    start_year, end_year = fin_year.split("-")
    return f"{int(start_year) - years_back}-{int(end_year) - years_back}"


def get_customer_config(view_type: str) -> dict:
    if view_type == "origin":
        return {"code_col": "cngrcode", "name_col": "Consignor", "label": "Consignor"}
    return {"code_col": "ConsigneeCode", "name_col": "Consignee", "label": "Consignee"}


def apply_filters(
    df: pd.DataFrame,
    zone,
    circle,
    branch,
    quarter,
    month,
    load_type: str,
    customer: str,
    customer_name_col: str,
) -> pd.DataFrame:
    filtered = df.copy()

    def apply_multi(frame, column, selected):
        if column not in frame.columns:
            return frame
        if selected is None or selected == "All" or selected == []:
            return frame
        values = selected if isinstance(selected, (list, tuple, set)) else [selected]
        return frame[frame[column].isin(values)]

    filtered = apply_multi(filtered, "Zone", zone)
    filtered = apply_multi(filtered, "Circle", circle)
    filtered = apply_multi(filtered, "Branch", branch)
    filtered = apply_multi(filtered, "Quarter", quarter)
    filtered = apply_multi(filtered, "Month", month)

    if load_type != "All" and "LoadType" in filtered.columns:
        filtered = filtered[filtered["LoadType"] == load_type]
    if customer != "All" and customer_name_col in filtered.columns:
        filtered = filtered[filtered[customer_name_col] == customer]
    return filtered


# =====================================================
# KPI Card - same component used by Overview Dashboard
# =====================================================
def kpi_card(
    title: str,
    value: str,
    delta: str,
    icon: str,
    color: str = "#2563eb",
    positive: bool | None = None,
) -> None:
    """Render the compact white KPI card used on the Overview dashboard.

    positive controls the delta colour:
    - True  -> green
    - False -> red
    - None  -> muted grey for informational subtitles
    """
    if positive is True:
        delta_color = "#166534"
    elif positive is False:
        delta_color = "#dc2626"
    else:
        delta_color = "#64748b"

    st.markdown(
        f"""
        <div class="kpi-card" style="--accent-color:{color};">
            <div class="kpi-card-top">
                <div class="kpi-title">{title}</div>
                <div class="kpi-icon">{icon}</div>
            </div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-delta" style="color:{delta_color};">{delta}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =====================================================
# Export
# =====================================================
@st.cache_data(show_spinner=False, ttl=600, max_entries=6)
def export_to_excel(
    df: pd.DataFrame,
    customer_summary: pd.DataFrame,
    growth_df: pd.DataFrame,
    monthly_df: pd.DataFrame,
    reactivated_df: pd.DataFrame,
    service_df: pd.DataFrame,
) -> BytesIO:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        sheets = {
            "Raw Summary Data":    df,
            "Customer Summary":    customer_summary,
            "Growth Degrowth":     growth_df,
            "Monthly Summary":     monthly_df,
            "Reactivated Customers": reactivated_df,
            "Service Performance": service_df,
        }
        workbook = writer.book
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#1f2937", "font_color": "white", "border": 1}
        )
        for sheet_name, sheet_df in sheets.items():
            sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
            worksheet = writer.sheets[sheet_name]
            worksheet.freeze_panes(1, 0)
            for col_num, col_name in enumerate(sheet_df.columns):
                worksheet.write(0, col_num, col_name, header_format)
                worksheet.set_column(col_num, col_num, 20)
    output.seek(0)
    return output


# =====================================================
# Data Preparation
# =====================================================
def build_customer_summary(
    df: pd.DataFrame,
    prev_df: pd.DataFrame,
    code_col: str,
    name_col: str,
) -> pd.DataFrame:
    current_summary = (
        df.groupby([code_col, name_col], as_index=False)
        .agg(
            revenue=("Revenue", "sum"),
            shipments=("ShipmentCount", "sum"),
            actual_weight=("ActualWeight", "sum"),
            charge_weight=("ChargeWeight", "sum"),
            avg_delay=("AvgDelayDays", "mean"),
            max_delay=("MaxDelayDays", "max"),
        )
    )
    previous_summary = (
        prev_df.groupby(code_col, as_index=False)
        .agg(prev_revenue=("Revenue", "sum"))
    )
    summary = current_summary.merge(previous_summary, on=code_col, how="left")
    summary["prev_revenue"]   = summary["prev_revenue"].fillna(0)
    summary["revenue_change"] = summary["revenue"] - summary["prev_revenue"]
    summary["growth_%"]       = summary.apply(
        lambda row: growth_percentage(row["revenue"], row["prev_revenue"]), axis=1
    )
    return summary


def build_monthly_summary(df: pd.DataFrame, code_col: str, conversion_type: str) -> pd.DataFrame:
    monthly = (
        df.groupby("FIN_MONTH", as_index=False)
        .agg(
            revenue=("Revenue", "sum"),
            shipments=("ShipmentCount", "sum"),
            customers=(code_col, "nunique"),
        )
        .sort_values("FIN_MONTH")
    )
    divisor, unit = get_revenue_conversion(conversion_type)
    monthly["Business Display"] = (monthly["revenue"] / divisor).round(2)
    monthly["Revenue Unit"] = unit
    return monthly


def build_service_summary(df: pd.DataFrame, code_col: str, name_col: str) -> pd.DataFrame:
    service = (
        df.groupby([code_col, name_col], as_index=False)
        .agg(
            shipments=("ShipmentCount", "sum"),
            avg_delay_days=("AvgDelayDays", "mean"),
            max_delay_days=("MaxDelayDays", "max"),
            revenue=("Revenue", "sum"),
        )
    )
    service["avg_delay_days"] = service["avg_delay_days"].round(2)
    return service


def add_customer_segments(customer_summary: pd.DataFrame) -> pd.DataFrame:
    segmented = customer_summary.copy()
    if segmented.empty:
        segmented["segment"] = ""
        return segmented
    segmented = segmented.sort_values("revenue", ascending=False)
    total_revenue = segmented["revenue"].sum()
    segmented["revenue_share"]     = segmented["revenue"] / total_revenue
    segmented["cum_revenue_share"] = segmented["revenue_share"].cumsum()

    def segment(cum_share: float) -> str:
        if cum_share <= 0.29: return "Champions"
        elif cum_share <= 0.55: return "Loyal"
        elif cum_share <= 0.80: return "Potential"
        elif cum_share <= 0.92: return "At Risk"
        else: return "Lost"

    segmented["segment"] = segmented["cum_revenue_share"].apply(segment)
    return segmented


# =====================================================
# UI Sections
# =====================================================
def render_dashboard_header():
    """Render the compact Overview-style header and return content/export placeholders."""
    with st.container(border=True):
        header_left, header_right = st.columns(
            [7, 1],
            gap="small",
            vertical_alignment="center",
        )

        with header_left:
            header_content_placeholder = st.empty()
            with header_content_placeholder:
                st.markdown(
                    """
                    <div class="dashboard-header" style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
                        <div class="dashboard-title" style="white-space:nowrap;">Customer Analysis</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with header_right:
            export_placeholder = st.empty()

    return header_content_placeholder, export_placeholder


def _checkbox_slicer(label, options, key, locked_values=None, searchable=False):
    options = [x for x in options if pd.notna(x)]
    options = list(dict.fromkeys(options))

    st.markdown(
        f'<div class="checkbox-slicer-label">{label}</div>',
        unsafe_allow_html=True,
    )

    if locked_values:
        locked_values = [x for x in locked_values if x is not None]
        summary = str(locked_values[0]) if len(locked_values) == 1 else f"{len(locked_values)} selected"
        with st.popover(summary, use_container_width=True):
            for value in locked_values:
                st.checkbox(str(value), value=True, disabled=True, key=f"{key}__locked__{value}")
        return locked_values

    def state_key(value):
        return f"{key}__item__{str(value)}"

    if searchable:
        selection_key = f"{key}__instant_selected"
        legacy_selected = [value for value in options if st.session_state.get(state_key(value), False)]
        if selection_key not in st.session_state:
            st.session_state[selection_key] = legacy_selected
        else:
            st.session_state[selection_key] = [
                value for value in st.session_state.get(selection_key, []) if value in options
            ]

        selected_before = st.session_state.get(selection_key, [])
        summary = "All" if not selected_before else (str(selected_before[0]) if len(selected_before) == 1 else f"{len(selected_before)} selected")

        with st.popover(summary, use_container_width=True):
            action_cols = st.columns(2, gap="small")
            with action_cols[0]:
                if st.button("Select all", key=f"{key}__select_all", use_container_width=False):
                    st.session_state[selection_key] = list(options)
                    st.rerun()
            with action_cols[1]:
                if st.button("Clear", key=f"{key}__clear", use_container_width=False):
                    st.session_state[selection_key] = []
                    st.rerun()
            selected_values = st.multiselect(
                f"Search {str(label).replace('◎', '').replace('⌂', '').strip()}",
                options=options,
                key=selection_key,
                placeholder="Type to search...",
                label_visibility="collapsed",
            )
            if not options:
                st.caption("No values available")

        selected_set = set(selected_values)
        for value in options:
            st.session_state[state_key(value)] = value in selected_set
        return selected_values

    selected_before = [value for value in options if st.session_state.get(state_key(value), False)]
    summary = "All" if not selected_before else (str(selected_before[0]) if len(selected_before) == 1 else f"{len(selected_before)} selected")

    with st.popover(summary, use_container_width=True):
        action_cols = st.columns(2, gap="small")
        with action_cols[0]:
            if st.button("Select all", key=f"{key}__select_all", use_container_width=False):
                for value in options:
                    st.session_state[state_key(value)] = True
                st.rerun()
        with action_cols[1]:
            if st.button("Clear", key=f"{key}__clear", use_container_width=False):
                for value in options:
                    st.session_state[state_key(value)] = False
                st.rerun()
        if not options:
            st.caption("No values available")
        else:
            for value in options:
                st.checkbox(str(value), key=state_key(value))

    return [value for value in options if st.session_state.get(state_key(value), False)]


def render_filter_row_start():
    """Create the Overview-style single filter row with View Type first, then FY."""
    filter_columns = st.columns(
        [1.00, 1.10, 0.82, 0.92, 1.00, 0.72, 0.82, 0.92, 1.25, 0.82],
        gap="small",
    )

    with filter_columns[0]:
        view_type = st.selectbox(
            "⇄ View Type",
            ["origin", "destination"],
            format_func=lambda x: "Origin" if x == "origin" else "Destination",
            key="customer_view_type",
        )

    with filter_columns[1]:
        fin_year = st.selectbox(
            "◷ Financial Year",
            FINANCIAL_YEARS,
            key="customer_financial_year",
        )

    return filter_columns, fin_year, view_type


def render_data_filters(
    df: pd.DataFrame,
    customer_label: str,
    customer_name_col: str,
    filter_columns,
):
    """Render Overview-style role-aware cascading filters.

    Hierarchy:
        Zone -> Circle -> Branch -> Quarter -> Month -> Load Type -> Customer

    Role behaviour comes from ``st.session_state["data_scope"]``:
        {}                          -> unrestricted
        {"zone": "..."}           -> Zone locked, Circle/Branch cascade below it
        {"circle": "..."}         -> Zone + Circle locked, Branch cascades below it
        {"branch": "..."}         -> Zone + Circle + Branch all locked
    """
    data_scope = st.session_state.get("data_scope", {}) or {}
    locked_zone = data_scope.get("zone")
    locked_circle = data_scope.get("circle")
    locked_branch = data_scope.get("branch")

    def _canon(value):
        """Normalize role values for safe case/space-insensitive matching."""
        if value is None:
            return ""
        return " ".join(str(value).strip().split()).casefold()

    def _match(frame: pd.DataFrame, column: str, value):
        if frame is None or frame.empty or column not in frame.columns or value in (None, ""):
            return frame.iloc[0:0] if frame is not None else pd.DataFrame()
        target = _canon(value)
        normalized = (
            frame[column]
            .fillna("")
            .astype(str)
            .map(lambda x: " ".join(x.strip().split()).casefold())
        )
        return frame[normalized.eq(target)]

    # Resolve the exact hierarchy names from the current FY data.  This avoids
    # case/spacing differences between login rights and database values.
    if locked_branch:
        role_row = _match(df, "Branch", locked_branch)
        if not role_row.empty:
            locked_branch = role_row["Branch"].iloc[0]
            if "Circle" in role_row.columns:
                locked_circle = role_row["Circle"].iloc[0]
            if "Zone" in role_row.columns:
                locked_zone = role_row["Zone"].iloc[0]
    elif locked_circle:
        role_row = _match(df, "Circle", locked_circle)
        if not role_row.empty:
            locked_circle = role_row["Circle"].iloc[0]
            if "Zone" in role_row.columns:
                locked_zone = role_row["Zone"].iloc[0]
    elif locked_zone:
        role_row = _match(df, "Zone", locked_zone)
        if not role_row.empty:
            locked_zone = role_row["Zone"].iloc[0]

    f1, f2, f3, f4, f5, f6, f7, f8 = filter_columns[2:]
    filter_source_df = df.copy()

    # ------------------------------------------------------------------
    # ZONE
    # ------------------------------------------------------------------
    with f1:
        zone_options = (
            sorted(filter_source_df["Zone"].dropna().astype(str).str.strip().unique().tolist(), key=str.casefold)
            if "Zone" in filter_source_df.columns else []
        )
        selected_zones = _checkbox_slicer(
            "◉ Zone",
            zone_options,
            key="customer_zone_slicer",
            locked_values=[locked_zone] if locked_zone else None,
        )

    zone_source_df = filter_source_df.copy()
    if selected_zones and "Zone" in zone_source_df.columns:
        zone_source_df = zone_source_df[zone_source_df["Zone"].isin(selected_zones)]

    # ------------------------------------------------------------------
    # CIRCLE - options only from selected/locked Zone
    # ------------------------------------------------------------------
    with f2:
        circle_options = (
            sorted(zone_source_df["Circle"].dropna().astype(str).str.strip().unique().tolist(), key=str.casefold)
            if "Circle" in zone_source_df.columns else []
        )
        selected_circles = _checkbox_slicer(
            "◎ Circle",
            circle_options,
            key="customer_circle_slicer",
            locked_values=[locked_circle] if locked_circle else None,
            searchable=True,
        )

    circle_source_df = zone_source_df.copy()
    if selected_circles and "Circle" in circle_source_df.columns:
        circle_source_df = circle_source_df[circle_source_df["Circle"].isin(selected_circles)]

    # ------------------------------------------------------------------
    # BRANCH - options only from selected/locked Zone + Circle
    # ------------------------------------------------------------------
    with f3:
        branch_options = (
            sorted(circle_source_df["Branch"].dropna().astype(str).str.strip().unique().tolist(), key=str.casefold)
            if "Branch" in circle_source_df.columns else []
        )
        selected_branches = _checkbox_slicer(
            "⌂ Branch",
            branch_options,
            key="customer_branch_slicer",
            locked_values=[locked_branch] if locked_branch else None,
            searchable=True,
        )

    branch_source_df = circle_source_df.copy()
    if selected_branches and "Branch" in branch_source_df.columns:
        branch_source_df = branch_source_df[branch_source_df["Branch"].isin(selected_branches)]

    # ------------------------------------------------------------------
    # QUARTER - options only from selected hierarchy
    # ------------------------------------------------------------------
    with f4:
        available_quarters = [
            q for q in QUARTER_ORDER
            if "Quarter" in branch_source_df.columns
            and q in branch_source_df["Quarter"].dropna().unique().tolist()
        ]
        selected_quarters = _checkbox_slicer(
            "▦ Quarter",
            available_quarters,
            key="customer_quarter_slicer",
        )

    quarter_source_df = branch_source_df.copy()
    if selected_quarters and "Quarter" in quarter_source_df.columns:
        quarter_source_df = quarter_source_df[quarter_source_df["Quarter"].isin(selected_quarters)]

    # ------------------------------------------------------------------
    # MONTH - options only from selected hierarchy + Quarter
    # ------------------------------------------------------------------
    with f5:
        available_months = [
            m for m in MONTH_ORDER
            if "Month" in quarter_source_df.columns
            and m in quarter_source_df["Month"].dropna().unique().tolist()
        ]
        selected_months = _checkbox_slicer(
            "▣ Month",
            available_months,
            key="customer_month_slicer",
        )

    selection_df = quarter_source_df.copy()
    if selected_months and "Month" in selection_df.columns:
        selection_df = selection_df[selection_df["Month"].isin(selected_months)]

    # ------------------------------------------------------------------
    # LOAD TYPE / CUSTOMER / CONVERSION
    # ------------------------------------------------------------------
    with f6:
        loadtype_values = (
            sorted(selection_df["LoadType"].dropna().astype(str).str.strip().unique().tolist(), key=str.casefold)
            if "LoadType" in selection_df.columns else []
        )
        loadtype_list = ["All"] + loadtype_values
        current_load = st.session_state.get("customer_loadtype", "All")
        if current_load not in loadtype_list:
            st.session_state["customer_loadtype"] = "All"
        load_type = st.selectbox("▤ Load Type", loadtype_list, key="customer_loadtype")

    loadtype_df = (
        selection_df
        if load_type == "All" or "LoadType" not in selection_df.columns
        else selection_df[selection_df["LoadType"] == load_type]
    )

    with f7:
        customer_values = (
            sorted(loadtype_df[customer_name_col].dropna().astype(str).str.strip().unique().tolist(), key=str.casefold)
            if customer_name_col in loadtype_df.columns else []
        )
        customer_list = ["All"] + customer_values
        current_customer = st.session_state.get("customer_name_filter", "All")
        if current_customer not in customer_list:
            st.session_state["customer_name_filter"] = "All"
        customer = st.selectbox(
            f"👤 {customer_label}",
            customer_list,
            key="customer_name_filter",
        )

    with f8:
        conversion_type = st.selectbox(
            "₹ Conversion",
            ["Crore", "Lac"],
            key="customer_conversion_type",
        )

    return (
        selected_zones,
        selected_circles,
        selected_branches,
        selected_quarters,
        selected_months,
        load_type,
        customer,
        conversion_type,
    )


# =====================================================
# KPI Row  — 8 equal columns
# =====================================================
def render_kpis(metrics: dict, customer_label: str, conversion_type: str) -> None:
    """Render all Customer Analysis KPIs using the Overview dashboard card style."""
    cols = st.columns(7, gap="small")

    cards = [
        {
            "title": f"Active {customer_label}s",
            "value": f"{metrics['active_customers']:,}",
            "delta": f"{format_delta(metrics['active_growth'])}",
            "icon": "👥", "color": "#2563eb",
            "positive": metrics["active_growth"] >= 0,
        },
        {
            "title": f"New {customer_label}s",
            "value": f"{metrics['new_customers']:,}",
            "delta": "Current FY vs Previous FY",
            "icon": "🆕", "color": "#16a34a", "positive": None,
        },
        {
            "title": f"Lost {customer_label}s",
            "value": f"{metrics['lost_customers']:,}",
            "delta": "Previous FY not active now",
            "icon": "❌", "color": "#dc2626",
            "positive": False if metrics["lost_customers"] > 0 else None,
        },
        {
            "title": "Reactivated Customers",
            "value": f"{metrics['reactivated_customers']:,}",
            "delta": "Returned after inactive FY",
            "icon": "🔄", "color": "#16a34a",
            "positive": True if metrics["reactivated_customers"] > 0 else None,
        },
        {
            "title": "Total Business",
            "value": money_display(metrics["total_revenue"], conversion_type),
            "delta": f"{format_delta(metrics['revenue_growth'])}",
            "icon": "₹", "color": "#2563eb",
            "positive": metrics["revenue_growth"] >= 0,
        },
        {
            "title": f"At Risk {customer_label}s",
            "value": f"{metrics['at_risk_customers']:,}",
            "delta": "Business dropped above 25%",
            "icon": "⚠️", "color": "#d97706",
            "positive": False if metrics["at_risk_customers"] > 0 else None,
        },
        {
            "title": "Current Yield",
            "value": f"₹{metrics['current_yield']:.2f} /Kg",
            "delta": "Business / Charge Weight",
            "icon": "⚡", "color": "#2563eb", "positive": None,
        },
    ]

    for col, card in zip(cols, cards):
        with col:
            kpi_card(**card)



def render_overview_tab(
    customer_summary: pd.DataFrame,
    monthly: pd.DataFrame,
    df: pd.DataFrame,
    code_col: str,
    name_col: str,
    customer_label: str,
    prev_df,
    lost_customer_codes,
    conversion_type: str,
) -> None:
    # --- Three equal chart columns ---
    c1, c2, c3 = st.columns(3, gap="small")

    with c1:
        with st.container(border=True):
            _, revenue_unit = get_revenue_conversion(conversion_type)
            fig = px.bar(
                monthly, x="FIN_MONTH", y="Business Display",
                text="Business Display", title=f"Month-wise Business ({revenue_unit})",
            )
            fig.update_traces(texttemplate=f"Rs.%{{text:.2f}} {revenue_unit}", textposition="outside", marker_color="#60a5fa", marker_line_color="#2563eb", marker_line_width=1)
            fig.update_yaxes(title=f"Business ({revenue_unit})")
            fig.update_layout(height=330, margin=dict(t=45, b=20), plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with c2:
        with st.container(border=True):
            title_col, logic_col = st.columns([4.2, 1.2], gap="small", vertical_alignment="center")
            with title_col:
                st.markdown(
                    "<div style='font-size:16px;font-weight:800;color:#0f2744;margin:1px 0 3px 0;'>Business Concentration</div>",
                    unsafe_allow_html=True,
                )
            with logic_col:
                with st.popover("ⓘ Metric Logic", use_container_width=True):
                    st.markdown(
                        "**What it shows**  \n"
                        "How much of total selected business is contributed by the highest-value customers.\n\n"
                        "**Calculation**  \n"
                        "`Top-N Concentration % = Top-N Customer Business ÷ Total Business × 100`\n\n"
                        "Customers are ranked by **CY Business**, highest to lowest. "
                        "Top 20 includes Top 10, Top 50 includes Top 20, and Top 100 includes Top 50.\n\n"
                        "**Example**  \n"
                        "If total business is **₹100 Cr** and the Top 10 customers together contribute **₹8.70 Cr**, "
                        "then **Top 10 Concentration = 8.70 ÷ 100 × 100 = 8.7%**.  \n"
                        "Management meaning: **8.7% of business comes from the 10 largest customers** and the remaining **91.3%** comes from other customers."
                    )

            revenue_rank = customer_summary.sort_values("revenue", ascending=False)
            total_revenue = revenue_rank["revenue"].sum()
            rows = []
            for lbl, top_n in [("Top 10", 10), ("Top 20", 20), ("Top 50", 50), ("Top 100", 100)]:
                top_rev = revenue_rank.head(top_n)["revenue"].sum()
                pct = (top_rev / total_revenue * 100) if total_revenue else 0
                rows.append({"Customer Group": lbl, "% of Total Business": round(pct, 1)})
            concentration_df = pd.DataFrame(rows)
            fig = px.bar(
                concentration_df,
                x="% of Total Business", y="Customer Group",
                orientation="h", text="% of Total Business",
            )
            concentration_colors = ["#2563EB", "#06B6D4", "#8B5CF6", "#F59E0B"]
            fig.update_traces(
                texttemplate="%{text}%",
                textposition="outside",
                marker_color=concentration_colors,
            )
            fig.update_layout(
                xaxis_title="% of Total Business", yaxis_title="",
                height=300, margin=dict(t=10, b=20), plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with c3:
        with st.container(border=True):
            title_col, logic_col = st.columns([4.2, 1.35], gap="small", vertical_alignment="center")
            with title_col:
                st.markdown(
                    f"<div style='font-size:16px;font-weight:800;color:#0f2744;margin:1px 0 3px 0;'>{html.escape(customer_label)} Segmentation</div>",
                    unsafe_allow_html=True,
                )
            with logic_col:
                with st.popover("ⓘ Segmentation Logic", use_container_width=True):
                    st.markdown(
                        "**Customer value segmentation by cumulative CY Business contribution**\n\n"
                        "- **Champions:** first 29% of cumulative business\n"
                        "- **Loyal:** above 29% up to 55%\n"
                        "- **Potential:** above 55% up to 80%\n"
                        "- **At Risk:** above 80% up to 92%\n"
                        "- **Long Tail:** above 92%\n\n"
                        "The donut displays the **number of customers** in each segment and their **share of total customers**. "
                        "This is a value-contribution segmentation; it is separate from the dashboard's actual Lost Customer and At Risk KPI logic.\n\n"
                        "**Example**  \n"
                        "Assume total CY Business is **₹100 Cr** and customers are ranked from highest to lowest business. "
                        "Customers contributing the first cumulative **₹29 Cr** are **Champions**. "
                        "The customers taking cumulative business from **₹29 Cr to ₹55 Cr** are **Loyal**; **₹55–80 Cr** are **Potential**; "
                        "**₹80–92 Cr** are **At Risk**; and customers contributing the remaining **₹8 Cr (92–100%)** are **Long Tail**.  \n"
                        "The donut then shows how many customers fall into each value band and their percentage of total customers."
                    )

            segmented = add_customer_segments(customer_summary)
            display_segment_map = {"Lost": "Long Tail"}
            segment_order = ["Champions", "Loyal", "Potential", "At Risk", "Long Tail"]
            segment_colors = {
                "Champions": "#14946b", "Loyal": "#0f6ec7", "Potential": "#5ab0e8",
                "At Risk": "#f59e0b", "Long Tail": "#ef4444",
            }
            segmented["segment_display"] = segmented["segment"].replace(display_segment_map)
            segment_df = (
                segmented.groupby("segment_display", as_index=False)
                .agg(Customers=("segment_display", "size"), Business=("revenue", "sum"))
                .rename(columns={"segment_display": "segment"})
            )
            total_segment_customers = int(segment_df["Customers"].sum())
            segment_df["Customer Share %"] = (
                segment_df["Customers"] / total_segment_customers * 100
            ).round(1) if total_segment_customers else 0
            segment_df["Legend Label"] = segment_df.apply(
                lambda r: f"{r['segment']} ({int(r['Customers']):,} | {r['Customer Share %']:.1f}%)", axis=1
            )
            segment_df["segment"] = pd.Categorical(segment_df["segment"], categories=segment_order, ordered=True)
            segment_df = segment_df.sort_values("segment")
            fig = px.pie(
                segment_df, names="Legend Label", values="Customers", hole=0.55,
                color="segment", color_discrete_map=segment_colors,
            )
            fig.update_traces(
                texttemplate="%{value:,}<br>%{percent:.1%}",
                textposition="inside",
                hovertemplate="%{label}<br>Customers: %{value:,}<br>Share: %{percent}<extra></extra>",
            )
            fig.update_layout(
                height=300, margin=dict(t=10, b=5),
                annotations=[dict(
                    text=f"Total<br>{total_segment_customers:,}",
                    x=0.5, y=0.5, font_size=12, showarrow=False,
                )],
                legend=dict(orientation="v", y=0.95, yanchor="top", x=1.0, xanchor="left", font=dict(size=10)),
                legend_title_text="",
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div class='insight-section-spacer'></div>", unsafe_allow_html=True)

    # --- Replace three large tables with three compact horizontal visuals ---
    top_growing = customer_summary[
        (customer_summary["prev_revenue"] > 0) &
        (customer_summary["revenue"] > customer_summary["prev_revenue"])
    ].copy().sort_values("growth_%", ascending=False)

    top_degrowing = customer_summary[
        (customer_summary["prev_revenue"] > 0) &
        (customer_summary["revenue"] < customer_summary["prev_revenue"]) &
        (customer_summary["revenue"] > 0)
    ].copy().sort_values("growth_%", ascending=True)

    def _build_lost_customer_summary(inactive_months: int) -> pd.DataFrame:
        """Customers with no business in the most recent N fiscal months.

        FIN_MONTH is the source of truth (1=Apr ... 12=Mar). Previous-FY rows
        are placed immediately before current-FY rows on one continuous fiscal
        month axis so the 3/6/9/12-month inactivity test works across FY boundaries.
        """
        history_parts = []

        if not prev_df.empty:
            py = prev_df.copy()
            py["__abs_month"] = pd.to_numeric(py["FIN_MONTH"], errors="coerce").fillna(0).astype(int) - 12
            history_parts.append(py)

        if not df.empty:
            cy = df.copy()
            cy["__abs_month"] = pd.to_numeric(cy["FIN_MONTH"], errors="coerce").fillna(0).astype(int)
            history_parts.append(cy)

        if not history_parts:
            return pd.DataFrame()

        history = pd.concat(history_parts, ignore_index=True, sort=False)
        history = history[history["__abs_month"].notna()].copy()
        if history.empty:
            return pd.DataFrame()

        current_months = pd.to_numeric(df.get("FIN_MONTH", pd.Series(dtype=float)), errors="coerce").dropna()
        as_of_month = int(current_months.max()) if not current_months.empty else 12
        cutoff_month = as_of_month - int(inactive_months)

        # Pick the latest actual business row for each customer. When the stored
        # procedure exposes a GR/booking date, use it to resolve the exact date
        # inside the latest fiscal month.
        sort_cols = ["__abs_month"]
        if "BusinessDate" in history.columns:
            sort_cols.append("BusinessDate")
        last_rows = history.sort_values(sort_cols).groupby(code_col, as_index=False).tail(1)
        keep_cols = [code_col, name_col, "__abs_month", "FIN_MONTH", "Branch", "Zone"]
        if "BusinessDate" in last_rows.columns:
            keep_cols.append("BusinessDate")
        last_rows = last_rows[keep_cols].rename(columns={"FIN_MONTH": "last_business_ref"})
        last_rows = last_rows[last_rows["__abs_month"] <= cutoff_month].copy()
        if last_rows.empty:
            return pd.DataFrame()

        lost_codes = set(last_rows[code_col].dropna().tolist())
        business_summary = (
            history[history[code_col].isin(lost_codes)]
            .groupby(code_col, as_index=False)
            .agg(lost_revenue=("Revenue", "sum"))
        )

        return (
            last_rows.merge(business_summary, on=code_col, how="left")
            .sort_values("lost_revenue", ascending=False)
            .head(10)
        )

    divisor, unit = get_revenue_conversion(conversion_type)

    def _fmt_business(value: float) -> str:
        return f"₹{value / divisor:.2f} {unit}"

    def _render_growth_detail_table(
        source_df: pd.DataFrame,
        title: str,
        positive: bool,
        empty_message: str,
        top_n: int,
    ) -> None:
        if title:
            st.markdown(f"<div class='section-header'>{html.escape(title)}</div>", unsafe_allow_html=True)
        if source_df.empty:
            st.info(empty_message)
            return

        table_df = source_df.copy().head(top_n)
        max_pct = max(float(table_df["growth_%"].abs().max()), 1.0)
        rows_html = []

        for _, row in table_df.iterrows():
            customer_name = html.escape(str(row.get(name_col, "")))
            ly = float(row.get("prev_revenue", 0) or 0)
            cy = float(row.get("revenue", 0) or 0)
            pct = float(row.get("growth_%", 0) or 0)
            delta = cy - ly
            shipments = int(round(float(row.get("shipments", 0) or 0)))
            bar_width = max(5.0, min(abs(pct) / max_pct * 100.0, 100.0))
            accent = "#16a34a" if positive else "#ef4444"
            pct_label = f"{abs(pct):.1f}%"
            delta_label = _fmt_business(abs(delta))

            rows_html.append(
                f'<div class="customer-rank-row">'
                f'<div class="customer-name-cell">{customer_name}</div>'
                f'<div class="customer-num-cell">{_fmt_business(ly)}</div>'
                f'<div class="customer-num-cell">{_fmt_business(cy)}</div>'
                f'<div class="customer-growth-cell">'
                f'<div class="customer-growth-track">'
                f'<div class="customer-growth-fill" style="width:{bar_width:.1f}%;background:{accent};"></div>'
                f'</div>'
                f'<span style="color:{accent};">{pct_label}</span>'
                f'</div>'
                f'<div class="customer-num-cell" style="color:{accent};font-weight:800;">{delta_label}</div>'
                f'<div class="customer-num-cell">{shipments:,}</div>'
                f'</div>'
            )

        change_header = "Growth %" if positive else "Decline %"
        amount_header = "Growth (₹)" if positive else "Loss (₹)"
        table_html = (
            f'<div class="customer-rank-table">'
            f'<div class="customer-rank-head">'
            f'<div>{html.escape(customer_label)}</div>'
            f'<div>LY Business</div>'
            f'<div>CY Business</div>'
            f'<div>{change_header}</div>'
            f'<div>{amount_header}</div>'
            f'<div>CY Shipments</div>'
            f'</div>'
            f'{"".join(rows_html)}'
            f'</div>'
        )
        st.markdown(table_html, unsafe_allow_html=True)

    # Growing and de-growing details: table-led design instead of charts.
    g1, g2 = st.columns(2, gap="small", vertical_alignment="top")
    with g1:
        with st.container(border=True):
            grow_title_col, grow_selector_col = st.columns(
                [4.2, 1.0], gap="small", vertical_alignment="center"
            )
            with grow_selector_col:
                grow_top_n = st.selectbox(
                    "Growing customers to display",
                    TOP_N_OPTIONS,
                    index=0,
                    format_func=lambda value: f"Top {value}",
                    key="customer_growth_top_n",
                    label_visibility="collapsed",
                )
            with grow_title_col:
                st.markdown(
                    f"<div style='font-size:16px;font-weight:800;color:#0f2744;margin:1px 0 7px 0;'>TOP {grow_top_n} GROWING {customer_label.upper()}S <span style='font-size:12px;font-weight:600;'>(By Growth %)</span></div>",
                    unsafe_allow_html=True,
                )
            _render_growth_detail_table(
                top_growing,
                "",
                True,
                "No growing customers for selected filters.",
                grow_top_n,
            )

    with g2:
        with st.container(border=True):
            degrow_title_col, degrow_selector_col = st.columns(
                [4.2, 1.0], gap="small", vertical_alignment="center"
            )
            with degrow_selector_col:
                degrow_top_n = st.selectbox(
                    "De-growing customers to display",
                    TOP_N_OPTIONS,
                    index=0,
                    format_func=lambda value: f"Top {value}",
                    key="customer_degrowth_top_n",
                    label_visibility="collapsed",
                )
            with degrow_title_col:
                st.markdown(
                    f"<div style='font-size:16px;font-weight:800;color:#0f2744;margin:1px 0 7px 0;'>TOP {degrow_top_n} DE-GROWING {customer_label.upper()}S <span style='font-size:12px;font-weight:600;'>(By Decline %)</span></div>",
                    unsafe_allow_html=True,
                )
            _render_growth_detail_table(
                top_degrowing,
                "",
                False,
                "No de-growing customers for selected filters.",
                degrow_top_n,
            )

    dashboard_spacer()

    # Top customers: compact CY vs LY ranked table.
    top_left, lost_right = st.columns([1.65, 1], gap="small", vertical_alignment="top")
    with top_left:
        with st.container(border=True):
            top_title_col, top_selector_col = st.columns(
                [4.2, 1.0], gap="small", vertical_alignment="center"
            )
            with top_selector_col:
                top_customer_n = st.selectbox(
                    "Top customers to display",
                    TOP_N_OPTIONS,
                    index=0,
                    format_func=lambda value: f"Top {value}",
                    key=f"top_customers_cy_ly_{customer_label.lower()}",
                    label_visibility="collapsed",
                )
            with top_title_col:
                st.markdown(
                    f"<div style='font-size:16px;font-weight:800;color:#0f2744;margin:1px 0 7px 0;'>TOP {top_customer_n} {customer_label.upper()}S <span style='font-size:12px;font-weight:600;'>(CY vs LY)</span></div>",
                    unsafe_allow_html=True,
                )

            top_customer_df = (
                customer_summary.copy()
                .sort_values("revenue", ascending=False)
                .head(top_customer_n)
            )

            if top_customer_df.empty:
                st.info(f"No {customer_label.lower()} business data available for selected filters.")
            else:
                max_cy = max(float(top_customer_df["revenue"].max()), 1.0)
                top_rows_html = []
                for _, row in top_customer_df.iterrows():
                    customer_name = html.escape(str(row.get(name_col, "")))
                    cy = float(row.get("revenue", 0) or 0)
                    ly = float(row.get("prev_revenue", 0) or 0)
                    growth = float(row.get("growth_%", 0) or 0)
                    scale_width = max(2.0, min(cy / max_cy * 100.0, 100.0)) if cy > 0 else 0.0
                    growth_color = "#16a34a" if growth >= 0 else "#ef4444"
                    growth_arrow = "▲" if growth >= 0 else "▼"

                    top_rows_html.append(
                        f'<div class="top-customer-row">'
                        f'<div class="customer-name-cell">{customer_name}</div>'
                        f'<div class="top-customer-scale"><div class="top-customer-scale-fill" style="width:{scale_width:.1f}%;"></div></div>'
                        f'<div class="customer-num-cell">{_fmt_business(cy)}</div>'
                        f'<div class="customer-num-cell" style="color:#64748b;">{_fmt_business(ly)}</div>'
                        f'<div class="customer-num-cell" style="color:{growth_color};font-weight:850;">{growth_arrow} {abs(growth):.1f}%</div>'
                        f'</div>'
                    )

                top_table_html = (
                    f'<div class="top-customer-table">'
                    f'<div class="top-customer-head">'
                    f'<div>{html.escape(customer_label)}</div>'
                    f'<div>Scale</div>'
                    f'<div>CY Business</div>'
                    f'<div>LY Business</div>'
                    f'<div>Growth %</div>'
                    f'</div>'
                    f'{"".join(top_rows_html)}'
                    f'</div>'
                )
                st.markdown(top_table_html, unsafe_allow_html=True)

    with lost_right:
        with st.container(border=True):
            lost_title_col, lost_period_col = st.columns([4.2, 1.35], gap="small", vertical_alignment="center")
            with lost_title_col:
                st.markdown(
                    f"<div style='font-size:16px;font-weight:800;color:#0f2744;margin:1px 0 7px 0;'>LOST {customer_label.upper()}S</div>",
                    unsafe_allow_html=True,
                )
            with lost_period_col:
                lost_period_label = st.selectbox(
                    "Lost customer period",
                    ["Last 3 Months", "Last 6 Months", "Last 9 Months", "Last 12 Months"],
                    index=0,
                    key=f"lost_customer_period_{customer_label.lower()}",
                    label_visibility="collapsed",
                )

            inactive_months = int(lost_period_label.split()[1])
            lost_summary = _build_lost_customer_summary(inactive_months)

            st.caption(f"Customers with no business in the most recent {inactive_months} months.")

            if lost_summary.empty:
                st.info(f"No customers inactive for the last {inactive_months} months under the selected filters.")
            else:
                if "BusinessDate" not in lost_summary.columns or lost_summary["BusinessDate"].isna().all():
                    st.caption(
                        "Last Business Date is not present in the stored-procedure output. "
                        "The dashboard will show it automatically once a GR/booking date column is returned."
                    )
                lost_rows_html = []
                for _, row in lost_summary.iterrows():
                    customer_name = html.escape(str(row.get(name_col, "")))
                    business_value = _fmt_business(float(row.get("lost_revenue", 0) or 0))
                    last_business_date = row.get("BusinessDate")
                    if pd.notna(last_business_date):
                        try:
                            last_ref_text = pd.to_datetime(last_business_date).strftime("%d-%b-%Y")
                        except Exception:
                            last_ref_text = "-"
                    else:
                        # Exact date is intentionally not fabricated from FIN_MONTH.
                        # If the source procedure does not return a date, show a dash.
                        last_ref_text = "-"

                    lost_rows_html.append(
                        f'<div class="lost-customer-row">'
                        f'<div class="customer-name-cell">{customer_name}</div>'
                        f'<div class="lost-customer-date">{html.escape(last_ref_text)}</div>'
                        f'<div class="customer-num-cell">{business_value}</div>'
                        f'</div>'
                    )

                lost_table_html = (
                    f'<div class="lost-customer-table">'
                    f'<div class="lost-customer-head">'
                    f'<div>{html.escape(customer_label)}</div>'
                    f'<div>Last Business Date</div>'
                    f'<div>Previous Business</div>'
                    f'</div>'
                    f'{"".join(lost_rows_html)}'
                    f'</div>'
                )
                st.markdown(lost_table_html, unsafe_allow_html=True)

    dashboard_spacer()

    # Regular / consistent customers: customers with business in every month of
    # the selected trailing period. This is an additional insight only and does
    # not alter any existing customer calculations.
    with st.container(border=True):
        regular_title_col, regular_period_col, regular_top_col = st.columns(
            [5.0, 1.15, 1.0], gap="small", vertical_alignment="center"
        )
        with regular_title_col:
            st.markdown(
                f"<div style='font-size:16px;font-weight:800;color:#0f2744;margin:1px 0 1px 0;'>REGULAR (CONSISTENT) {customer_label.upper()}S</div>"
                f"<div style='font-size:11px;color:#64748b;margin-bottom:7px;'>Customers who have given business in every month of the selected trailing period.</div>",
                unsafe_allow_html=True,
            )
        with regular_period_col:
            regular_period = st.selectbox(
                "Consistency period",
                [3, 6, 9, 12],
                index=3,
                format_func=lambda value: f"Last {value} Months",
                key=f"regular_customer_period_{customer_label.lower()}",
                label_visibility="collapsed",
            )
        with regular_top_col:
            regular_top_n = st.selectbox(
                "Regular customers to display",
                TOP_N_OPTIONS,
                index=0,
                format_func=lambda value: f"Top {value}",
                key=f"regular_customer_top_n_{customer_label.lower()}",
                label_visibility="collapsed",
            )

        history_parts = []
        if not prev_df.empty:
            py = prev_df.copy()
            py["__abs_month"] = pd.to_numeric(py["FIN_MONTH"], errors="coerce").fillna(0).astype(int) - 12
            history_parts.append(py)
        if not df.empty:
            cy = df.copy()
            cy["__abs_month"] = pd.to_numeric(cy["FIN_MONTH"], errors="coerce").fillna(0).astype(int)
            history_parts.append(cy)

        if not history_parts:
            st.info(f"No {customer_label.lower()} history available for consistency analysis.")
        else:
            regular_history = pd.concat(history_parts, ignore_index=True, sort=False)
            current_months = pd.to_numeric(df.get("FIN_MONTH", pd.Series(dtype=float)), errors="coerce").dropna()
            as_of_month = int(current_months.max()) if not current_months.empty else 12
            period_months = list(range(as_of_month - regular_period + 1, as_of_month + 1))
            period_history = regular_history[regular_history["__abs_month"].isin(period_months)].copy()

            if period_history.empty:
                st.info("No business data available for the selected consistency period.")
            else:
                monthly_customer = (
                    period_history.groupby([code_col, name_col, "__abs_month"], as_index=False)
                    .agg(month_business=("Revenue", "sum"))
                )
                activity = (
                    monthly_customer[monthly_customer["month_business"] > 0]
                    .groupby([code_col, name_col], as_index=False)
                    .agg(months_active=("__abs_month", "nunique"), total_business=("month_business", "sum"))
                )
                regular_customers = activity[activity["months_active"] == regular_period].copy()

                if regular_customers.empty:
                    st.info(
                        f"No {customer_label.lower()} has business in all {regular_period} months under the selected filters."
                    )
                else:
                    regular_customers["avg_month_business"] = regular_customers["total_business"] / regular_period
                    growth_lookup = customer_summary[[code_col, "growth_%"]].drop_duplicates(code_col)
                    regular_customers = regular_customers.merge(growth_lookup, on=code_col, how="left")
                    regular_customers["growth_%"] = regular_customers["growth_%"].fillna(0)
                    regular_customers = regular_customers.sort_values("total_business", ascending=False).head(regular_top_n)

                    pivot = monthly_customer.pivot_table(
                        index=[code_col, name_col],
                        columns="__abs_month",
                        values="month_business",
                        aggfunc="sum",
                        fill_value=0,
                    )
                    pivot = pivot.reset_index()
                    regular_customers = regular_customers.merge(pivot, on=[code_col, name_col], how="left")

                    def _month_label(abs_month: int) -> str:
                        fin_month = ((int(abs_month) - 1) % 12) + 1
                        return MONTH_MAP.get(fin_month, str(fin_month))

                    month_labels = [_month_label(m) for m in period_months]
                    month_cols_css = " ".join(["0.68fr"] * regular_period)
                    grid_template = f"minmax(175px,1.55fr) {month_cols_css} 0.88fr 0.78fr 0.70fr 0.72fr 0.72fr"

                    head_cells = [f"<div>{html.escape(customer_label)}</div>"]
                    head_cells += [f"<div style='text-align:right;'>{html.escape(lbl)}</div>" for lbl in month_labels]
                    head_cells += [
                        "<div style='text-align:right;'>Total Business</div>",
                        "<div style='text-align:right;'>Avg / Month</div>",
                        "<div style='text-align:center;'>Months Active</div>",
                        "<div style='text-align:center;'>Consistency</div>",
                        "<div style='text-align:right;'>Growth %</div>",
                    ]

                    regular_rows_html = []
                    for _, row in regular_customers.iterrows():
                        customer_name = html.escape(str(row.get(name_col, "")))
                        row_cells = [f'<div class="customer-name-cell">{customer_name}</div>']
                        for abs_month in period_months:
                            value = float(row.get(abs_month, 0) or 0)
                            row_cells.append(f'<div class="regular-customer-month">{_fmt_business(value)}</div>')

                        total_business = float(row.get("total_business", 0) or 0)
                        avg_business = float(row.get("avg_month_business", 0) or 0)
                        growth = float(row.get("growth_%", 0) or 0)
                        growth_color = "#16a34a" if growth >= 0 else "#ef4444"
                        growth_arrow = "▲" if growth >= 0 else "▼"
                        row_cells += [
                            f'<div class="regular-customer-total">{_fmt_business(total_business)}</div>',
                            f'<div class="customer-num-cell">{_fmt_business(avg_business)}</div>',
                            f'<div class="regular-customer-muted">{regular_period}/{regular_period}</div>',
                            '<div class="regular-customer-consistency">100%</div>',
                            f'<div class="customer-num-cell" style="color:{growth_color};font-weight:850;">{growth_arrow} {abs(growth):.1f}%</div>',
                        ]
                        regular_rows_html.append(
                            f'<div class="regular-customer-row" style="grid-template-columns:{grid_template};">'
                            + "".join(row_cells)
                            + "</div>"
                        )

                    regular_table_html = (
                        '<div class="regular-customer-wrap">'
                        '<div class="regular-customer-table">'
                        f'<div class="regular-customer-head" style="grid-template-columns:{grid_template};">'
                        + "".join(head_cells)
                        + "</div>"
                        + "".join(regular_rows_html)
                        + "</div></div>"
                    )
                    st.markdown(regular_table_html, unsafe_allow_html=True)
                    st.caption(
                        f"Showing {len(regular_customers):,} of the top regular {customer_label.lower()}s with business in all {regular_period} months. Growth % uses the dashboard's existing CY vs LY comparison."
                    )


def render_growth_tab(growth_df: pd.DataFrame, name_col: str, customer_label: str, conversion_type: str) -> None:
    st.markdown(f"<div class='section-header'>{customer_label} Growth / Degrowth</div>", unsafe_allow_html=True)
    if growth_df.empty:
        st.info("No growth data available.")
        return

    display_df = growth_df.copy()
    divisor, unit = get_revenue_conversion(conversion_type)
    revenue_col = f"Business ({unit})"
    previous_col = f"Previous Business ({unit})"
    display_df[revenue_col] = (display_df["revenue"] / divisor).round(2)
    display_df[previous_col] = (display_df["prev_revenue"] / divisor).round(2)

    st.dataframe(
        display_df[[
            name_col, revenue_col, previous_col, "growth_%", "Customer Status",
            "shipments", "actual_weight", "charge_weight", "avg_delay", "max_delay",
        ]].sort_values("growth_%", ascending=False),
        use_container_width=True,
        hide_index=True,
        height=520,
    )


def render_service_tab(service_df: pd.DataFrame, customer_label: str, conversion_type: str) -> None:
    st.markdown(f"<div class='section-header'>{customer_label} Service Performance</div>", unsafe_allow_html=True)
    if service_df.empty:
        st.info("No service performance data available.")
        return

    display_df = service_df.copy()
    divisor, unit = get_revenue_conversion(conversion_type)
    display_df[f"Business ({unit})"] = (display_df["revenue"] / divisor).round(2)

    service_columns = [
        c for c in display_df.columns
        if c not in {"revenue", "Business Display", "Bubble Size"}
    ]
    st.dataframe(
        display_df[service_columns].sort_values("avg_delay_days", ascending=False),
        use_container_width=True,
        hide_index=True,
        height=520,
    )


def render_revenue_bridge(metrics: dict, customer_label: str, conversion_type: str) -> None:
    revenue_divisor, revenue_unit = get_revenue_conversion(conversion_type)

    py_revenue = metrics["prev_revenue"] / revenue_divisor
    new_revenue = metrics["revenue_from_new_customers"] / revenue_divisor
    reactivated_revenue = metrics["reactivated_revenue"] / revenue_divisor
    lost_revenue = -metrics["lost_revenue"] / revenue_divisor
    cy_revenue = metrics["total_revenue"] / revenue_divisor

    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "relative", "relative", "total"],
            x=[
                "Business PY",
                f"New {customer_label}s",
                "Reactivated",
                "Lost Business",
                "Business CY",
            ],
            y=[py_revenue, new_revenue, reactivated_revenue, lost_revenue, cy_revenue],
            text=[
                f"₹{py_revenue:.2f}",
                f"+₹{new_revenue:.2f}",
                f"+₹{reactivated_revenue:.2f}",
                f"-₹{abs(lost_revenue):.2f}",
                f"₹{cy_revenue:.2f}",
            ],
            textposition="outside",
            connector={"line": {"color": "#cbd5e1", "width": 1}},
            increasing={"marker": {"color": "#16a34a"}},
            decreasing={"marker": {"color": "#dc2626"}},
            totals={"marker": {"color": "#2563eb"}},
            hovertemplate=f"%{{x}}<br>₹%{{y:.2f}} {revenue_unit}<extra></extra>",
        )
    )
    fig.update_layout(
        height=330,
        margin=dict(l=8, r=8, t=18, b=8),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(
            title="",
            showgrid=False,
            tickfont=dict(family="Arial", size=12, color="#000000"),
            linecolor="#000000",
            tickcolor="#000000",
        ),
        yaxis=dict(
            title=dict(
                text=f"Business ({revenue_unit})",
                font=dict(family="Arial", size=12, color="#000000"),
            ),
            showgrid=False,
            zeroline=False,
            tickfont=dict(family="Arial", size=11, color="#000000"),
            linecolor="#000000",
            tickcolor="#000000",
        ),
        font=dict(family="Arial", size=11, color="#000000"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# =====================================================
# Zone Summary Table
# =====================================================
def render_zone_summary_table(
    df: pd.DataFrame,
    prev_df: pd.DataFrame,
    code_col: str,
    customer_label: str,
    conversion_type: str,
) -> None:
    """Executive zone comparison insight with current vs previous business and customer movement."""
    current_zone = df.groupby("Zone", as_index=False).agg(
        Active_Customers=(code_col, "nunique"),
        Revenue=("Revenue", "sum"),
    )
    prev_zone = prev_df.groupby("Zone", as_index=False).agg(
        Prev_Customers=(code_col, "nunique"),
        Prev_Revenue=("Revenue", "sum"),
    )

    current_codes = set(df[code_col].dropna().unique())
    previous_codes = set(prev_df[code_col].dropna().unique())
    new_df = df[df[code_col].isin(current_codes - previous_codes)]
    lost_df = prev_df[prev_df[code_col].isin(previous_codes - current_codes)]
    new_zone = new_df.groupby("Zone", as_index=False).agg(New=(code_col, "nunique"))
    lost_zone = lost_df.groupby("Zone", as_index=False).agg(Lost=(code_col, "nunique"))

    summary = (
        current_zone
        .merge(prev_zone, on="Zone", how="outer")
        .merge(new_zone, on="Zone", how="left")
        .merge(lost_zone, on="Zone", how="left")
        .fillna(0)
    )
    if summary.empty:
        st.info("No zone performance data available.")
        return

    summary["Growth %"] = summary.apply(
        lambda row: growth_percentage(row["Revenue"], row["Prev_Revenue"]), axis=1
    )
    summary["Customer Change"] = summary["Active_Customers"] - summary["Prev_Customers"]
    summary = summary.sort_values("Revenue", ascending=False).reset_index(drop=True)

    st.markdown(
        "<div class='section-header'>Zone Business: CY vs PY</div>",
        unsafe_allow_html=True,
    )

    total_cy = float(summary["Revenue"].sum() or 0)
    max_cy = max(float(summary["Revenue"].max() or 0), 1.0)
    rows_html = []

    for idx, row in summary.iterrows():
        zone_name = html.escape(str(row.get("Zone", "")))
        cy = float(row.get("Revenue", 0) or 0)
        py = float(row.get("Prev_Revenue", 0) or 0)
        active = int(row.get("Active_Customers", 0) or 0)
        new_count = int(row.get("New", 0) or 0)
        lost_count = int(row.get("Lost", 0) or 0)
        growth = float(row.get("Growth %", 0) or 0)
        share = (cy / total_cy * 100.0) if total_cy > 0 else 0.0
        scale_width = max(2.0, min(cy / max_cy * 100.0, 100.0)) if cy > 0 else 0.0

        growth_color = "#16a34a" if growth >= 0 else "#ef4444"
        growth_arrow = "▲" if growth >= 0 else "▼"
        new_color = "#16a34a" if new_count > 0 else "#64748b"
        lost_color = "#ef4444" if lost_count > 0 else "#64748b"

        rows_html.append(
            f'<div class="zone-rank-row">'
            f'<div class="zone-rank-no">{idx + 1}</div>'
            f'<div class="zone-rank-name">{zone_name}</div>'
            f'<div class="zone-rank-scale"><div class="zone-rank-scale-fill" style="width:{scale_width:.1f}%;"></div></div>'
            f'<div class="zone-rank-num zone-rank-cy">{money_display(cy, conversion_type)}</div>'
            f'<div class="zone-rank-num zone-rank-py">{money_display(py, conversion_type)}</div>'
            f'<div class="zone-rank-num zone-rank-share">{share:.1f}%</div>'
            f'<div class="zone-rank-num">{active:,}</div>'
            f'<div class="zone-rank-num" style="color:{new_color};font-weight:800;">+{new_count:,}</div>'
            f'<div class="zone-rank-num" style="color:{lost_color};font-weight:800;">-{lost_count:,}</div>'
            f'<div class="zone-rank-num" style="color:{growth_color};font-weight:850;">{growth_arrow} {abs(growth):.1f}%</div>'
            f'</div>'
        )

    zone_table_html = f"""
    <style>
    .zone-rank-table {{width:100%;font-size:11px;color:#0f2742;}}
    .zone-rank-head,.zone-rank-row {{display:grid;grid-template-columns:38px minmax(105px,.9fr) minmax(140px,1.25fr) .78fr .78fr .58fr .64fr .58fr .58fr .68fr;align-items:center;column-gap:10px;}}
    .zone-rank-head {{font-weight:850;padding:7px 10px 8px;color:#17365d;border-bottom:1px solid #dbe5f0;}}
    .zone-rank-row {{min-height:44px;padding:6px 10px;margin:6px 0;background:linear-gradient(180deg,#ffffff 0%,#fbfdff 100%);border:1px solid #dbe5f0;border-radius:10px;box-shadow:0 1px 3px rgba(15,23,42,.04);transition:transform .12s ease,box-shadow .12s ease;}}
    .zone-rank-row:hover {{transform:translateY(-1px);box-shadow:0 4px 10px rgba(15,23,42,.08);}}
    .zone-rank-no {{text-align:center;color:#64748b;font-weight:700;}}
    .zone-rank-name {{font-weight:850;color:#0f2742;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
    .zone-rank-scale {{height:9px;background:#e8eef6;border-radius:999px;overflow:hidden;}}
    .zone-rank-scale-fill {{height:100%;background:linear-gradient(90deg,#0ea5e9,#2563eb);border-radius:999px;}}
    .zone-rank-num {{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;}}
    .zone-rank-cy {{font-weight:850;color:#0f2742;}}
    .zone-rank-py {{color:#64748b;}}
    .zone-rank-share {{color:#7c3aed;font-weight:800;}}
    @media (max-width:1450px) {{.zone-rank-head,.zone-rank-row {{grid-template-columns:32px minmax(90px,.8fr) minmax(110px,1fr) .68fr .68fr .52fr .58fr .52fr .52fr .62fr;column-gap:7px;}} .zone-rank-table {{font-size:10px;}}}}
    </style>
    <div class="zone-rank-table">
      <div class="zone-rank-head">
        <div>#</div><div>Zone</div><div>Scale</div>
        <div style="text-align:right;">CY Business</div>
        <div style="text-align:right;">PY Business</div>
        <div style="text-align:right;">Share</div>
        <div style="text-align:right;">{html.escape(customer_label)}s</div>
        <div style="text-align:right;">New</div>
        <div style="text-align:right;">Lost</div>
        <div style="text-align:right;">Growth</div>
      </div>
      {''.join(rows_html)}
    </div>
    """
    st.markdown(zone_table_html, unsafe_allow_html=True)


def render_branch_summary_table(
    df: pd.DataFrame,
    prev_df: pd.DataFrame,
    code_col: str,
    customer_label: str,
    conversion_type: str,
) -> None:
    """Top branches CY vs PY details table with user-selectable row count."""
    current = df.groupby("Branch", as_index=False).agg(
        Revenue=("Revenue", "sum"),
        Customers=(code_col, "nunique"),
    )
    previous = prev_df.groupby("Branch", as_index=False).agg(
        PrevRevenue=("Revenue", "sum"),
        PrevCustomers=(code_col, "nunique"),
    )
    current_codes = set(df[code_col].dropna().unique())
    previous_codes = set(prev_df[code_col].dropna().unique())
    new_df = df[df[code_col].isin(current_codes - previous_codes)]
    new_branch = new_df.groupby("Branch", as_index=False).agg(NewCustomers=(code_col, "nunique"))

    summary = (
        current
        .merge(previous, on="Branch", how="outer")
        .merge(new_branch, on="Branch", how="left")
        .fillna(0)
    )
    if summary.empty:
        st.info("No branch performance data available.")
        return

    divisor, unit = get_revenue_conversion(conversion_type)
    cy_col = f"CY Business ({unit})"
    py_col = f"PY Business ({unit})"
    summary[cy_col] = (summary["Revenue"] / divisor).round(2)
    summary[py_col] = (summary["PrevRevenue"] / divisor).round(2)
    summary["Growth %"] = summary.apply(
        lambda row: growth_percentage(row["Revenue"], row["PrevRevenue"]), axis=1
    )

    header_left, header_right = st.columns([5, 1], vertical_alignment="center")
    with header_right:
        top_n = st.selectbox(
            "Top",
            [10, 20, 30, 40],
            index=0,
            format_func=lambda value: f"Top {value}",
            key="customer_branch_top_n",
            label_visibility="collapsed",
        )
    with header_left:
        st.markdown(
            f"<div class='section-header'>Top {top_n} Branches: CY vs PY</div>",
            unsafe_allow_html=True,
        )

    summary = summary.nlargest(top_n, "Revenue").sort_values("Revenue", ascending=False).reset_index(drop=True)

    max_cy = max(float(summary["Revenue"].max()), 1.0)
    rows_html = []
    for idx, row in summary.iterrows():
        branch_name = html.escape(str(row.get("Branch", "")))
        cy = float(row.get("Revenue", 0) or 0)
        py = float(row.get("PrevRevenue", 0) or 0)
        customers_cy = int(row.get("Customers", 0) or 0)
        new_customers = int(row.get("NewCustomers", 0) or 0)
        growth = float(row.get("Growth %", 0) or 0)
        scale_width = max(2.0, min(cy / max_cy * 100.0, 100.0)) if cy > 0 else 0.0
        growth_color = "#16a34a" if growth >= 0 else "#ef4444"
        growth_arrow = "▲" if growth >= 0 else "▼"
        new_color = "#2563eb" if new_customers > 0 else "#64748b"

        rows_html.append(
            f'<div class="branch-rank-row">'
            f'<div class="branch-rank-no">{idx + 1}</div>'
            f'<div class="branch-rank-name">{branch_name}</div>'
            f'<div class="branch-rank-scale"><div class="branch-rank-scale-fill" style="width:{scale_width:.1f}%;"></div></div>'
            f'<div class="branch-rank-num branch-rank-cy">{money_display(cy, conversion_type)}</div>'
            f'<div class="branch-rank-num branch-rank-py">{money_display(py, conversion_type)}</div>'
            f'<div class="branch-rank-num">{customers_cy:,}</div>'
            f'<div class="branch-rank-num" style="color:{new_color};font-weight:800;">+{new_customers:,}</div>'
            f'<div class="branch-rank-num" style="color:{growth_color};font-weight:850;">{growth_arrow} {abs(growth):.1f}%</div>'
            f'</div>'
        )

    branch_table_html = f"""
    <style>
    .branch-rank-table {{width:100%;font-size:11px;color:#0f2742;}}
    .branch-rank-head,.branch-rank-row {{display:grid;grid-template-columns:42px minmax(155px,1.15fr) minmax(180px,1.45fr) .78fr .78fr .72fr .72fr .72fr;align-items:center;column-gap:12px;}}
    .branch-rank-head {{font-weight:850;padding:7px 10px 8px;color:#17365d;border-bottom:1px solid #dbe5f0;}}
    .branch-rank-row {{min-height:44px;padding:6px 10px;margin:6px 0;background:#fbfdff;border:1px solid #dbe5f0;border-radius:10px;box-shadow:0 1px 2px rgba(15,23,42,.03);}}
    .branch-rank-no {{text-align:center;color:#64748b;font-weight:700;}}
    .branch-rank-name {{font-weight:800;color:#0f2742;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
    .branch-rank-scale {{height:9px;background:#e8eef6;border-radius:999px;overflow:hidden;}}
    .branch-rank-scale-fill {{height:100%;background:linear-gradient(90deg,#7c3aed,#2563eb);border-radius:999px;}}
    .branch-rank-num {{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;}}
    .branch-rank-cy {{font-weight:850;color:#0f2742;}}
    .branch-rank-py {{color:#64748b;}}
    @media (max-width:1400px) {{.branch-rank-head,.branch-rank-row {{grid-template-columns:34px minmax(130px,1.05fr) minmax(130px,1.15fr) .75fr .75fr .65fr .65fr .68fr;column-gap:8px;}} .branch-rank-table {{font-size:10px;}}}}
    </style>
    <div class="branch-rank-table">
      <div class="branch-rank-head">
        <div>#</div><div>Branch</div><div>Scale</div><div style="text-align:right;">CY Business</div>
        <div style="text-align:right;">PY Business</div><div style="text-align:right;">{html.escape(customer_label)}s</div>
        <div style="text-align:right;">New</div><div style="text-align:right;">Growth</div>
      </div>
      {''.join(rows_html)}
    </div>
    """
    st.markdown(branch_table_html, unsafe_allow_html=True)


def render_drilldown_tab(df: pd.DataFrame, name_col: str, customer_label: str, conversion_type: str) -> None:
    st.subheader(f"{customer_label} Drill Down")
    customers = sorted(df[name_col].dropna().unique())
    if not customers:
        st.info(f"No {customer_label.lower()} available for drill down.")
        return

    selected_customer = st.selectbox(f"Select {customer_label} for Detail", customers)
    customer_df = df[df[name_col] == selected_customer]

    total_shipments          = customer_df["ShipmentCount"].sum()
    total_revenue            = customer_df["Revenue"].sum()
    total_weight             = customer_df["ChargeWeight"].sum()
    avg_revenue_per_shipment = total_revenue / total_shipments if total_shipments > 0 else 0

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Total Shipments",        f"{total_shipments:,.0f}")
    d2.metric("Business",                money_display(total_revenue, conversion_type))
    d3.metric("Charge Weight",          f"{total_weight:,.0f}")
    d4.metric("Avg Business / Shipment", f"Rs.{avg_revenue_per_shipment:,.0f}")
    customer_display_df = customer_df.rename(columns={"Revenue": "Business"})
    st.dataframe(customer_display_df, use_container_width=True, hide_index=True)


def dashboard_spacer(height: int = 12) -> None:
    """Render a non-collapsing vertical gap between major dashboard rows."""
    st.markdown(
        f"<div aria-hidden='true' class='dashboard-row-gap' style='height:{height}px;min-height:{height}px;line-height:{height}px;'>&nbsp;</div>",
        unsafe_allow_html=True,
    )


# =====================================================
# Cached base data loader
# =====================================================
@st.cache_data(show_spinner=False, ttl=1800, max_entries=8)
def load_customer_analysis_periods(fin_year: str, view_type: str):
    """Load current, previous and older FY data once per FY/view.

    Streamlit reruns the script whenever a filter widget changes. Without this
    cache, the three database queries were executed again for every Zone, Circle,
    Branch, Quarter, Month, Load Type, Customer or Conversion change.
    """
    start_date, end_date = get_date_range(fin_year)

    previous_year = previous_financial_year(fin_year, 1)
    prev_start, prev_end = get_date_range(previous_year)

    older_year = previous_financial_year(fin_year, 2)
    old_start, old_end = get_date_range(older_year)

    with ThreadPoolExecutor(max_workers=3) as executor:
        current_future = executor.submit(
            load_booking_data, start_date, end_date, view_type
        )
        previous_future = executor.submit(
            load_booking_data, prev_start, prev_end, view_type
        )
        older_future = executor.submit(
            load_booking_data, old_start, old_end, view_type
        )

        current_df = clean_booking_data(current_future.result())
        previous_df = clean_booking_data(previous_future.result())
        older_df = clean_booking_data(older_future.result())

    return current_df, previous_df, older_df, previous_year, older_year


# =====================================================
# Main Dashboard
# =====================================================
def show_CustomerAnalysis() -> None:
    apply_dashboard_style()
    header_content_placeholder, export_placeholder = render_dashboard_header()

    filter_columns, fin_year, view_type = render_filter_row_start()
    if fin_year == "Select FY":
        st.info("Please select a Financial Year to continue.")
        return

    config         = get_customer_config(view_type)
    code_col       = config["code_col"]
    name_col       = config["name_col"]
    customer_label = config["label"]

    # Load the three financial-year datasets once per FY/View combination.
    # Filter widget changes now work against cached in-memory DataFrames instead
    # of executing the stored procedure three more times on every Streamlit rerun.
    try:
        with st.spinner("Loading customer summary data..."):
            df, prev_df, old_df, previous_year, older_year = load_customer_analysis_periods(
                fin_year, view_type
            )
    except Exception as exc:
        st.error(f"Unable to load Customer Analysis data: {exc}")
        return

    if df.empty:
        st.warning("No customer data found for the selected financial year.")
        return

    # Validate the columns required by the dashboard before creating helper
    # columns or filters. YR is intentionally not required.
    required_cols = [
        code_col,
        name_col,
        "Zone",
        "Circle",
        "Branch",
        "FIN_MONTH",
        "Revenue",
        "ShipmentCount",
        "ActualWeight",
        "ChargeWeight",
        "AvgDelayDays",
        "MaxDelayDays",
    ]

    missing_cols = [column for column in required_cols if column not in df.columns]
    if missing_cols:
        st.error(f"Missing columns returned by stored procedure: {missing_cols}")
        st.write("Available columns:", list(df.columns))
        return

    # Previous and older periods use the same output structure. Validate them
    # separately so a procedure issue is shown clearly instead of failing later.
    for period_label, period_df in (
        (previous_year, prev_df),
        (older_year, old_df),
    ):
        period_missing = [
            column for column in required_cols
            if column not in period_df.columns
        ]
        if period_missing:
            st.error(
                f"Missing columns for FY {period_label}: {period_missing}"
            )
            st.write(
                f"Available columns for FY {period_label}:",
                list(period_df.columns),
            )
            return

    # Display/filter helper columns. FIN_MONTH remains the source of truth.
    for period_df in (df, prev_df, old_df):
        period_df["Month"] = period_df["FIN_MONTH"].map(MONTH_MAP)
        period_df["Quarter"] = period_df["FIN_MONTH"].map(QUARTER_MAP)

    zone, circle, branch, quarter, month, load_type, customer, conversion_type = render_data_filters(
        df,
        customer_label,
        name_col,
        filter_columns,
    )

    def _chip_value(values, all_label="All"):
        if values in (None, "All"):
            return all_label
        if isinstance(values, (list, tuple, set)):
            vals = [str(v) for v in values if v not in (None, "", "All")]
            if not vals:
                return all_label
            return vals[0] if len(vals) == 1 else f"{len(vals)} selected"
        return str(values)

    header_items = [
        ("FY", fin_year),
        ("View", "Origin" if view_type == "origin" else "Destination"),
        ("Unit", conversion_type),
    ]

    # Show active slicer selections in the header as compact chips.
    # All/default selections are omitted so the header stays clean.
    active_header_filters = [
        ("Zone", zone),
        ("Circle", circle),
        ("Branch", branch),
        ("Quarter", quarter),
        ("Month", month),
        ("Load", load_type),
        (customer_label, customer),
    ]
    for label, value in active_header_filters:
        chip_val = _chip_value(value)
        if chip_val != "All":
            header_items.append((label, chip_val))
    header_chips = "".join(
        f'<span class="header-filter-chip">{label}: {value}</span>'
        for label, value in header_items
    )
    with header_content_placeholder:
        st.markdown(
            f"""
            <div class="dashboard-header" style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
                <div class="dashboard-title" style="white-space:nowrap;">Customer Analysis</div>
                <div class="header-filter-summary">{header_chips}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    df      = apply_filters(df,      zone, circle, branch, quarter, month, load_type, customer, name_col)
    prev_df = apply_filters(prev_df, zone, circle, branch, quarter, month, load_type, customer, name_col)
    old_df  = apply_filters(old_df,  zone, circle, branch, quarter, month, load_type, customer, name_col)

    if df.empty:
        st.warning("No data found for selected filters.")
        return

    dashboard_spacer()

    # --- Customer sets ---
    current_customers    = set(df[code_col].dropna().unique())
    previous_customers   = set(prev_df[code_col].dropna().unique())
    older_customers      = set(old_df[code_col].dropna().unique())
    new_customer_codes         = current_customers - previous_customers
    lost_customer_codes        = previous_customers - current_customers
    reactivated_customer_codes = (current_customers & older_customers) - previous_customers

    active_customers      = len(current_customers)
    prev_active_customers = len(previous_customers)
    new_customers         = len(new_customer_codes)
    lost_customers        = len(lost_customer_codes)
    reactivated_customers = len(reactivated_customer_codes)
    total_revenue         = df["Revenue"].sum()
    prev_revenue          = prev_df["Revenue"].sum()

    customer_summary = build_customer_summary(df, prev_df, code_col, name_col)
    monthly          = build_monthly_summary(df, code_col, conversion_type)
    service_df       = build_service_summary(df, code_col, name_col)

    reactivated_df = customer_summary[customer_summary[code_col].isin(reactivated_customer_codes)].copy()
    if not reactivated_df.empty:
        revenue_divisor, revenue_unit = get_revenue_conversion(conversion_type)
        reactivated_df[f"Business ({revenue_unit})"] = (reactivated_df["revenue"] / revenue_divisor).round(2)
        reactivated_df[f"Previous Business ({revenue_unit})"] = (reactivated_df["prev_revenue"] / revenue_divisor).round(2)

    growth_df = customer_summary.copy()
    growth_df["Customer Status"] = "Existing"
    growth_df.loc[growth_df[code_col].isin(new_customer_codes),         "Customer Status"] = "New"
    growth_df.loc[growth_df[code_col].isin(reactivated_customer_codes), "Customer Status"] = "Reactivated"

    at_risk_customers = customer_summary[
        (customer_summary["prev_revenue"] > 0) &
        (customer_summary["revenue"] < customer_summary["prev_revenue"] * 0.75)
    ][code_col].nunique()

    revenue_from_new_customers = df[df[code_col].isin(new_customer_codes)]["Revenue"].sum()
    lost_revenue               = prev_df[prev_df[code_col].isin(lost_customer_codes)]["Revenue"].sum()
    reactivated_revenue        = df[df[code_col].isin(reactivated_customer_codes)]["Revenue"].sum()
    charged_weight             = df["ChargeWeight"].sum()
    current_yield              = total_revenue / charged_weight if charged_weight > 0 else 0

    # Repeat Rate:
    # A customer is treated as repeat when the filtered period contains more than
    # one shipment for that customer. The rate is repeat customers / active customers.
    current_customer_shipments = df.groupby(code_col)["ShipmentCount"].sum()
    previous_customer_shipments = prev_df.groupby(code_col)["ShipmentCount"].sum()

    repeat_customers = int((current_customer_shipments > 1).sum())
    prev_repeat_customers = int((previous_customer_shipments > 1).sum())

    repeat_rate = (
        repeat_customers / active_customers * 100
        if active_customers > 0 else 0.0
    )
    prev_repeat_rate = (
        prev_repeat_customers / prev_active_customers * 100
        if prev_active_customers > 0 else 0.0
    )

    retention_percent          = (
        ((active_customers - new_customers) / prev_active_customers) * 100
        if prev_active_customers > 0 else 0
    )

    metrics = {
        "active_customers":           active_customers,
        "new_customers":              new_customers,
        "lost_customers":             lost_customers,
        "reactivated_customers":      reactivated_customers,
        "at_risk_customers":          at_risk_customers,
        "total_revenue":              total_revenue,
        "prev_revenue":               prev_revenue,
        "active_growth":              growth_percentage(active_customers, prev_active_customers),
        "revenue_growth":             growth_percentage(total_revenue, prev_revenue),
        "retention_percent":          retention_percent,
        "revenue_from_new_customers": revenue_from_new_customers,
        "lost_revenue":               lost_revenue,
        "reactivated_revenue":        reactivated_revenue,
        "current_yield":              current_yield,
        "repeat_customers":           repeat_customers,
        "repeat_rate":                repeat_rate,
        "repeat_rate_growth":         growth_percentage(repeat_rate, prev_repeat_rate),
    }

    excel_file = export_to_excel(
        df=df,
        customer_summary=customer_summary,
        growth_df=growth_df,
        monthly_df=monthly,
        reactivated_df=reactivated_df,
        service_df=service_df,
    )
    with export_placeholder:
        st.download_button(
            label="Export to Excel",
            data=excel_file,
            file_name=f"customer_analysis_{view_type}_{fin_year}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="customer_analysis_export_excel",
            help="Download the filtered customer analysis data.",
            use_container_width=True,
        )

    # --- KPIs ---
    render_kpis(metrics, customer_label, conversion_type)

    # Real Streamlit spacer so the next insight row never touches the KPI cards.
    with st.container(height=18, border=False):
        st.markdown("&nbsp;", unsafe_allow_html=True)

    # --- Business and geography ---
    c1, c2 = st.columns([1.15, 0.85], gap="medium", vertical_alignment="top")
    with c1:
        with st.container(border=True):
            render_zone_summary_table(df, prev_df, code_col, customer_label, conversion_type)
    with c2:
        with st.container(border=True):
            st.markdown("<div class='section-header business-movement-title'>Business Movement</div>", unsafe_allow_html=True)
            render_revenue_bridge(metrics, customer_label, conversion_type)

    dashboard_spacer()

    # --- Branch customer intelligence ---
    with st.container(border=True):
        render_branch_summary_table(df, prev_df, code_col, customer_label, conversion_type)

    dashboard_spacer()

    # --- Tabs ---
    tab1, tab2 = st.tabs([
        "Executive Overview",
        "Detailed Analysis",
    ])
    with tab1:
        render_overview_tab(customer_summary, monthly, df, code_col, name_col, customer_label, prev_df, lost_customer_codes, conversion_type)
    with tab2:
        render_drilldown_tab(df, name_col, customer_label, conversion_type)
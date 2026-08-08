import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    monthly["Revenue Display"] = (monthly["revenue"] / divisor).round(2)
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
    data_scope = st.session_state.get("data_scope", {}) or {}
    locked_zone = data_scope.get("zone")
    locked_circle = data_scope.get("circle")
    locked_branch = data_scope.get("branch")

    if locked_branch:
        row = df[df["Branch"].astype(str).str.casefold() == str(locked_branch).casefold()]
        if not row.empty:
            locked_branch = row["Branch"].iloc[0]
            locked_circle = row["Circle"].iloc[0]
            locked_zone = row["Zone"].iloc[0]
    elif locked_circle:
        row = df[df["Circle"].astype(str).str.casefold() == str(locked_circle).casefold()]
        if not row.empty:
            locked_circle = row["Circle"].iloc[0]
            locked_zone = row["Zone"].iloc[0]

    f1, f2, f3, f4, f5, f6, f7, f8 = filter_columns[2:]
    filter_source_df = df.copy()

    with f1:
        zone_options = sorted(filter_source_df["Zone"].dropna().unique().tolist()) if "Zone" in filter_source_df.columns else []
        selected_zones = _checkbox_slicer(
            "◉ Zone", zone_options, key="customer_zone_slicer",
            locked_values=[locked_zone] if locked_zone else None,
        )

    with f2:
        circle_options = sorted(filter_source_df["Circle"].dropna().unique().tolist()) if "Circle" in filter_source_df.columns else []
        selected_circles = _checkbox_slicer(
            "◎ Circle", circle_options, key="customer_circle_slicer",
            locked_values=[locked_circle] if locked_circle else None,
            searchable=True,
        )

    with f3:
        branch_options = sorted(filter_source_df["Branch"].dropna().unique().tolist()) if "Branch" in filter_source_df.columns else []
        selected_branches = _checkbox_slicer(
            "⌂ Branch", branch_options, key="customer_branch_slicer",
            locked_values=[locked_branch] if locked_branch else None,
            searchable=True,
        )

    with f4:
        available_quarters = [
            q for q in QUARTER_ORDER
            if q in filter_source_df["Quarter"].dropna().unique().tolist()
        ]
        selected_quarters = _checkbox_slicer(
            "▦ Quarter", available_quarters, key="customer_quarter_slicer"
        )

    with f5:
        month_source_df = filter_source_df
        if selected_quarters:
            month_source_df = month_source_df[month_source_df["Quarter"].isin(selected_quarters)]
        available_months = [
            m for m in MONTH_ORDER
            if m in month_source_df["Month"].dropna().unique().tolist()
        ]
        selected_months = _checkbox_slicer(
            "▣ Month", available_months, key="customer_month_slicer"
        )

    selection_df = filter_source_df
    if selected_zones:
        selection_df = selection_df[selection_df["Zone"].isin(selected_zones)]
    if selected_circles:
        selection_df = selection_df[selection_df["Circle"].isin(selected_circles)]
    if selected_branches:
        selection_df = selection_df[selection_df["Branch"].isin(selected_branches)]
    if selected_quarters:
        selection_df = selection_df[selection_df["Quarter"].isin(selected_quarters)]
    if selected_months:
        selection_df = selection_df[selection_df["Month"].isin(selected_months)]

    with f6:
        loadtype_list = ["All"] + (sorted(selection_df["LoadType"].dropna().unique()) if "LoadType" in selection_df.columns else [])
        load_type = st.selectbox("▤ Load Type", loadtype_list, key="customer_loadtype")
    loadtype_df = selection_df if load_type == "All" else selection_df[selection_df["LoadType"] == load_type]

    with f7:
        customer_list = ["All"] + (sorted(loadtype_df[customer_name_col].dropna().unique()) if customer_name_col in loadtype_df.columns else [])
        customer = st.selectbox(f"👤 {customer_label}", customer_list, key="customer_name_filter")

    with f8:
        conversion_type = st.selectbox("₹ Conversion", ["Crore", "Lac"], key="customer_conversion_type")

    return selected_zones, selected_circles, selected_branches, selected_quarters, selected_months, load_type, customer, conversion_type


# =====================================================
# KPI Row  — 8 equal columns
# =====================================================
def render_kpis(metrics: dict, customer_label: str, conversion_type: str) -> None:
    """Render all Customer Analysis KPIs using the Overview dashboard card style."""
    cols = st.columns(8, gap="small")

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
            "title": "Total Revenue",
            "value": money_display(metrics["total_revenue"], conversion_type),
            "delta": f"{format_delta(metrics['revenue_growth'])}",
            "icon": "₹", "color": "#2563eb",
            "positive": metrics["revenue_growth"] >= 0,
        },
        {
            "title": "Multi-Shipment Customers %",
            "value": f"{metrics['repeat_rate']:.1f}%",
            "delta": f"{format_delta(metrics['repeat_rate_growth'])}",
            "icon": "🔁", "color": "#2563eb",
            "positive": metrics["repeat_rate_growth"] >= 0,
        },
        {
            "title": f"At Risk {customer_label}s",
            "value": f"{metrics['at_risk_customers']:,}",
            "delta": "Revenue dropped above 25%",
            "icon": "⚠️", "color": "#d97706",
            "positive": False if metrics["at_risk_customers"] > 0 else None,
        },
        {
            "title": "Current Yield",
            "value": f"₹{metrics['current_yield']:.2f} /Kg",
            "delta": "Revenue / Charge Weight",
            "icon": "⚡", "color": "#2563eb", "positive": None,
        },
    ]

    for col, card in zip(cols, cards):
        with col:
            kpi_card(**card)

    st.markdown("<div class='kpi-row-spacer'></div>", unsafe_allow_html=True)


def render_overview_tab(
    customer_summary: pd.DataFrame,
    monthly: pd.DataFrame,
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
                monthly, x="FIN_MONTH", y="Revenue Display",
                text="Revenue Display", title=f"Month-wise Revenue ({revenue_unit})",
            )
            fig.update_traces(texttemplate=f"Rs.%{{text:.2f}} {revenue_unit}", textposition="outside", marker_color="#60a5fa", marker_line_color="#2563eb", marker_line_width=1)
            fig.update_yaxes(title=f"Revenue ({revenue_unit})")
            fig.update_layout(height=330, margin=dict(t=45, b=20), plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with c2:
        with st.container(border=True):
            revenue_rank = customer_summary.sort_values("revenue", ascending=False)
            total_revenue = revenue_rank["revenue"].sum()
            rows = []
            for lbl, top_n in [("Top 10", 10), ("Top 20", 20), ("Top 50", 50), ("Top 100", 100)]:
                top_rev = revenue_rank.head(top_n)["revenue"].sum()
                pct = (top_rev / total_revenue * 100) if total_revenue else 0
                rows.append({"Customer Group": lbl, "% of Total Revenue": round(pct, 1)})
            concentration_df = pd.DataFrame(rows)
            fig = px.bar(
                concentration_df,
                x="% of Total Revenue", y="Customer Group",
                orientation="h", text="% of Total Revenue",
                title="Revenue Concentration",
            )
            fig.update_traces(texttemplate="%{text}%", textposition="outside")
            fig.update_layout(
                xaxis_title="% of Total Revenue", yaxis_title="",
                height=330, margin=dict(t=45, b=20), plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with c3:
        with st.container(border=True):
            segmented = add_customer_segments(customer_summary)
            segment_order = ["Champions", "Loyal", "Potential", "At Risk", "Lost"]
            segment_colors = {
                "Champions": "#14946b", "Loyal": "#0f6ec7", "Potential": "#5ab0e8",
                "At Risk": "#f59e0b", "Lost": "#ef4444",
            }
            segment_df = segmented.groupby("segment", as_index=False).agg(revenue=("revenue", "sum"))
            total_seg_rev = segment_df["revenue"].sum()
            segment_df["Contribution %"] = (segment_df["revenue"] / total_seg_rev * 100).round(1) if total_seg_rev else 0
            segment_df["Legend Label"] = segment_df.apply(
                lambda r: f"{r['segment']} {r['Contribution %']:.1f}%", axis=1
            )
            segment_df["segment"] = pd.Categorical(segment_df["segment"], categories=segment_order, ordered=True)
            segment_df = segment_df.sort_values("segment")
            fig = px.pie(
                segment_df, names="Legend Label", values="revenue", hole=0.55,
                title=f"{customer_label} Segmentation", color="segment",
                color_discrete_map=segment_colors,
            )
            fig.update_traces(textinfo="percent", textposition="inside")
            fig.update_layout(
                height=330, margin=dict(t=45, b=5),
                annotations=[dict(
                    text=f"Total<br>{money_display(total_seg_rev, conversion_type)}",
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
    ].copy().nlargest(10, "growth_%")

    top_degrowing = customer_summary[
        (customer_summary["prev_revenue"] > 0) &
        (customer_summary["revenue"] < customer_summary["prev_revenue"]) &
        (customer_summary["revenue"] > 0)
    ].copy().nsmallest(10, "growth_%")

    lost_summary = (
        prev_df[prev_df[code_col].isin(lost_customer_codes)]
        .groupby([code_col, name_col], as_index=False)
        .agg(lost_revenue=("Revenue", "sum"), last_CN_month=("FIN_MONTH", "max"))
        .nlargest(10, "lost_revenue")
    )

    divisor, unit = get_revenue_conversion(conversion_type)
    v1, v2, v3 = st.columns(3, gap="small")

    def render_cy_py_customer_chart(
        source_df: pd.DataFrame,
        title: str,
        sort_column: str,
        ascending: bool,
        empty_message: str,
        table_columns: list[str],
    ) -> None:
        st.markdown(f"<div class='section-header'>{title}</div>", unsafe_allow_html=True)
        if source_df.empty:
            st.info(empty_message)
            return

        chart_df = source_df.copy().sort_values(sort_column, ascending=ascending)
        chart_df["CY Revenue"] = chart_df["revenue"] / divisor
        chart_df["PY Revenue"] = chart_df["prev_revenue"] / divisor

        long_df = chart_df.melt(
            id_vars=[name_col, "growth_%"],
            value_vars=["PY Revenue", "CY Revenue"],
            var_name="Period",
            value_name="Revenue Display",
        )
        fig = px.bar(
            long_df,
            x="Revenue Display",
            y=name_col,
            color="Period",
            orientation="h",
            barmode="group",
            text="Revenue Display",
            custom_data=["growth_%"],
            category_orders={name_col: chart_df[name_col].tolist()},
        )
        fig.update_traces(
            texttemplate=f"%{{text:.2f}} {unit}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                f"%{{y}}<br>%{{fullData.name}}: %{{x:.2f}} {unit}"
                "<br>Growth: %{customdata[0]:.1f}%<extra></extra>"
            ),
        )
        fig.update_layout(
            height=320,
            margin=dict(l=5, r=35, t=5, b=20),
            xaxis_title=f"Revenue ({unit})",
            yaxis_title="",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend_title_text="",
            legend=dict(orientation="h", y=1.02, x=0),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # FIXED: Only select columns that actually exist in chart_df
        safe_columns = [col for col in table_columns if col in chart_df.columns]
        if safe_columns:
            detail_df = chart_df[safe_columns].copy()
            detail_df["CY Revenue"] = chart_df["revenue"] / divisor
            detail_df["PY Revenue"] = chart_df["prev_revenue"] / divisor
            
            # Only rename columns that exist
            rename_map = {
                name_col: customer_label,
                "growth_%": "Growth %",
                "shipments": "CY Shipments",
            }
            # Only add prev_shipments to rename if it exists
            if "prev_shipments" in detail_df.columns:
                rename_map["prev_shipments"] = "PY Shipments"
            
            detail_df = detail_df.rename(columns=rename_map)
            
            with st.expander("View detailed CY / PY figures"):
                st.dataframe(
                    detail_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "CY Revenue": st.column_config.NumberColumn(format=f"%.2f {unit}"),
                        "PY Revenue": st.column_config.NumberColumn(format=f"%.2f {unit}"),
                        "Growth %": st.column_config.NumberColumn(format="%.1f%%"),
                    },
                )

    with v1:
        with st.container(border=True):
            render_cy_py_customer_chart(
                top_growing,
                f"Top Growing {customer_label}s",
                "growth_%",
                True,
                "No growing customers for selected filters.",
                [name_col, "growth_%", "shipments", "prev_shipments"],
            )

    with v2:
        with st.container(border=True):
            render_cy_py_customer_chart(
                top_degrowing,
                f"Top De-growing {customer_label}s",
                "growth_%",
                False,
                "No de-growing customers for selected filters.",
                [name_col, "growth_%", "shipments", "prev_shipments"],
            )

    with v3:
        with st.container(border=True):
            st.markdown(f"<div class='section-header'>Top Lost {customer_label}s</div>", unsafe_allow_html=True)
            if lost_summary.empty:
                st.info("No lost customers for selected filters.")
            else:
                chart_df = lost_summary.copy().sort_values("lost_revenue", ascending=True)
                chart_df["prev_revenue"] = chart_df["lost_revenue"]
                chart_df["revenue"] = 0.0
                chart_df["growth_%"] = -100.0
                chart_df["PY Revenue"] = chart_df["prev_revenue"] / divisor
                chart_df["CY Revenue"] = 0.0

                long_df = chart_df.melt(
                    id_vars=[name_col, "growth_%"],
                    value_vars=["PY Revenue", "CY Revenue"],
                    var_name="Period",
                    value_name="Revenue Display",
                )
                fig = px.bar(
                    long_df,
                    x="Revenue Display",
                    y=name_col,
                    color="Period",
                    orientation="h",
                    barmode="group",
                    text="Revenue Display",
                    custom_data=["growth_%"],
                    category_orders={name_col: chart_df[name_col].tolist()},
                )
                fig.update_traces(
                    texttemplate=f"%{{text:.2f}} {unit}",
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate=(
                        f"%{{y}}<br>%{{fullData.name}}: %{{x:.2f}} {unit}"
                        "<br>Growth: %{customdata[0]:.1f}%<extra></extra>"
                    ),
                )
                fig.update_layout(
                    height=320,
                    margin=dict(l=5, r=35, t=5, b=20),
                    xaxis_title=f"Revenue ({unit})",
                    yaxis_title="",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    legend_title_text="",
                    legend=dict(orientation="h", y=1.02, x=0),
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

                detail_df = chart_df[[name_col, "last_CN_month", "PY Revenue", "CY Revenue", "growth_%"]].copy()
                detail_df = detail_df.rename(columns={
                    name_col: customer_label,
                    "last_CN_month": "Last CN Month",
                    "growth_%": "Growth %",
                })
                with st.expander("View detailed CY / PY figures"):
                    st.dataframe(
                        detail_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "CY Revenue": st.column_config.NumberColumn(format=f"%.2f {unit}"),
                            "PY Revenue": st.column_config.NumberColumn(format=f"%.2f {unit}"),
                            "Growth %": st.column_config.NumberColumn(format="%.1f%%"),
                        },
                    )


def render_growth_tab(growth_df: pd.DataFrame, name_col: str, customer_label: str, conversion_type: str) -> None:
    st.markdown(f"<div class='section-header'>{customer_label} Growth / Degrowth</div>", unsafe_allow_html=True)
    if growth_df.empty:
        st.info("No growth data available.")
        return

    display_df = growth_df.copy()
    divisor, unit = get_revenue_conversion(conversion_type)
    display_df["Revenue Display"] = display_df["revenue"] / divisor
    display_df["Previous Revenue Display"] = display_df["prev_revenue"] / divisor
    display_df["Bubble Size"] = display_df["shipments"].clip(lower=1)

    fig = px.scatter(
        display_df,
        x="Previous Revenue Display",
        y="Revenue Display",
        size="Bubble Size",
        color="Customer Status",
        hover_name=name_col,
        hover_data={"growth_%": ":.1f", "shipments": ":,.0f", "Bubble Size": False},
        size_max=34,
        title="Current Revenue vs Previous Revenue",
    )
    max_value = max(display_df["Revenue Display"].max(), display_df["Previous Revenue Display"].max(), 1)
    fig.add_shape(type="line", x0=0, y0=0, x1=max_value, y1=max_value, line=dict(dash="dash", color="#64748b"))
    fig.update_layout(
        height=430, margin=dict(t=45, b=25),
        xaxis_title=f"Previous Revenue ({unit})", yaxis_title=f"Current Revenue ({unit})",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with st.expander("View detailed growth table"):
        revenue_col = f"Revenue ({unit})"
        previous_col = f"Previous Revenue ({unit})"
        display_df[revenue_col] = display_df["Revenue Display"].round(2)
        display_df[previous_col] = display_df["Previous Revenue Display"].round(2)
        st.dataframe(
            display_df[[
                name_col, revenue_col, previous_col, "growth_%", "Customer Status",
                "shipments", "actual_weight", "charge_weight", "avg_delay", "max_delay",
            ]].sort_values("growth_%", ascending=True),
            use_container_width=True, hide_index=True,
        )


def render_service_tab(service_df: pd.DataFrame, customer_label: str, conversion_type: str) -> None:
    st.markdown(f"<div class='section-header'>{customer_label} Service Performance</div>", unsafe_allow_html=True)
    if service_df.empty:
        st.info("No service performance data available.")
        return

    display_df = service_df.copy()
    divisor, unit = get_revenue_conversion(conversion_type)
    display_df["Revenue Display"] = display_df["revenue"] / divisor
    shipment_col = "shipments" if "shipments" in display_df.columns else None
    name_candidates = [c for c in display_df.columns if c not in {
        "revenue", "Revenue Display", "avg_delay_days", "max_delay_days",
        "shipments", "actual_weight", "charge_weight"
    }]
    hover_name = name_candidates[0] if name_candidates else None
    display_df["Bubble Size"] = display_df[shipment_col].clip(lower=1) if shipment_col else 1

    left, right = st.columns([1.35, 1], gap="small")
    with left:
        with st.container(border=True):
            fig = px.scatter(
                display_df,
                x="avg_delay_days",
                y="Revenue Display",
                size="Bubble Size",
                color="max_delay_days",
                hover_name=hover_name,
                hover_data={"Bubble Size": False},
                color_continuous_scale="YlOrRd",
                size_max=38,
                title="Revenue vs Average Delay",
            )
            fig.update_layout(
                height=390, margin=dict(t=45, b=25),
                xaxis_title="Average Delay (Days)", yaxis_title=f"Revenue ({unit})",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with right:
        with st.container(border=True):
            delayed = display_df.nlargest(12, "avg_delay_days").sort_values("avg_delay_days")
            y_col = hover_name if hover_name else delayed.index.astype(str)
            if hover_name is None:
                delayed = delayed.assign(Customer=delayed.index.astype(str))
                y_col = "Customer"
            fig = px.bar(
                delayed, x="avg_delay_days", y=y_col, orientation="h",
                text="avg_delay_days", title="Highest Average Delay",
            )
            fig.update_traces(texttemplate="%{text:.1f} d", textposition="outside")
            fig.update_layout(
                height=390, margin=dict(l=5, r=25, t=45, b=25),
                xaxis_title="Average Delay (Days)", yaxis_title="",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with st.expander("View detailed service table"):
        display_df[f"Revenue ({unit})"] = display_df["Revenue Display"].round(2)
        st.dataframe(
            display_df.drop(columns=["Revenue Display", "Bubble Size"], errors="ignore")
            .sort_values("avg_delay_days", ascending=False),
            use_container_width=True, hide_index=True,
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
                "Revenue PY",
                f"New {customer_label}s",
                "Reactivated",
                "Lost Revenue",
                "Revenue CY",
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
        xaxis=dict(title="", showgrid=False),
        yaxis=dict(title=f"Revenue ({revenue_unit})", showgrid=False, zeroline=False),
        font=dict(family="Arial", size=11, color="#334155"),
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
    """Zone comparison visual with both current-year and previous-year figures."""
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

    divisor, unit = get_revenue_conversion(conversion_type)
    cy_col = f"CY Revenue ({unit})"
    py_col = f"PY Revenue ({unit})"
    summary[cy_col] = (summary["Revenue"] / divisor).round(2)
    summary[py_col] = (summary["Prev_Revenue"] / divisor).round(2)
    summary["Growth %"] = summary.apply(
        lambda row: growth_percentage(row["Revenue"], row["Prev_Revenue"]), axis=1
    )
    summary = summary.sort_values("Revenue", ascending=False).reset_index(drop=True)

    total_cy_revenue = float(summary["Revenue"].sum())
    summary["Share %"] = (summary["Revenue"] / total_cy_revenue * 100) if total_cy_revenue else 0.0
    max_cy_display = max(float(summary[cy_col].abs().max()), 1.0)

    st.markdown(
        "<div class='section-header'>Zone Revenue: CY vs PY</div>",
        unsafe_allow_html=True,
    )

    zone_rows = []
    for idx, row in summary.iterrows():
        cy_value = float(row[cy_col] or 0)
        py_value = float(row[py_col] or 0)
        share_value = float(row["Share %"] or 0)
        growth_value = float(row["Growth %"] or 0)
        width_pct = min(abs(cy_value) / max_cy_display * 100, 100)
        growth_color = "#16a34a" if growth_value >= 0 else "#dc2626"
        growth_arrow = "▲" if growth_value >= 0 else "▼"
        zone_name = str(row["Zone"])
        zone_rows.append(
            f"<div class='zone-rank-row'>"
            f"<div class='zone-rank'>{idx + 1}</div>"
            f"<div class='zone-name-cell' title='{zone_name}'>{zone_name}</div>"
            f"<div class='zone-scale'><div class='zone-scale-fill' style='width:{width_pct:.1f}%'></div></div>"
            f"<div class='zone-cy'>₹{cy_value:,.2f} {unit}</div>"
            f"<div class='zone-py'>₹{py_value:,.2f} {unit}</div>"
            f"<div class='zone-share'>{share_value:.2f}%</div>"
            f"<div class='zone-growth' style='color:{growth_color};'>{growth_arrow} {abs(growth_value):.1f}%</div>"
            f"</div>"
        )

    zone_html = f"""
    <style>
        .zone-rank-wrap {{width:100%;padding:0 1px 2px 1px;}}
        .zone-rank-header,.zone-rank-row {{
            display:grid;grid-template-columns:34px minmax(95px,150px) minmax(120px,1fr) 105px 105px 72px 82px;
            align-items:center;gap:10px;
        }}
        .zone-rank-header {{padding:2px 10px 6px;color:#64748b;font-size:10px;font-weight:700;border-bottom:1px solid #dbe4ef;}}
        .zone-rank-row {{margin-top:7px;padding:9px 10px;border:1px solid #dbe4ef;border-radius:12px;background:#fbfdff;}}
        .zone-rank {{text-align:center;color:#475569;font-size:12px;}}
        .zone-name-cell {{font-size:12px;font-weight:650;color:#0f2744;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
        .zone-scale {{height:7px;background:#e7edf5;border-radius:999px;overflow:hidden;box-shadow:inset 0 1px 2px rgba(15,23,42,.08);}}
        .zone-scale-fill {{height:7px;background:linear-gradient(90deg,#7c3aed,#2563eb);border-radius:999px;}}
        .zone-cy {{text-align:right;color:#0f172a;font-size:12px;font-weight:750;white-space:nowrap;}}
        .zone-py {{text-align:right;color:#64748b;font-size:12px;white-space:nowrap;}}
        .zone-share {{text-align:right;color:#6d28d9;font-size:12px;font-weight:700;white-space:nowrap;}}
        .zone-growth {{text-align:right;font-size:12px;font-weight:700;white-space:nowrap;}}
        @media (max-width:1100px) {{
            .zone-rank-header,.zone-rank-row {{grid-template-columns:30px minmax(85px,120px) minmax(90px,1fr) 88px 88px 62px 72px;gap:6px;}}
        }}
    </style>
    <div class='zone-rank-wrap'>
        <div class='zone-rank-header'>
            <div style='text-align:center;'>#</div><div>Zone</div><div>Scale</div>
            <div style='text-align:right;'>CY</div><div style='text-align:right;'>PY</div>
            <div style='text-align:right;'>Share</div><div style='text-align:right;'>Growth</div>
        </div>
        {''.join(zone_rows)}
    </div>
    """
    if hasattr(st, "html"):
        st.html(zone_html)
    else:
        st.markdown(zone_html, unsafe_allow_html=True)

    table_df = summary.rename(columns={
        "Active_Customers": f"Active {customer_label}s CY",
        "Prev_Customers": f"Active {customer_label}s PY",
    })[[
        "Zone",
        f"Active {customer_label}s CY",
        f"Active {customer_label}s PY",
        "New",
        "Lost",
        cy_col,
        py_col,
        "Growth %",
    ]].sort_values(cy_col, ascending=False)

    with st.expander("View zone figures (CY and PY)", expanded=False):
        st.dataframe(
            table_df.style.format({
                f"Active {customer_label}s CY": "{:,.0f}",
                f"Active {customer_label}s PY": "{:,.0f}",
                "New": "{:,.0f}",
                "Lost": "{:,.0f}",
                cy_col: "{:,.2f}",
                py_col: "{:,.2f}",
                "Growth %": "{:.1f}%",
            }),
            use_container_width=True,
            hide_index=True,
        )


def render_branch_summary_table(
    df: pd.DataFrame,
    prev_df: pd.DataFrame,
    code_col: str,
    customer_label: str,
    conversion_type: str,
) -> None:
    """Top branches comparison visual retaining current-year and previous-year figures."""
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
    cy_col = f"CY Revenue ({unit})"
    py_col = f"PY Revenue ({unit})"
    summary[cy_col] = (summary["Revenue"] / divisor).round(2)
    summary[py_col] = (summary["PrevRevenue"] / divisor).round(2)
    summary["Growth %"] = summary.apply(
        lambda row: growth_percentage(row["Revenue"], row["PrevRevenue"]), axis=1
    )
    summary = summary.nlargest(10, "Revenue").sort_values("Revenue", ascending=True)

    chart_df = summary[["Branch", cy_col, py_col]].melt(
        id_vars="Branch",
        var_name="Period",
        value_name="Revenue Display",
    )
    st.markdown(
        "<div class='section-header'>Top 10 Branches: CY vs PY</div>",
        unsafe_allow_html=True,
    )
    fig = px.bar(
        chart_df,
        x="Revenue Display",
        y="Branch",
        color="Period",
        barmode="group",
        orientation="h",
        text="Revenue Display",
        category_orders={"Period": [py_col, cy_col]},
    )
    fig.update_traces(
        texttemplate="%{text:.2f}",
        textposition="outside",
        cliponaxis=False,
    )
    fig.update_layout(
        height=310,
        margin=dict(l=5, r=30, t=8, b=5),
        xaxis_title=f"Revenue ({unit})",
        yaxis_title="",
        legend_title_text="",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    table_df = summary.rename(columns={
        "Customers": f"{customer_label}s CY",
        "PrevCustomers": f"{customer_label}s PY",
        "NewCustomers": f"New {customer_label}s",
    })[[
        "Branch",
        cy_col,
        py_col,
        f"{customer_label}s CY",
        f"{customer_label}s PY",
        f"New {customer_label}s",
        "Growth %",
    ]].sort_values(cy_col, ascending=False)

    with st.expander("View branch figures (CY and PY)", expanded=False):
        st.dataframe(
            table_df.style.format({
                cy_col: "{:,.2f}",
                py_col: "{:,.2f}",
                f"{customer_label}s CY": "{:,.0f}",
                f"{customer_label}s PY": "{:,.0f}",
                f"New {customer_label}s": "{:,.0f}",
                "Growth %": "{:.1f}%",
            }),
            use_container_width=True,
            hide_index=True,
        )


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
    d2.metric("Revenue",                money_display(total_revenue, conversion_type))
    d3.metric("Charge Weight",          f"{total_weight:,.0f}")
    d4.metric("Avg Revenue / Shipment", f"Rs.{avg_revenue_per_shipment:,.0f}")
    st.dataframe(customer_df, use_container_width=True, hide_index=True)


def dashboard_spacer(height: int = 12) -> None:
    """Render a non-collapsing vertical gap between major dashboard rows."""
    st.markdown(
        f"<div aria-hidden='true' class='dashboard-row-gap' style='height:{height}px;min-height:{height}px;line-height:{height}px;'>&nbsp;</div>",
        unsafe_allow_html=True,
    )


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

    start_date, end_date = get_date_range(fin_year)

    previous_year = previous_financial_year(fin_year, 1)
    prev_start, prev_end = get_date_range(previous_year)

    older_year = previous_financial_year(fin_year, 2)
    old_start, old_end = get_date_range(older_year)

    # Load each financial year separately. The stored procedure does not need to
    # return a YR column because the date range itself identifies the period.
    # Three independent calls are executed in parallel to reduce wait time.
    try:
        with st.spinner("Loading customer summary data..."):
            with ThreadPoolExecutor(max_workers=3) as executor:
                current_future = executor.submit(
                    load_booking_data,
                    start_date,
                    end_date,
                    view_type,
                )
                previous_future = executor.submit(
                    load_booking_data,
                    prev_start,
                    prev_end,
                    view_type,
                )
                older_future = executor.submit(
                    load_booking_data,
                    old_start,
                    old_end,
                    view_type,
                )

                df = clean_booking_data(current_future.result())
                prev_df = clean_booking_data(previous_future.result())
                old_df = clean_booking_data(older_future.result())
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

    header_items = [
        ("FY", fin_year),
        ("View", "Origin" if view_type == "origin" else "Destination"),
        ("Unit", conversion_type),
    ]
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
        reactivated_df[f"Revenue ({revenue_unit})"] = (reactivated_df["revenue"] / revenue_divisor).round(2)
        reactivated_df[f"Previous Revenue ({revenue_unit})"] = (reactivated_df["prev_revenue"] / revenue_divisor).round(2)

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
    dashboard_spacer()

    # --- Revenue and geography ---
    c1, c2 = st.columns([1.15, 0.85], gap="medium", vertical_alignment="top")
    with c1:
        with st.container(border=True):
            render_zone_summary_table(df, prev_df, code_col, customer_label, conversion_type)
    with c2:
        with st.container(border=True):
            st.markdown("<div class='section-header'>Revenue Movement</div>", unsafe_allow_html=True)
            render_revenue_bridge(metrics, customer_label, conversion_type)

    dashboard_spacer()

    # --- Branch customer intelligence ---
    with st.container(border=True):
        render_branch_summary_table(df, prev_df, code_col, customer_label, conversion_type)

    dashboard_spacer()

    # --- Tabs ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "Executive Overview",
        "Customer Intelligence",
        "Service Performance",
        "Detailed Analysis",
    ])
    with tab1:
        render_overview_tab(customer_summary, monthly, code_col, name_col, customer_label, prev_df, lost_customer_codes, conversion_type)
    with tab2:
        render_growth_tab(growth_df, name_col, customer_label, conversion_type)
    with tab3:
        render_service_tab(service_df, customer_label, conversion_type)
    with tab4:
        render_drilldown_tab(df, name_col, customer_label, conversion_type)

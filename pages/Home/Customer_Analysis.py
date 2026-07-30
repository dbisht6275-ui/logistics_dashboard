import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
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
            height: 14px;
            width: 100%;
            clear: both;
        }
        .insight-section-spacer {
            height: 6px;
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
    df = normalize_columns(df)
    numeric_cols = [
        "YR", "FIN_MONTH", "ShipmentCount", "ActualWeight",
        "ChargeWeight", "Revenue", "AvgDelayDays", "MaxDelayDays",
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
    zone: str,
    circle: str,
    branch: str,
    quarter: str,
    month: str,
    load_type: str,
    customer: str,
    customer_name_col: str,
) -> pd.DataFrame:
    filtered = df.copy()
    if zone      != "All" and "Zone"     in filtered.columns: filtered = filtered[filtered["Zone"]     == zone]
    if circle    != "All" and "Circle"   in filtered.columns: filtered = filtered[filtered["Circle"]   == circle]
    if branch    != "All" and "Branch"   in filtered.columns: filtered = filtered[filtered["Branch"]   == branch]
    if quarter   != "All" and "Quarter"  in filtered.columns: filtered = filtered[filtered["Quarter"]  == quarter]
    if month     != "All" and "Month"    in filtered.columns: filtered = filtered[filtered["Month"]    == month]
    if load_type != "All" and "LoadType" in filtered.columns: filtered = filtered[filtered["LoadType"] == load_type]
    if customer  != "All" and customer_name_col in filtered.columns:
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
    intelligence_df: pd.DataFrame | None = None,
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
        if intelligence_df is not None:
            sheets["Customer Intelligence"] = intelligence_df
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
        .agg(prev_revenue=("Revenue", "sum"), prev_shipments=("ShipmentCount", "sum"))
    )
    summary = current_summary.merge(previous_summary, on=code_col, how="left")
    summary["prev_revenue"]   = summary["prev_revenue"].fillna(0)
    summary["prev_shipments"] = summary["prev_shipments"].fillna(0)
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
    """Render the compact Overview-style heading and return the export placeholder."""
    with st.container(border=True):
        header_left, header_right = st.columns(
            [7, 1],
            gap="small",
            vertical_alignment="center",
        )

        with header_left:
            st.markdown(
                """
                <div class="dashboard-header">
                    <div class="dashboard-title">Customer Analysis</div>
                    <div class="dashboard-subtitle">
                        Analyze customer acquisition, retention, revenue and branch performance.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with header_right:
            export_placeholder = st.empty()

    return export_placeholder


def render_filter_row_start():
    """Create the complete single-row filter layout and render FY/View Type first.

    The remaining column objects are reused after the selected FY/View Type data is loaded,
    allowing every dashboard filter to stay on one visual row without changing any logic.
    """
    filter_columns = st.columns(
        [1.10, 1.00, 0.82, 0.92, 1.00, 0.72, 0.82, 0.92, 1.25, 0.82],
        gap="small",
    )

    with filter_columns[0]:
        fin_year = st.selectbox(
            "Financial Year",
            FINANCIAL_YEARS,
            key="customer_financial_year",
        )

    with filter_columns[1]:
        view_type = st.selectbox(
            "View Type",
            ["origin", "destination"],
            format_func=lambda x: "Origin" if x == "origin" else "Destination",
            key="customer_view_type",
        )

    return filter_columns, fin_year, view_type


def render_data_filters(
    df: pd.DataFrame,
    customer_label: str,
    customer_name_col: str,
    filter_columns,
):
    data_scope    = st.session_state.get("data_scope", {})
    locked_zone   = data_scope.get("zone")
    locked_circle = data_scope.get("circle")
    locked_branch = data_scope.get("branch")

    if locked_branch:
        row = df[df["Branch"] == locked_branch]
        if not row.empty:
            locked_circle = row["Circle"].iloc[0]
            locked_zone   = row["Zone"].iloc[0]
    elif locked_circle:
        row = df[df["Circle"] == locked_circle]
        if not row.empty:
            locked_zone = row["Zone"].iloc[0]

    # Financial Year and View Type occupy the first two columns.
    # These eight columns complete the same single filter row.
    f1, f2, f3, f4, f5, f6, f7, f8 = filter_columns[2:]

    with f1:
        if locked_zone:
            zone = locked_zone
            st.selectbox("Zone", [zone], disabled=True, key="customer_zone_locked")
        else:
            zone_list = ["All"] + (sorted(df["Zone"].dropna().unique()) if "Zone" in df.columns else [])
            zone = st.selectbox("Zone", zone_list, key="customer_zone")
    zone_df = df if zone == "All" else df[df["Zone"] == zone]

    with f2:
        if locked_circle:
            circle = locked_circle
            st.selectbox("Circle", [circle], disabled=True, key="customer_circle_locked")
        else:
            circle_list = ["All"] + (sorted(zone_df["Circle"].dropna().unique()) if "Circle" in zone_df.columns else [])
            circle = st.selectbox("Circle", circle_list, key="customer_circle")
    circle_df = zone_df if circle == "All" else zone_df[zone_df["Circle"] == circle]

    with f3:
        if locked_branch:
            branch = locked_branch
            st.selectbox("Branch", [branch], disabled=True, key="customer_branch_locked")
        else:
            branch_list = ["All"] + (sorted(circle_df["Branch"].dropna().unique()) if "Branch" in circle_df.columns else [])
            branch = st.selectbox("Branch", branch_list, key="customer_branch")
    branch_df = circle_df if branch == "All" else circle_df[circle_df["Branch"] == branch]

    with f4:
        available_quarters = [q for q in QUARTER_ORDER if q in branch_df["Quarter"].dropna().unique().tolist()]
        quarter = st.selectbox("Quarter", ["All"] + available_quarters, key="customer_quarter")
    quarter_df = branch_df if quarter == "All" else branch_df[branch_df["Quarter"] == quarter]

    with f5:
        available_months = [m for m in MONTH_ORDER if m in quarter_df["Month"].dropna().unique().tolist()]
        month = st.selectbox("Month", ["All"] + available_months, key="customer_month")
    month_df = quarter_df if month == "All" else quarter_df[quarter_df["Month"] == month]

    with f6:
        loadtype_list = ["All"] + (sorted(month_df["LoadType"].dropna().unique()) if "LoadType" in month_df.columns else [])
        load_type = st.selectbox("Load Type", loadtype_list, key="customer_loadtype")
    loadtype_df = month_df if load_type == "All" else month_df[month_df["LoadType"] == load_type]

    with f7:
        customer_list = ["All"] + (sorted(loadtype_df[customer_name_col].dropna().unique()) if customer_name_col in loadtype_df.columns else [])
        customer = st.selectbox(customer_label, customer_list, key="customer_name_filter")

    with f8:
        conversion_type = st.selectbox("Conversion", ["Crore", "Lac"], key="customer_conversion_type")

    return zone, circle, branch, quarter, month, load_type, customer, conversion_type


# =====================================================
# KPI Row  — 7 equal columns
# =====================================================
def render_kpis(metrics: dict, customer_label: str, conversion_type: str) -> None:
    """Render core customer KPIs using the Overview dashboard card style."""
    cards = [
        {"title": f"Active {customer_label}s", "value": f"{metrics['active_customers']:,}",
         "delta": format_delta(metrics['active_growth']), "icon": "👥", "color": "#2563eb",
         "positive": metrics['active_growth'] >= 0},
        {"title": f"New {customer_label}s", "value": f"{metrics['new_customers']:,}",
         "delta": "Acquired vs previous FY", "icon": "🆕", "color": "#16a34a", "positive": None},
        {"title": "Customer Churn", "value": f"{metrics['churn_rate']:.1f}%",
         "delta": f"{metrics['lost_customers']:,} customers inactive", "icon": "📉", "color": "#dc2626",
         "positive": False if metrics['churn_rate'] > 0 else None},
        {"title": "Repeat Rate", "value": f"{metrics['repeat_rate']:.1f}%",
         "delta": "Customers with more than 1 shipment", "icon": "🔁", "color": "#0d9488",
         "positive": True},
        {"title": "Total Revenue", "value": money_display(metrics['total_revenue'], conversion_type),
         "delta": format_delta(metrics['revenue_growth']), "icon": "₹", "color": "#7c3aed",
         "positive": metrics['revenue_growth'] >= 0},
        {"title": "Revenue / Customer", "value": money_display(metrics['arpu'], conversion_type),
         "delta": "Average revenue per active customer", "icon": "💳", "color": "#9333ea", "positive": None},
        {"title": "Avg Shipment Value", "value": f"₹{metrics['avg_shipment_value']:,.0f}",
         "delta": "Revenue divided by shipments", "icon": "📦", "color": "#d97706", "positive": None},
        {"title": "Top 20% Revenue Share", "value": f"{metrics['top20_share']:.1f}%",
         "delta": "Customer concentration (80/20)", "icon": "🎯", "color": "#ea580c", "positive": None},
        {"title": "Current Yield", "value": f"₹{metrics['current_yield']:.2f} /Kg",
         "delta": "Revenue / charge weight", "icon": "⚡", "color": "#db2777", "positive": None},
    ]

    for row_cards in (cards[:5], cards[5:]):
        cols = st.columns(len(row_cards), gap="small")
        for col, card in zip(cols, row_cards):
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
            fig.update_traces(texttemplate=f"Rs.%{{text:.2f}} {revenue_unit}", textposition="outside")
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
    bridge_df = pd.DataFrame({
        "Metric": [
            "Revenue PY",
            f"New {customer_label}s",
            "Reactivated",
            "Lost Revenue",
            "Revenue CY",
        ],
        "Value": [
            metrics["prev_revenue"],
            metrics["revenue_from_new_customers"],
            metrics["reactivated_revenue"],
            -metrics["lost_revenue"],
            metrics["total_revenue"],
        ],
    })
    revenue_divisor, revenue_unit = get_revenue_conversion(conversion_type)
    fig = px.bar(
        bridge_df,
        x="Metric",
        y=bridge_df["Value"] / revenue_divisor,
        text=(bridge_df["Value"] / revenue_divisor).round(2),
    )
    fig.update_traces(texttemplate=f"Rs. %{{text:.2f}} {revenue_unit}", textposition="outside")
    fig.update_yaxes(title=f"Revenue ({revenue_unit})")
    fig.update_xaxes(title="")
    fig.update_layout(
        height=330,
        margin=dict(l=5, r=5, t=12, b=5),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
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
    summary = summary.sort_values("Revenue", ascending=True)

    chart_df = summary[["Zone", cy_col, py_col]].melt(
        id_vars="Zone",
        var_name="Period",
        value_name="Revenue Display",
    )
    st.markdown(
        f"<div class='section-header'>Zone Revenue: CY vs PY</div>",
        unsafe_allow_html=True,
    )
    fig = px.bar(
        chart_df,
        x="Revenue Display",
        y="Zone",
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


def build_customer_intelligence(
    customer_summary: pd.DataFrame,
    code_col: str,
    name_col: str,
    new_customer_codes: set,
    reactivated_customer_codes: set,
) -> pd.DataFrame:
    """Build customer-level commercial intelligence from fields available in the current query."""
    intel = customer_summary.copy()
    if intel.empty:
        return intel

    total_revenue = float(intel["revenue"].sum())
    intel["revenue_share_%"] = (intel["revenue"] / total_revenue * 100) if total_revenue else 0
    intel["revenue_per_shipment"] = intel["revenue"] / intel["shipments"].replace(0, pd.NA)
    intel["revenue_per_shipment"] = intel["revenue_per_shipment"].fillna(0)
    intel["shipment_growth_%"] = intel.apply(
        lambda r: growth_percentage(r["shipments"], r["prev_shipments"]), axis=1
    )
    intel["repeat_type"] = intel["shipments"].apply(lambda x: "Repeat" if x > 1 else "One-time")
    intel["service_proxy"] = intel["avg_delay"].apply(
        lambda x: "On-time / early avg" if x <= 0 else "Delayed avg"
    )

    revenue_cut = intel["revenue"].quantile(0.80)
    frequency_cut = intel["shipments"].median()

    def classify(row):
        code = row[code_col]
        if code in new_customer_codes:
            return "New"
        if code in reactivated_customer_codes:
            return "Reactivated"
        if row["revenue"] >= revenue_cut and row["shipments"] >= frequency_cut:
            return "VIP"
        if row["shipment_growth_%"] >= 20:
            return "Growing"
        if row["shipment_growth_%"] <= -20 or row["growth_%"] <= -25:
            return "Declining"
        if row["shipments"] <= 1:
            return "One-time"
        return "Regular"

    intel["strategic_segment"] = intel.apply(classify, axis=1)
    return intel.sort_values("revenue", ascending=False).reset_index(drop=True)


def render_customer_intelligence_tab(
    intelligence_df: pd.DataFrame,
    monthly: pd.DataFrame,
    df: pd.DataFrame,
    prev_df: pd.DataFrame,
    code_col: str,
    name_col: str,
    customer_label: str,
    lost_customer_codes: set,
    conversion_type: str,
) -> None:
    if intelligence_df.empty:
        st.info("No customer intelligence data available.")
        return

    divisor, unit = get_revenue_conversion(conversion_type)
    total_customers = len(intelligence_df)
    repeat_customers = int((intelligence_df["repeat_type"] == "Repeat").sum())
    one_time_customers = total_customers - repeat_customers
    on_time_proxy = float((intelligence_df["avg_delay"] <= 0).mean() * 100) if total_customers else 0

    # Executive commercial insights
    a, b, c = st.columns([1.1, 1, 1], gap="small")
    with a:
        with st.container(border=True):
            st.markdown("<div class='section-header'>Strategic Customer Segmentation</div>", unsafe_allow_html=True)
            segment = intelligence_df.groupby("strategic_segment", as_index=False).agg(
                Customers=(code_col, "nunique"), Revenue=("revenue", "sum")
            )
            segment["Revenue Display"] = segment["Revenue"] / divisor
            fig = px.scatter(
                segment, x="Customers", y="Revenue Display", size="Customers",
                color="strategic_segment", text="strategic_segment",
                hover_data={"Revenue": False, "Revenue Display": ":.2f"},
            )
            fig.update_traces(textposition="top center")
            fig.update_layout(height=320, margin=dict(l=5, r=5, t=10, b=25),
                              xaxis_title="Customers", yaxis_title=f"Revenue ({unit})",
                              showlegend=False, plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with b:
        with st.container(border=True):
            st.markdown("<div class='section-header'>Repeat vs One-time Customers</div>", unsafe_allow_html=True)
            repeat_df = pd.DataFrame({"Type": ["Repeat", "One-time"],
                                      "Customers": [repeat_customers, one_time_customers]})
            fig = px.pie(repeat_df, names="Type", values="Customers", hole=0.58,
                         color="Type", color_discrete_map={"Repeat": "#16a34a", "One-time": "#f59e0b"})
            fig.update_traces(textinfo="label+percent")
            fig.update_layout(height=320, margin=dict(l=5, r=5, t=10, b=5), showlegend=False,
                              annotations=[dict(text=f"{repeat_customers/total_customers*100:.1f}%<br>Repeat" if total_customers else "0%",
                                                x=.5, y=.5, showarrow=False, font_size=13)])
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with c:
        with st.container(border=True):
            st.markdown("<div class='section-header'>Shipment Frequency Trend</div>", unsafe_allow_html=True)
            trend = monthly.copy()
            trend["Shipments / Customer"] = trend["shipments"] / trend["customers"].replace(0, pd.NA)
            trend["Shipments / Customer"] = trend["Shipments / Customer"].fillna(0)
            trend["Month"] = trend["FIN_MONTH"].map(MONTH_MAP)
            fig = px.line(trend, x="Month", y="Shipments / Customer", markers=True,
                          category_orders={"Month": MONTH_ORDER})
            fig.update_layout(height=320, margin=dict(l=5, r=5, t=10, b=25),
                              xaxis_title="", yaxis_title="Avg shipments / active customer",
                              plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # 80/20 and geographic growth
    left, right = st.columns([1.15, 1], gap="small")
    with left:
        with st.container(border=True):
            st.markdown("<div class='section-header'>80/20 Revenue Concentration</div>", unsafe_allow_html=True)
            ranked = intelligence_df.sort_values("revenue", ascending=False).copy()
            ranked["Customer Rank %"] = (ranked.index.to_series() + 1) / len(ranked) * 100
            ranked["Cumulative Revenue %"] = ranked["revenue"].cumsum() / ranked["revenue"].sum() * 100
            fig = px.line(ranked, x="Customer Rank %", y="Cumulative Revenue %", markers=False)
            fig.add_vline(x=20, line_dash="dash", line_color="#dc2626")
            fig.add_hline(y=80, line_dash="dash", line_color="#64748b")
            fig.update_layout(height=330, margin=dict(l=5, r=5, t=10, b=25),
                              xaxis_title="Top customer population (%)",
                              yaxis_title="Cumulative revenue (%)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with right:
        with st.container(border=True):
            st.markdown("<div class='section-header'>Growth by Zone</div>", unsafe_allow_html=True)
            cy = df.groupby("Zone", as_index=False).agg(CY_Revenue=("Revenue", "sum"), CY_Customers=(code_col, "nunique"))
            py = prev_df.groupby("Zone", as_index=False).agg(PY_Revenue=("Revenue", "sum"), PY_Customers=(code_col, "nunique"))
            geo = cy.merge(py, on="Zone", how="outer").fillna(0)
            geo["Growth %"] = geo.apply(lambda r: growth_percentage(r["CY_Revenue"], r["PY_Revenue"]), axis=1)
            geo["CY Revenue"] = geo["CY_Revenue"] / divisor
            geo = geo.sort_values("CY Revenue", ascending=True)
            fig = px.bar(geo, x="CY Revenue", y="Zone", orientation="h", color="Growth %",
                         color_continuous_scale="RdYlGn", text="Growth %")
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig.update_layout(height=330, margin=dict(l=5, r=35, t=10, b=25),
                              xaxis_title=f"Current Revenue ({unit})", yaxis_title="",
                              plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Service proxy and lost/dormant customers
    s1, s2 = st.columns(2, gap="small")
    with s1:
        with st.container(border=True):
            st.markdown("<div class='section-header'>Customer Service Proxy</div>", unsafe_allow_html=True)
            st.metric("Customers with average delay ≤ 0 days", f"{on_time_proxy:.1f}%")
            st.caption("This is a customer-level proxy based on average delay, not a true shipment-level on-time or SLA compliance rate.")
            service_view = intelligence_df[[name_col, "shipments", "avg_delay", "max_delay", "service_proxy"]].copy()
            st.dataframe(service_view.sort_values("avg_delay", ascending=False).head(15),
                         use_container_width=True, hide_index=True)

    with s2:
        with st.container(border=True):
            st.markdown(f"<div class='section-header'>Dormant / Lost {customer_label}s</div>", unsafe_allow_html=True)
            dormant = prev_df[prev_df[code_col].isin(lost_customer_codes)].groupby(
                [code_col, name_col], as_index=False
            ).agg(Previous_Revenue=("Revenue", "sum"), Previous_Shipments=("ShipmentCount", "sum"),
                  Last_Active_Month=("FIN_MONTH", "max"))
            dormant["Last Active"] = dormant["Last_Active_Month"].map(MONTH_MAP)
            dormant[f"Previous Revenue ({unit})"] = dormant["Previous_Revenue"] / divisor
            show_cols = [name_col, "Previous_Shipments", "Last Active", f"Previous Revenue ({unit})"]
            st.dataframe(dormant.sort_values("Previous_Revenue", ascending=False)[show_cols].head(15),
                         use_container_width=True, hide_index=True)

    st.markdown("<div class='section-header'>Customer Intelligence Detail</div>", unsafe_allow_html=True)
    detail_cols = [name_col, "strategic_segment", "repeat_type", "revenue", "shipments",
                   "revenue_per_shipment", "growth_%", "shipment_growth_%", "avg_delay", "service_proxy"]
    st.dataframe(intelligence_df[detail_cols], use_container_width=True, hide_index=True,
                 column_config={
                     "revenue": st.column_config.NumberColumn("Revenue (Rs.)", format="₹%,.0f"),
                     "revenue_per_shipment": st.column_config.NumberColumn("Revenue / Shipment", format="₹%,.0f"),
                     "growth_%": st.column_config.NumberColumn("Revenue Growth %", format="%.1f%%"),
                     "shipment_growth_%": st.column_config.NumberColumn("Shipment Growth %", format="%.1f%%"),
                     "avg_delay": st.column_config.NumberColumn("Avg Delay", format="%.2f"),
                 })

    with st.expander("Metrics requiring additional source data"):
        st.markdown(
            """
            - **Peak routing corridors:** requires origin and destination on the same record/query.
            - **True on-time delivery and SLA compliance:** requires shipment-level promised and actual delivery status/counts.
            - **Complaints, service ratings and satisfaction:** require CRM/helpdesk/survey data.
            - **Cost per shipment and margin:** require shipment-level direct/allocated cost.
            - **Customer lifetime value:** requires customer acquisition date, retention horizon and margin history.
            """
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


# =====================================================
# Main Dashboard
# =====================================================
def show_CustomerAnalysis() -> None:
    apply_dashboard_style()
    export_placeholder = render_dashboard_header()

    filter_columns, fin_year, view_type = render_filter_row_start()
    if fin_year == "Select FY":
        st.info("Please select a Financial Year to continue.")
        return

    config         = get_customer_config(view_type)
    code_col       = config["code_col"]
    name_col       = config["name_col"]
    customer_label = config["label"]

    start_date, end_date = get_date_range(fin_year)
    prev_start, prev_end = get_date_range(previous_financial_year(fin_year, 1))
    old_start,  old_end  = get_date_range(previous_financial_year(fin_year, 2))

    with st.spinner("Loading customer summary data..."):
        all_df = clean_booking_data(load_booking_data(old_start, end_date, view_type))

    df      = all_df[all_df["YR"].astype(int) == int(fin_year.split("-")[0])].copy()
    prev_df = all_df[all_df["YR"].astype(int) == int(previous_financial_year(fin_year, 1).split("-")[0])].copy()
    old_df  = all_df[all_df["YR"].astype(int) == int(previous_financial_year(fin_year, 2).split("-")[0])].copy()

    if df.empty:
        st.warning("No customer data found.")
        return

    # Display/filter helper columns. FIN_MONTH remains the source of truth.
    for period_df in (df, prev_df, old_df):
        period_df["Month"] = period_df["FIN_MONTH"].map(MONTH_MAP)
        period_df["Quarter"] = period_df["FIN_MONTH"].map(QUARTER_MAP)

    required_cols = [code_col, name_col, "Zone", "Branch", "FIN_MONTH",
                     "Revenue", "ShipmentCount", "ActualWeight", "ChargeWeight",
                     "AvgDelayDays", "MaxDelayDays"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        st.error(f"Missing columns: {missing_cols}")
        st.write("Available columns:", list(df.columns))
        return

    zone, circle, branch, quarter, month, load_type, customer, conversion_type = render_data_filters(
        df,
        customer_label,
        name_col,
        filter_columns,
    )

    df      = apply_filters(df,      zone, circle, branch, quarter, month, load_type, customer, name_col)
    prev_df = apply_filters(prev_df, zone, circle, branch, quarter, month, load_type, customer, name_col)
    old_df  = apply_filters(old_df,  zone, circle, branch, quarter, month, load_type, customer, name_col)

    if df.empty:
        st.warning("No data found for selected filters.")
        return

    st.divider()

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
    total_shipments            = float(customer_summary["shipments"].sum())
    arpu                       = total_revenue / active_customers if active_customers else 0
    avg_shipment_value         = total_revenue / total_shipments if total_shipments else 0
    repeat_customers           = int((customer_summary["shipments"] > 1).sum())
    repeat_rate                = (repeat_customers / active_customers * 100) if active_customers else 0
    churn_rate                 = (lost_customers / prev_active_customers * 100) if prev_active_customers else 0
    top_n                      = max(1, int((active_customers * 0.20) + 0.999999)) if active_customers else 0
    top20_revenue              = customer_summary.nlargest(top_n, "revenue")["revenue"].sum() if top_n else 0
    top20_share                = (top20_revenue / total_revenue * 100) if total_revenue else 0
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
        "arpu":                       arpu,
        "avg_shipment_value":         avg_shipment_value,
        "repeat_rate":                repeat_rate,
        "churn_rate":                 churn_rate,
        "top20_share":                top20_share,
    }

    intelligence_df = build_customer_intelligence(
        customer_summary, code_col, name_col, new_customer_codes, reactivated_customer_codes
    )

    excel_file = export_to_excel(
        df=df,
        customer_summary=customer_summary,
        growth_df=growth_df,
        monthly_df=monthly,
        reactivated_df=reactivated_df,
        service_df=service_df,
        intelligence_df=intelligence_df,
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

    # --- Visual insight row: Zone CY/PY | Revenue Bridge | Branch CY/PY ---
    c1, c2, c3 = st.columns([1, 1, 1], gap="small", vertical_alignment="top")
    with c1:
        with st.container(border=True):
            render_zone_summary_table(df, prev_df, code_col, customer_label, conversion_type)
    with c2:
        with st.container(border=True):
            st.markdown("<div class='section-header'>Revenue Bridge</div>", unsafe_allow_html=True)
            render_revenue_bridge(metrics, customer_label, conversion_type)
    with c3:
        with st.container(border=True):
            render_branch_summary_table(df, prev_df, code_col, customer_label, conversion_type)

    st.markdown("<div class='insight-section-spacer'></div>", unsafe_allow_html=True)

    # --- Tabs ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        f"{customer_label} Overview",
        "Customer Intelligence",
        "Growth & Retention",
        "Service Performance",
        f"{customer_label} Drill Down",
    ])
    with tab1:
        render_overview_tab(customer_summary, monthly, code_col, name_col, customer_label, prev_df, lost_customer_codes, conversion_type)
    with tab2:
        render_customer_intelligence_tab(
            intelligence_df, monthly, df, prev_df, code_col, name_col,
            customer_label, lost_customer_codes, conversion_type
        )
    with tab3:
        render_growth_tab(growth_df, name_col, customer_label, conversion_type)
    with tab4:
        render_service_tab(service_df, customer_label, conversion_type)
    with tab5:
        render_drilldown_tab(df, name_col, customer_label, conversion_type)
